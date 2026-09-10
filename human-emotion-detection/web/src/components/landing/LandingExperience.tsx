"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import EmotionCore from "./EmotionCore";
import { useEffect, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  BarChart3,
  Camera,
  Check,
  Eye,
  LockKeyhole,
  ScanFace,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
} from "lucide-react";

type Stage = "intro" | "guide" | "policy";

const POLICY_KEY = "emora.policy.v2.accepted";

const guide = [
  {
    icon: Camera,
    number: "01",
    title: "Choose a mode",
    text: "Use Live Detection for your camera, or Upload for an existing photo.",
  },
  {
    icon: ScanFace,
    number: "02",
    title: "Position the face",
    text: "Use a clear, front-facing face with steady lighting for a more reliable estimate.",
  },
  {
    icon: BarChart3,
    number: "03",
    title: "Read the signal",
    text: "Compare the expression, confidence scores, timeline and private session report.",
  },
];

const limitations = [
  [
    "Model accuracy",
    "The desktop model reached 82.26% accuracy and 0.7398 macro-F1 on the held-out FERPlus test set. Results are estimates, not facts.",
  ],
  [
    "Not a diagnosis",
    "Emora Vision cannot determine mental health, intentions, honesty or personality and must not be used for medical decisions.",
  ],
  [
    "Environmental limits",
    "Lighting, camera quality, face angle, motion, masks, glasses and partial obstruction can change predictions.",
  ],
  [
    "Human variation",
    "Expressions differ across people, cultures and situations. A visible expression may not represent what someone actually feels.",
  ],
  [
    "Privacy and consent",
    "Camera inference runs in the browser and frames are not saved. Only session statistics are stored locally. Get consent before analysing another person.",
  ],
];

export default function LandingExperience() {
  const router = useRouter();
  const [stage, setStage] = useState<Stage>("intro");
  const [accepted, setAccepted] = useState(false);
  const [checked, setChecked] = useState(false);

  useEffect(() => setAccepted(localStorage.getItem(POLICY_KEY) === "true"), []);

  const begin = () =>
    accepted ? router.push("/dashboard") : setStage("guide");

  function agree() {
    if (!checked) return;
    localStorage.setItem(POLICY_KEY, "true");
    router.push("/dashboard");
  }

  return (
    <main className={`home-app onboarding-stage-${stage}`}>
      <div className="home-aurora home-aurora-one" />
      <div className="home-aurora home-aurora-two" />
      <div className="home-grid" />

      <header className="home-header">
        <Link href="/" className="home-brand">
          <span className="home-brand-mark">
            <ScanFace />
          </span>
          <span>
            <strong>Emora Vision</strong>
            <small>Expression intelligence</small>
          </span>
        </Link>
        <nav>
          <button onClick={() => setStage("guide")}>How it works</button>
          <button onClick={() => setStage("policy")}>Limitations</button>
        </nav>
        <button className="home-nav-cta" onClick={begin}>
          {accepted ? "Dashboard" : "Begin"}
          <ArrowRight />
        </button>
      </header>

      <section className="landing-hero">
        <div className="home-copy">
          <div className="home-eyebrow">
            <span /> Private, real-time visual intelligence
          </div>
          <h1>
            See what a<br />
            <em>moment</em> feels like.
          </h1>
          <p>
            Read facial-expression signals through a live camera or uploaded
            image, directly inside your browser.
          </p>
          <div className="home-actions">
            <button className="home-primary" onClick={begin}>
              <Sparkles /> {accepted ? "Open dashboard" : "Discover Emora"}{" "}
              <ArrowRight />
            </button>
          </div>
          <div className="home-trust">
            <span>
              <ShieldCheck /> On-device processing
            </span>
            <span>
              <Eye /> Explainable mode
            </span>
            <span>
              <LockKeyhole /> Frames never stored
            </span>
          </div>
        </div>

        <div className="landing-3d">
          <EmotionCore />
        </div>
      </section>

      <section className="home-status">
        <div>
          <span className="status-dot" />
          <small>SYSTEM</small>
          <strong>READY</strong>
        </div>
        <div>
          <small>MODES</small>
          <strong>LIVE + IMAGE</strong>
        </div>
        <div>
          <small>PROCESSING</small>
          <strong>ON DEVICE</strong>
        </div>
        <div>
          <small>EXPRESSIONS</small>
          <strong>7 CLASSES</strong>
        </div>
      </section>

      <div className="home-horizon" />

      {stage !== "intro" && (
        <div
          className="onboarding-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="onboarding-title"
        >
          {stage === "guide" ? (
            <section className="guide-panel">
              <div className="onboarding-top">
                <button onClick={() => setStage("intro")}>
                  <ArrowLeft /> Back
                </button>
                <span>GUIDE · 01</span>
              </div>
              <div className="guide-heading">
                <p>THREE SIMPLE STEPS</p>
                <h2 id="onboarding-title">How Emora Vision works</h2>
                <span>
                  Analysis stays on this device from start to finish.
                </span>
              </div>
              <div className="guide-grid">
                {guide.map(({ icon: Icon, number, title, text }) => (
                  <article key={number}>
                    <div>
                      <Icon />
                      <small>{number}</small>
                    </div>
                    <h3>{title}</h3>
                    <p>{text}</p>
                  </article>
                ))}
              </div>
              <div className="onboarding-footer">
                <small>Next: read the product limitations</small>
                <button onClick={() => setStage("policy")}>
                  Continue <ArrowRight />
                </button>
              </div>
            </section>
          ) : (
            <section className="policy-panel">
              <div className="scroll-rod scroll-rod-top">
                <i />
              </div>
              <div className="policy-paper">
                <div className="policy-seal">
                  <ScanFace />
                </div>
                <p className="policy-kicker">利用規約 · RESPONSIBLE USE</p>
                <h2 id="onboarding-title">App limitations</h2>
                <p className="policy-intro">
                  Understand what this system can—and cannot—tell you before
                  continuing.
                </p>
                <div className="policy-rules">
                  {limitations.map(([title, text], index) => (
                    <article key={title}>
                      <span>{String(index + 1).padStart(2, "0")}</span>
                      <div>
                        <h3>{title}</h3>
                        <p>{text}</p>
                      </div>
                    </article>
                  ))}
                </div>
                <label className="policy-check">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(event) => setChecked(event.target.checked)}
                  />
                  <span>
                    <Check />
                  </span>
                  <p>
                    I understand these limitations and will use expression
                    estimates responsibly.
                  </p>
                </label>
                <div className="policy-actions">
                  <button
                    className="policy-back"
                    onClick={() => setStage("guide")}
                  >
                    <ArrowLeft /> Guide
                  </button>
                  <button
                    className="policy-agree"
                    disabled={!checked}
                    onClick={agree}
                  >
                    Agree and enter <ArrowRight />
                  </button>
                </div>
                <div className="policy-warning">
                  <TriangleAlert /> This application is an AI demonstration, not
                  a medical or psychological assessment tool.
                </div>
              </div>
              <div className="scroll-rod scroll-rod-bottom">
                <i />
              </div>
            </section>
          )}
        </div>
      )}
    </main>
  );
}