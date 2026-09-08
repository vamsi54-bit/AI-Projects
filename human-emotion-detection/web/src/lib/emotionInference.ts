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

export type ModelProfile = "mobile" | "desktop";

interface LoadedModel {
  session: InferenceSession;
  profile: ModelProfile;
  imageSize: number;
}

const MODEL_SETTINGS = {
  mobile: {
    path: "/models/emotion_model_mobile.onnx",
    imageSize: 160,
  },
  desktop: {
    path: "/models/emotion_model_desktop.onnx",
    imageSize: 260,
  },
} as const;

let modelPromise: Promise<LoadedModel> | null = null;

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

let preprocessingCanvas: HTMLCanvasElement | null = null;
let preprocessingContext: CanvasRenderingContext2D | null = null;

export function getDeviceModelProfile(): ModelProfile {
  if (typeof window === "undefined") {
    return "desktop";
  }

  const navigatorWithHints = navigator as Navigator & {
    userAgentData?: {
      mobile?: boolean;
    };
    deviceMemory?: number;
  };

  const explicitlyMobile =
    navigatorWithHints.userAgentData?.mobile === true;

  const mobileUserAgent =
    /Android|iPhone|iPad|iPod|Mobile/i.test(
      navigator.userAgent,
    );

  const smallTouchDevice =
    window.matchMedia("(pointer: coarse)").matches &&
    Math.min(window.screen.width, window.screen.height) <= 900;

  const lowMemoryDevice =
    typeof navigatorWithHints.deviceMemory === "number" &&
    navigatorWithHints.deviceMemory <= 4;

  if (
    explicitlyMobile ||
    mobileUserAgent ||
    smallTouchDevice ||
    lowMemoryDevice
  ) {
    return "mobile";
  }

  return "desktop";
}

async function loadModel(): Promise<LoadedModel> {
  if (!modelPromise) {
    modelPromise = (async () => {
      const ort = await import("onnxruntime-web");
      const profile = getDeviceModelProfile();
      const settings = MODEL_SETTINGS[profile];

      ort.env.wasm.wasmPaths = "/ort/";
      ort.env.wasm.numThreads = 1;

      const [session, labelsResponse, calibrationResponse] =
        await Promise.all([
          ort.InferenceSession.create(settings.path, {
            executionProviders: ["wasm"],
            graphOptimizationLevel: "all",
            executionMode: "sequential",
          }),
          fetch("/models/labels.json"),
          fetch("/models/calibration.json"),
        ]);

      if (labelsResponse.ok) {
        labels = await labelsResponse.json();
      }

      if (calibrationResponse.ok) {
        const calibration =
          await calibrationResponse.json();

        temperature =
          Number(calibration.temperature) || 1;
      }

      console.info(
        `Emotion model: ${profile} (${settings.imageSize}x${settings.imageSize})`,
      );

      return {
        session,
        profile,
        imageSize: settings.imageSize,
      };
    })().catch((error) => {
      modelPromise = null;
      throw error;
    });
  }

  return modelPromise;
}

function preprocessFace(
  video: HTMLVideoElement,
  box: FaceBox,
  imageSize: number,
): Float32Array {
  if (!preprocessingCanvas) {
    preprocessingCanvas =
      document.createElement("canvas");

    preprocessingContext =
      preprocessingCanvas.getContext("2d", {
        willReadFrequently: true,
        alpha: false,
      });
  }

  preprocessingCanvas.width = imageSize;
  preprocessingCanvas.height = imageSize;

  const context = preprocessingContext;

  if (!context) {
    throw new Error("Canvas is unavailable.");
  }

  const padding =
    Math.max(box.width, box.height) * 0.15;

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

  context.clearRect(
    0,
    0,
    imageSize,
    imageSize,
  );

  context.drawImage(
    video,
    x,
    y,
    width,
    height,
    0,
    0,
    imageSize,
    imageSize,
  );

  const pixels = context.getImageData(
    0,
    0,
    imageSize,
    imageSize,
  ).data;

  const pixelCount = imageSize * imageSize;
  const tensor = new Float32Array(
    3 * pixelCount,
  );

  for (
    let index = 0;
    index < pixelCount;
    index++
  ) {
    const offset = index * 4;

    const gray =
      (
        0.299 * pixels[offset] +
        0.587 * pixels[offset + 1] +
        0.114 * pixels[offset + 2]
      ) / 255;

    tensor[index] =
      (gray - 0.485) / 0.229;

    tensor[pixelCount + index] =
      (gray - 0.456) / 0.224;

    tensor[pixelCount * 2 + index] =
      (gray - 0.406) / 0.225;
  }

  return tensor;
}

function softmax(logits: number[]): number[] {
  const scaled = logits.map(
    (value) => value / temperature,
  );

  const maximum = Math.max(...scaled);

  const exponentials = scaled.map(
    (value) => Math.exp(value - maximum),
  );

  const total = exponentials.reduce(
    (sum, value) => sum + value,
    0,
  );

  return exponentials.map(
    (value) => value / total,
  );
}

export async function prepareEmotionModel(): Promise<void> {
  await loadModel();
}

export async function getLoadedModelProfile():
Promise<ModelProfile> {
  const model = await loadModel();
  return model.profile;
}

export async function predictEmotion(
  video: HTMLVideoElement,
  box: FaceBox,
): Promise<EmotionPrediction> {
  const ort = await import("onnxruntime-web");
  const loadedModel = await loadModel();

  const inputData = preprocessFace(
    video,
    box,
    loadedModel.imageSize,
  );

  const inputTensor = new ort.Tensor(
    "float32",
    inputData,
    [
      1,
      3,
      loadedModel.imageSize,
      loadedModel.imageSize,
    ],
  );

  const results =
    await loadedModel.session.run({
      [loadedModel.session.inputNames[0]]:
        inputTensor,
    });

  const output =
    results[
      loadedModel.session.outputNames[0]
    ];

  const logits = Array.from(
    output.data as Float32Array,
  );

  const probabilities = softmax(logits);

  let bestIndex = 0;

  for (
    let index = 1;
    index < probabilities.length;
    index++
  ) {
    if (
      probabilities[index] >
      probabilities[bestIndex]
    ) {
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