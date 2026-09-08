"use client";

import type { FaceDetector } from "@mediapipe/tasks-vision";
import { Activity, Camera, LoaderCircle, ScanFace, ShieldCheck, Square } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState, type CSSProperties } from "react";

import {
  type EmotionPrediction,
  type FaceBox,
  predictEmotion,
  prepareEmotionModel,
} from "@/lib/emotionInference";
import { PredictionSmoother } from "@/lib/inference/predictionSmoothing";
import { createSession } from "@/lib/sessionStore";
import SessionSummary, { type SessionSummaryData } from "./SessionSummary";

interface LiveResult {
  box: FaceBox;
  prediction: EmotionPrediction;
}

interface TimelinePoint {
  emotion: string;
  confidence: number;
  id: number;
}

const emotionColors: Record<string, string> = {
  angry: "#ff647c",
  disgust: "#a3e635",
  fear: "#c084fc",
  happy: "#fde047",
  neutral: "#67e8f9",
  sad: "#818cf8",
  surprise: "#fb923c",
};

const emotionCodes: Record<string, string> = {
  angry: "AN",
  disgust: "DG",
  fear: "FR",
  happy: "HP",
  neutral: "NT",
  sad: "SD",
  surprise: "SP",
};

function formatDuration(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  return `${String(minutes).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

export function WebcamDetector() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const detectorRef = useRef<FaceDetector | null>(null);
  const animationRef = useRef<number | null>(null);
  const busyRef = useRef(false);
  const lastRunRef = useRef(0);
  const timelineIdRef = useRef(0);
  const smootherRef = useRef(new PredictionSmoother(6));
  const sessionStatsRef = useRef({
    samples: 0,
    confidenceTotal: 0,
    emotions: {} as Record<string, number>,
  });
  const performanceProfileRef = useRef({ interval: 300, maxFaces: 3 });

  const [status, setStatus] = useState<"idle" | "loading" | "live" | "error">("idle");
  const [error, setError] = useState("");
  const [results, setResults] = useState<LiveResult[]>([]);
  const [latency, setLatency] = useState(0);
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [summary, setSummary] = useState<SessionSummaryData | null>(null);
  const [, setVideoReady] = useState(false);

  async function createDetector() {
    const { FaceDetector, FilesetResolver } = await import("@mediapipe/tasks-vision");
    const vision = await FilesetResolver.forVisionTasks("/mediapipe");

    return FaceDetector.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: "/models/face_detector.tflite",
      },
      runningMode: "VIDEO",
      minDetectionConfidence: 0.55,
      minSuppressionThreshold: 0.3,
    });
  }

  async function analyseFrame(timestamp: number) {
    const video = videoRef.current;
    const detector = detectorRef.current;

    if (!video || !detector || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return;

    const startedAt = performance.now();
    const detectionResult = detector.detectForVideo(video, timestamp);
    const boxes: FaceBox[] = detectionResult.detections
      .map((detection) => detection.boundingBox)
      .filter((box) => Boolean(box))
      .slice(0, performanceProfileRef.current.maxFaces)
      .map((box) => ({
        x: box!.originX,
        y: box!.originY,
        width: box!.width,
        height: box!.height,
      }));

    if (boxes.length === 0) {
      setResults([]);
      setLatency(Math.round(performance.now() - startedAt));
      return;
    }

    const rawPredictions = await Promise.all(
      boxes.map(async (box) => ({ box, prediction: await predictEmotion(video, box) })),
    );

    const predictions = rawPredictions.map((result, index) => ({
      ...result,
      prediction: index === 0 ? smootherRef.current.update(result.prediction) : result.prediction,
    }));

    const primary = predictions[0]?.prediction;
    if (primary) {
      const stats = sessionStatsRef.current;
      stats.samples += 1;
      stats.confidenceTotal += primary.confidence;
      stats.emotions[primary.emotion] = (stats.emotions[primary.emotion] ?? 0) + 1;
      timelineIdRef.current += 1;
      setTimeline((current) => [
        ...current.slice(-15),
        {
          emotion: primary.emotion,
          confidence: primary.confidence,
          id: timelineIdRef.current,
        },
      ]);
    }

    setResults(predictions);
    setLatency(Math.round(performance.now() - startedAt));
  }

  function beginLoop() {
    const loop = (timestamp: number) => {
      animationRef.current = requestAnimationFrame(loop);
      if (timestamp - lastRunRef.current < performanceProfileRef.current.interval || busyRef.current) return;

      lastRunRef.current = timestamp;
      busyRef.current = true;
      void analyseFrame(timestamp).finally(() => {
        busyRef.current = false;
      });
    };

    animationRef.current = requestAnimationFrame(loop);
  }

  async function startCamera() {
    try {
      setStatus("loading");
      setError("");
      setResults([]);
      setTimeline([]);
      setSummary(null);
      setElapsedSeconds(0);
      smootherRef.current.reset();
      sessionStatsRef.current = { samples: 0, confidenceTotal: 0, emotions: {} };

      const mobileDevice = window.matchMedia("(pointer: coarse)").matches ||
        (navigator.hardwareConcurrency || 8) <= 4;
      performanceProfileRef.current = mobileDevice
        ? { interval: 350, maxFaces: 1 }
        : { interval: 300, maxFaces: 3 };

      const stream = await navigator.mediaDevices.getUserMedia({
        video: mobileDevice
          ? {
              width: { ideal: 480, max: 640 },
              height: { ideal: 360, max: 480 },
              frameRate: { ideal: 20, max: 24 },
              facingMode: "user",
            }
          : { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
        audio: false,
      });
      streamRef.current = stream;

      const video = videoRef.current;
      if (!video) throw new Error("Video element was not created.");

      video.srcObject = stream;
      await video.play();
      setVideoReady(true);

      const [detector] = await Promise.all([createDetector(), prepareEmotionModel()]);
      detectorRef.current = detector;
      setStatus("live");
      beginLoop();
    } catch (caughtError) {
      stopCamera(false);
      setError(
        caughtError instanceof Error ? caughtError.message : "Unable to start emotion detection.",
      );
      setStatus("error");
    }
  }

  function stopCamera(showSummary = false) {
    const stats = sessionStatsRef.current;
    if (showSummary && stats.samples > 0) {
      let dominantEmotion = "neutral";
      let dominantCount = 0;
      for (const [emotion, count] of Object.entries(stats.emotions)) {
        if (count > dominantCount) {
          dominantEmotion = emotion;
          dominantCount = count;
        }
      }
      setSummary({
        durationSeconds: elapsedSeconds,
        samples: stats.samples,
        averageConfidence: stats.confidenceTotal / stats.samples,
        dominantEmotion,
        distribution: { ...stats.emotions },
      });
      void createSession({
        durationSeconds: elapsedSeconds,
        samples: stats.samples,
        averageConfidence: stats.confidenceTotal / stats.samples,
        dominantEmotion,
        distribution: { ...stats.emotions },
      });
    }
    if (animationRef.current !== null) cancelAnimationFrame(animationRef.current);
    animationRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    detectorRef.current?.close();
    detectorRef.current = null;
    busyRef.current = false;
    if (videoRef.current) videoRef.current.srcObject = null;
    setVideoReady(false);
    setResults([]);
    setTimeline([]);
    setStatus("idle");
  }

  useEffect(() => {
    if (status !== "live") return;
    const timer = window.setInterval(() => setElapsedSeconds((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [status]);

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      detectorRef.current?.close();
      if (animationRef.current !== null) cancelAnimationFrame(animationRef.current);
    };
  }, []);

  const primaryResult = results[0]?.prediction;
  const primaryColor = primaryResult
    ? emotionColors[primaryResult.emotion] ?? "#67e8f9"
    : "#67e8f9";
  const rankedProbabilities = primaryResult
    ? Object.entries(primaryResult.probabilities).sort((a, b) => b[1] - a[1])
    : [];

  return (
    <main className="cinema-app">
      <div className="camera-stage">
        <video
          ref={videoRef}
          muted
          playsInline
          data-active={status === "live" || status === "loading"}
          className="camera-feed"
        />
      </div>

      <div className="cinema-grid" />
      <div className="cinema-noise" />
      <div className="cinema-vignette" />

      <header className="product-header">
        <div className="flex items-center gap-4">
          <div className="brand-mark"><ScanFace className="h-5 w-5 text-cyan-200" /></div>
          <div className="header-copy">
            <p className="text-[15px] font-semibold tracking-[-0.02em]">Emora Vision</p>
            <p className="mt-0.5 text-xs text-slate-500">Neural expression intelligence</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <nav className="detector-nav" aria-label="Product navigation">
            <Link href="/dashboard">Dashboard</Link>
            <Link href="/history">History</Link>
          </nav>
          <div className="glass-panel privacy-copy flex items-center gap-2 rounded-full px-3.5 py-2 text-xs text-slate-300">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-300" />
            On-device processing
          </div>
          <div className="glass-panel flex items-center gap-2 rounded-full px-3.5 py-2 text-xs">
            <span className={status === "live" ? "live-dot" : "h-2 w-2 rounded-full bg-slate-600"} />
            {status === "live" ? "System live" : status === "loading" ? "Initializing" : "Standby"}
          </div>
        </div>
      </header>

      {(status === "idle" || status === "error") && (
        <section className="absolute inset-0 z-10 grid place-items-center px-6 text-center">
          <div className="-translate-y-10">
            <div className="idle-core">
              <Camera className="relative z-10 h-9 w-9 text-cyan-200" />
            </div>
            <p className="mt-14 text-xs font-medium uppercase tracking-[0.32em] text-cyan-200/70">
              Visual intelligence ready
            </p>
            <h1 className="mx-auto mt-4 max-w-xl text-4xl font-medium tracking-[-0.045em] text-white sm:text-6xl">
              Read the moment.
            </h1>
            <p className="mx-auto mt-4 max-w-md text-base leading-7 text-slate-400">
              Live facial-expression analysis, processed privately in your browser.
            </p>
          </div>
        </section>
      )}

      {status === "loading" && (
        <section className="absolute inset-0 z-20 grid place-items-center bg-[#02040a]/65 backdrop-blur-md">
          <div className="text-center">
            <div className="loading-ring mx-auto grid place-items-center">
              <LoaderCircle className="h-5 w-5 animate-spin text-cyan-100" />
            </div>
            <p className="mt-7 text-sm font-medium text-white">Preparing neural engine</p>
            <p className="mt-2 text-xs tracking-wide text-slate-500">Loading face detector and emotion model</p>
          </div>
        </section>
      )}

      {status === "live" && <div className="scan-beam" />}

      {status === "live" && results.length === 0 && (
        <div className="glass-panel absolute left-1/2 top-1/2 z-10 -translate-x-1/2 -translate-y-1/2 rounded-full px-5 py-3 text-sm text-slate-300">
          <span className="mr-2 inline-block h-2 w-2 animate-pulse rounded-full bg-cyan-300" />
          Looking for a face
        </div>
      )}

      <aside className="analysis-panel glass-panel">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">Current signal</p>
            <p className="mt-1 text-xs text-slate-500">
              {status === "live" ? `${formatDuration(elapsedSeconds)} · ${results.length} face${results.length === 1 ? "" : "s"} · ${latency} ms` : "Waiting for camera"}
            </p>
          </div>
          <Activity className="h-4 w-4 text-cyan-300/70" />
        </div>

        <div className="mt-5 flex items-center gap-4">
          <div className="emotion-orb" style={{ "--emotion-color": primaryColor } as CSSProperties}>
            <span className="relative z-10 text-sm font-bold">{primaryResult ? emotionCodes[primaryResult.emotion] : "--"}</span>
          </div>
          <div>
            <h2 className="text-3xl font-medium capitalize tracking-[-0.04em] text-white">
              {primaryResult?.emotion ?? "No signal"}
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              {primaryResult ? `${(primaryResult.confidence * 100).toFixed(1)}% model confidence` : "Begin detection to analyse"}
            </p>
          </div>
        </div>

        <div className="analysis-details mt-7 border-t border-white/[0.08] pt-5">
          <div className="space-y-3.5">
            {(rankedProbabilities.length ? rankedProbabilities : [["neutral", 0], ["happy", 0], ["surprise", 0], ["sad", 0]]).map(
              ([emotion, probability]) => {
                const color = emotionColors[emotion] ?? "#67e8f9";
                return (
                  <div key={emotion}>
                    <div className="mb-1.5 flex justify-between text-xs">
                      <span className="capitalize text-slate-300">{emotion}</span>
                      <span className="font-mono text-slate-500">{(Number(probability) * 100).toFixed(0)}%</span>
                    </div>
                    <div className="confidence-track">
                      <div className="confidence-fill" style={{ width: `${Number(probability) * 100}%`, "--bar-color": color } as CSSProperties} />
                    </div>
                  </div>
                );
              },
            )}
          </div>

          <div className="mt-6 border-t border-white/[0.08] pt-4">
            <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.18em] text-slate-500">
              <span>Signal history</span><span>Live</span>
            </div>
            <div className="mt-3 grid h-10 grid-cols-[repeat(16,minmax(0,1fr))] items-end gap-1">
              {timeline.length === 0
                ? Array.from({ length: 16 }).map((_, index) => <span key={index} className="h-1 rounded-full bg-white/[0.05]" />)
                : timeline.map((point) => (
                    <span
                      key={point.id}
                      className="timeline-bar"
                      title={`${point.emotion}: ${(point.confidence * 100).toFixed(0)}%`}
                      style={{ height: `${Math.max(18, point.confidence * 100)}%`, "--history-color": emotionColors[point.emotion] } as CSSProperties}
                    />
                  ))}
            </div>
          </div>
        </div>
      </aside>

      <div className="control-dock glass-panel">
        {status === "live" || status === "loading" ? (
          <button type="button" onClick={() => stopCamera(true)} className="primary-control stop" aria-label="Stop live detection">
            <Square className="h-4 w-4 fill-current" /> Stop session
          </button>
        ) : (
          <button type="button" onClick={startCamera} className="primary-control" aria-label="Start live detection">
            <Camera className="h-5 w-5" /> Start live detection
          </button>
        )}
      </div>

      {error && <div className="error-toast" role="alert">{error}</div>}
      {summary && (
        <SessionSummary
          summary={summary}
          onClose={() => setSummary(null)}
          onRestart={() => {
            setSummary(null);
            void startCamera();
          }}
        />
      )}
    </main>
  );
}

export default WebcamDetector;
