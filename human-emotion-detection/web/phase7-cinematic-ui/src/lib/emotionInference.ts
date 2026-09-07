import type { InferenceSession } from "onnxruntime-web";

export interface FaceBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface EmotionPrediction {
  emotion: string;
  confidence: number;
  probabilities: Record<string, number>;
}

const IMAGE_SIZE = 260;

let sessionPromise: Promise<InferenceSession> | null = null;
let labels = [
  "angry",
  "disgust",
  "fear",
  "happy",
  "neutral",
  "sad",
  "surprise",
];
let temperature = 1;

async function loadSession(): Promise<InferenceSession> {
  if (!sessionPromise) {
    sessionPromise = (async () => {
      const ort = await import("onnxruntime-web");

      ort.env.wasm.wasmPaths = "/ort/";
      ort.env.wasm.numThreads = 1;

      const [session, labelsResponse, calibrationResponse] =
        await Promise.all([
          ort.InferenceSession.create("/models/emotion_model.onnx", {
            executionProviders: ["wasm"],
            graphOptimizationLevel: "all",
          }),
          fetch("/models/labels.json"),
          fetch("/models/calibration.json"),
        ]);

      if (labelsResponse.ok) {
        labels = await labelsResponse.json();
      }

      if (calibrationResponse.ok) {
        const calibration = await calibrationResponse.json();
        temperature = Number(calibration.temperature) || 1;
      }

      return session;
    })();
  }

  return sessionPromise;
}

function preprocessFace(
  video: HTMLVideoElement,
  box: FaceBox,
): Float32Array {
  const canvas = document.createElement("canvas");
  canvas.width = IMAGE_SIZE;
  canvas.height = IMAGE_SIZE;

  const context = canvas.getContext("2d", {
    willReadFrequently: true,
  });

  if (!context) {
    throw new Error("Canvas is unavailable.");
  }

  const padding = Math.max(box.width, box.height) * 0.15;

  const x = Math.max(0, box.x - padding);
  const y = Math.max(0, box.y - padding);
  const width = Math.min(
    video.videoWidth - x,
    box.width + padding * 2,
  );
  const height = Math.min(
    video.videoHeight - y,
    box.height + padding * 2,
  );

  context.drawImage(
    video,
    x,
    y,
    width,
    height,
    0,
    0,
    IMAGE_SIZE,
    IMAGE_SIZE,
  );

  const pixels = context.getImageData(
    0,
    0,
    IMAGE_SIZE,
    IMAGE_SIZE,
  ).data;

  const pixelCount = IMAGE_SIZE * IMAGE_SIZE;
  const tensor = new Float32Array(3 * pixelCount);

  for (let index = 0; index < pixelCount; index++) {
    const offset = index * 4;

    const gray =
      (0.299 * pixels[offset] +
        0.587 * pixels[offset + 1] +
        0.114 * pixels[offset + 2]) /
      255;

    tensor[index] = (gray - 0.485) / 0.229;
    tensor[pixelCount + index] = (gray - 0.456) / 0.224;
    tensor[pixelCount * 2 + index] = (gray - 0.406) / 0.225;
  }

  return tensor;
}

function softmax(logits: number[]): number[] {
  const scaled = logits.map((value) => value / temperature);
  const maximum = Math.max(...scaled);
  const exponentials = scaled.map((value) =>
    Math.exp(value - maximum),
  );
  const total = exponentials.reduce(
    (sum, value) => sum + value,
    0,
  );

  return exponentials.map((value) => value / total);
}

export async function prepareEmotionModel(): Promise<void> {
  await loadSession();
}

export async function predictEmotion(
  video: HTMLVideoElement,
  box: FaceBox,
): Promise<EmotionPrediction> {
  const ort = await import("onnxruntime-web");
  const session = await loadSession();
  const inputData = preprocessFace(video, box);

  const inputTensor = new ort.Tensor(
    "float32",
    inputData,
    [1, 3, IMAGE_SIZE, IMAGE_SIZE],
  );

  const results = await session.run({
    [session.inputNames[0]]: inputTensor,
  });

  const output = results[session.outputNames[0]];
  const logits = Array.from(output.data as Float32Array);
  const probabilities = softmax(logits);

  let bestIndex = 0;

  for (let index = 1; index < probabilities.length; index++) {
    if (probabilities[index] > probabilities[bestIndex]) {
      bestIndex = index;
    }
  }

  return {
    emotion: labels[bestIndex],
    confidence: probabilities[bestIndex],
    probabilities: Object.fromEntries(
      labels.map((label, index) => [
        label,
        probabilities[index],
      ]),
    ),
  };
}