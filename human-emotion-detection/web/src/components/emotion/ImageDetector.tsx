"use client";

import type { FaceDetector } from "@mediapipe/tasks-vision";
import { AlertCircle, ImagePlus, LoaderCircle, ScanFace, UploadCloud, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState, type CSSProperties, type DragEvent } from "react";

import {
  type EmotionPrediction,
  type FaceBox,
  predictEmotionFromImage,
  prepareEmotionModel,
} from "@/lib/emotionInference";

interface ImageResult {
  box: FaceBox;
  prediction: EmotionPrediction;
}

const MAX_FILE_SIZE = 12 * 1024 * 1024;
const MAX_FACES = 8;
const colors: Record<string, string> = {
  angry: "#ff647c", disgust: "#a3e635", fear: "#c084fc", happy: "#fde047",
  neutral: "#67e8f9", sad: "#818cf8", surprise: "#fb923c",
};

export default function ImageDetector() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const detectorRef = useRef<FaceDetector | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [dragging, setDragging] = useState(false);
  const [fileName, setFileName] = useState("");
  const [error, setError] = useState("");
  const [results, setResults] = useState<ImageResult[]>([]);

  const drawResults = useCallback((image: HTMLImageElement, items: ImageResult[]) => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    context.drawImage(image, 0, 0);
    const scale = Math.max(1, image.naturalWidth / 700);

    items.forEach(({ box, prediction }, index) => {
      const color = colors[prediction.emotion] ?? "#67e8f9";
      context.strokeStyle = color;
      context.lineWidth = 3 * scale;
      context.strokeRect(box.x, box.y, box.width, box.height);
      const label = `Face ${index + 1} · ${prediction.emotion} ${Math.round(prediction.confidence * 100)}%`;
      context.font = `600 ${14 * scale}px Arial`;
      const labelHeight = 26 * scale;
      const labelY = Math.max(labelHeight, box.y);
      context.fillStyle = "rgba(2,6,14,.88)";
      context.fillRect(box.x, labelY - labelHeight, context.measureText(label).width + 18 * scale, labelHeight);
      context.fillStyle = color;
      context.fillText(label, box.x + 9 * scale, labelY - 7 * scale);
    });
  }, []);

  useEffect(() => {
    void prepareEmotionModel().catch(() => undefined);
    return () => detectorRef.current?.close();
  }, []);

  async function getDetector() {
    if (detectorRef.current) return detectorRef.current;
    const { FaceDetector, FilesetResolver } = await import("@mediapipe/tasks-vision");
    const vision = await FilesetResolver.forVisionTasks("/mediapipe");
    detectorRef.current = await FaceDetector.createFromOptions(vision, {
      baseOptions: { modelAssetPath: "/models/face_detector.tflite" },
      runningMode: "IMAGE",
      minDetectionConfidence: 0.5,
      minSuppressionThreshold: 0.3,
    });
    return detectorRef.current;
  }

  async function analyseFile(file: File) {
    setError("");
    setResults([]);
    if (!file.type.startsWith("image/")) {
      setError("Choose a JPG, PNG, WEBP, or another image file.");
      setStatus("error");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setError("The image must be smaller than 12 MB.");
      setStatus("error");
      return;
    }

    setStatus("loading");
    setFileName(file.name);
    const url = URL.createObjectURL(file);
    try {
      const image = new Image();
      image.decoding = "async";
      image.src = url;
      await image.decode();
      drawResults(image, []);

      const [detector] = await Promise.all([getDetector(), prepareEmotionModel()]);
      const boxes = detector.detect(image).detections
        .map((item) => item.boundingBox)
        .filter((box): box is NonNullable<typeof box> => Boolean(box))
        .sort((a, b) => b.width * b.height - a.width * a.height)
        .slice(0, MAX_FACES);

      if (!boxes.length) {
        setError("No clear face found. Try a brighter, front-facing photo.");
        setStatus("error");
        return;
      }

      const predictions: ImageResult[] = [];
      for (const box of boxes) {
        const faceBox = { x: box.originX, y: box.originY, width: box.width, height: box.height };
        predictions.push({
          box: faceBox,
          prediction: await predictEmotionFromImage(
            image, image.naturalWidth, image.naturalHeight, faceBox,
          ),
        });
      }
      setResults(predictions);
      drawResults(image, predictions);
      setStatus("done");
    } catch (cause) {
      console.error(cause);
      setError("The image could not be analysed. Please try another photo.");
      setStatus("error");
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  function reset() {
    setStatus("idle");
    setError("");
    setFileName("");
    setResults([]);
    if (inputRef.current) inputRef.current.value = "";
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files[0];
    if (file) void analyseFile(file);
  }

  return (
    <main className="upload-app">
      <header className="data-header">
        <Link className="data-brand" href="/">
          <span><ScanFace /></span>
          <div><strong>Emora Vision</strong><small>Image intelligence</small></div>
        </Link>
        <nav>
          <Link href="/detect">Live camera</Link>
          <Link data-active="true" href="/upload">Image upload</Link>
          <Link href="/dashboard">Dashboard</Link>
        </nav>
      </header>

      <section className="upload-shell">
        <div className="upload-heading">
          <p className="data-kicker">STATIC IMAGE ANALYSIS</p>
          <h1>Understand every face in one frame.</h1>
          <p>Drop a group photo or portrait. Processing stays inside your browser.</p>
        </div>

        {status === "idle" ? (
          <div
            className={`drop-zone ${dragging ? "is-dragging" : ""}`}
            onClick={() => inputRef.current?.click()}
            onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDragOver={(event) => event.preventDefault()}
            onDrop={onDrop}
            role="button"
            tabIndex={0}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") inputRef.current?.click();
            }}
          >
            <div className="upload-orb"><UploadCloud /></div>
            <h2>Drop your image here</h2>
            <p>or click to browse · JPG, PNG or WEBP · maximum 12 MB</p>
            <button type="button"><ImagePlus /> Choose image</button>
            <input
              ref={inputRef}
              hidden
              type="file"
              accept="image/*"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void analyseFile(file);
              }}
            />
          </div>
        ) : (
          <div className="image-workspace">
            <section className="image-preview glass-panel">
              <div className="image-toolbar">
                <div><span>{fileName}</span><small>{results.length} face{results.length === 1 ? "" : "s"} detected</small></div>
                <button onClick={reset} type="button" aria-label="Choose another image"><X /></button>
              </div>
              <div className="canvas-wrap">
                <canvas ref={canvasRef} />
                {status === "loading" && (
                  <div className="image-loading"><LoaderCircle /><strong>Analysing faces</strong></div>
                )}
              </div>
            </section>

            <aside className="face-results glass-panel">
              <p className="data-kicker">DETECTION RESULTS</p>
              {error && <div className="upload-error"><AlertCircle />{error}</div>}
              {results.map(({ prediction }, index) => {
                const sorted = Object.entries(prediction.probabilities)
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 3);
                return (
                  <article key={index} style={{ "--face-color": colors[prediction.emotion] } as CSSProperties}>
                    <div className="face-result-title">
                      <span>Face {index + 1}</span>
                      <strong>{prediction.emotion}</strong>
                      <b>{Math.round(prediction.confidence * 100)}%</b>
                    </div>
                    {sorted.map(([emotion, confidence]) => (
                      <div className="face-score" key={emotion}>
                        <div><span>{emotion}</span><small>{Math.round(confidence * 100)}%</small></div>
                        <i><b style={{ width: `${confidence * 100}%` }} /></i>
                      </div>
                    ))}
                  </article>
                );
              })}
              <button className="analyse-another" onClick={reset} type="button">Analyse another image</button>
            </aside>
          </div>
        )}
      </section>
    </main>
  );
}
