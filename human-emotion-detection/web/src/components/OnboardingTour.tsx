"use client";

import { ArrowLeft, ArrowRight, Camera, HelpCircle, ImagePlus, LayoutDashboard, ShieldCheck, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const STORAGE_KEY = "emora-onboarding-complete-v1";

const steps = [
  {
    icon: Camera,
    kicker: "WELCOME TO EMORA VISION",
    title: "Understand facial expressions",
    text: "Emora Vision analyses facial expressions directly inside your browser.",
  },
  {
    icon: Camera,
    kicker: "LIVE DETECTION",
    title: "Use your camera",
    text: "Start live detection, face the camera naturally, and view expression confidence in real time.",
  },
  {
    icon: ImagePlus,
    kicker: "IMAGE ANALYSIS",
    title: "Upload individual or group photos",
    text: "Upload or drag and drop an image. The app detects multiple faces and shows confidence for each one.",
  },
  {
    icon: LayoutDashboard,
    kicker: "PRIVATE ANALYTICS",
    title: "Review your sessions",
    text: "The dashboard shows session history and emotion statistics. Camera frames are never saved.",
  },
];

export default function OnboardingTour() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (localStorage.getItem(STORAGE_KEY) !== "true") {
      const timer = window.setTimeout(() => setOpen(true), 450);
      return () => window.clearTimeout(timer);
    }
  }, []);

  useEffect(() => {
    function reopen() {
      setStep(0);
      setOpen(true);
    }
    window.addEventListener("emora:open-guide", reopen);
    return () => window.removeEventListener("emora:open-guide", reopen);
  }, []);

  useEffect(() => {
    function closeWithEscape(event: KeyboardEvent) {
      if (event.key === "Escape") finish();
    }
    if (open) window.addEventListener("keydown", closeWithEscape);
    return () => window.removeEventListener("keydown", closeWithEscape);
  });

  function finish(destination?: string) {
    localStorage.setItem(STORAGE_KEY, "true");
    setOpen(false);
    if (destination) router.push(destination);
  }

  const current = steps[step];
  const Icon = current.icon;
  const lastStep = step === steps.length - 1;

  return (
    <>
      {open && (
        <div className="fixed inset-0 z-[999] grid place-items-center bg-[#010308]/80 p-4 backdrop-blur-xl">
          <section
            className="relative w-full max-w-[520px] overflow-hidden rounded-[30px] border border-white/10 bg-[#08101d]/95 p-7 shadow-[0_35px_120px_rgba(0,0,0,.65)] sm:p-9"
            role="dialog"
            aria-modal="true"
            aria-labelledby="onboarding-title"
          >
            <div className="pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full bg-cyan-400/10 blur-3xl" />

            <button
              type="button"
              onClick={() => finish()}
              className="absolute right-5 top-5 grid h-9 w-9 place-items-center rounded-full border border-white/10 bg-white/5 text-slate-400 transition hover:bg-white/10 hover:text-white"
              aria-label="Close guide"
            >
              <X className="h-4 w-4" />
            </button>

            <div className="grid h-16 w-16 place-items-center rounded-2xl border border-cyan-300/20 bg-cyan-300/10 text-cyan-200 shadow-[0_0_38px_rgba(34,211,238,.13)]">
              <Icon className="h-7 w-7" />
            </div>

            <p className="mt-7 text-[10px] font-bold tracking-[.24em] text-cyan-300/80">
              {current.kicker}
            </p>
            <h2 id="onboarding-title" className="mt-3 text-3xl font-semibold tracking-[-.04em] text-white sm:text-4xl">
              {current.title}
            </h2>
            <p className="mt-4 text-sm leading-7 text-slate-400">{current.text}</p>

            {step === 0 && (
              <div className="mt-5 flex items-center gap-2 rounded-xl border border-emerald-300/10 bg-emerald-300/5 px-4 py-3 text-xs text-emerald-200/80">
                <ShieldCheck className="h-4 w-4" /> On-device processing protects your camera data.
              </div>
            )}

            <div className="mt-8 flex gap-2" aria-label="Guide progress">
              {steps.map((_, index) => (
                <span
                  key={index}
                  className={`h-1.5 flex-1 rounded-full transition-all ${index <= step ? "bg-cyan-300" : "bg-white/10"}`}
                />
              ))}
            </div>

            <div className="mt-7 flex items-center justify-between gap-3">
              <button
                type="button"
                onClick={() => step === 0 ? finish() : setStep((value) => value - 1)}
                className="flex min-h-11 items-center gap-2 rounded-full px-4 text-sm text-slate-400 transition hover:bg-white/5 hover:text-white"
              >
                {step === 0 ? "Skip" : <><ArrowLeft className="h-4 w-4" /> Back</>}
              </button>

              {lastStep ? (
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => finish("/upload")}
                    className="min-h-11 rounded-full border border-cyan-300/20 bg-cyan-300/10 px-4 text-sm font-semibold text-cyan-100"
                  >
                    Upload image
                  </button>
                  <button
                    type="button"
                    onClick={() => finish("/detect")}
                    className="flex min-h-11 items-center gap-2 rounded-full bg-cyan-300 px-5 text-sm font-bold text-slate-950"
                  >
                    Start live <Camera className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setStep((value) => value + 1)}
                  className="flex min-h-11 items-center gap-2 rounded-full bg-cyan-300 px-5 text-sm font-bold text-slate-950"
                >
                  Next <ArrowRight className="h-4 w-4" />
                </button>
              )}
            </div>
          </section>
        </div>
      )}

      {!open && (
        <button
          type="button"
          onClick={() => { setStep(0); setOpen(true); }}
          className="fixed bottom-5 right-5 z-[90] grid h-11 w-11 place-items-center rounded-full border border-cyan-300/20 bg-[#0a1422]/90 text-cyan-200 shadow-xl backdrop-blur-md transition hover:scale-105 hover:bg-cyan-300/15"
          aria-label="Open app guide"
          title="App guide"
        >
          <HelpCircle className="h-5 w-5" />
        </button>
      )}
    </>
  );
}
