"use client";

import { Activity, Clock3, RotateCcw, ScanFace, X } from "lucide-react";

export interface SessionSummaryData {
  durationSeconds: number;
  samples: number;
  averageConfidence: number;
  dominantEmotion: string;
  distribution: Record<string, number>;
}

interface SessionSummaryProps {
  summary: SessionSummaryData;
  onClose: () => void;
  onRestart: () => void;
}

function formatDuration(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

export default function SessionSummary({ summary, onClose, onRestart }: SessionSummaryProps) {
  return (
    <div className="summary-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="summary-card glass-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="summary-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button type="button" className="summary-close" onClick={onClose} aria-label="Close session summary">
          <X className="h-4 w-4" />
        </button>

        <div className="summary-icon"><ScanFace className="h-7 w-7" /></div>
        <p className="summary-kicker">Session complete</p>
        <h2 id="summary-title">Expression snapshot</h2>
        <p className="summary-lead">Your video stayed on this device. Only live model signals were analysed.</p>

        <div className="summary-primary">
          <span>Dominant expression</span>
          <strong>{summary.dominantEmotion}</strong>
        </div>

        <div className="summary-grid">
          <div><Clock3 /><span>Duration</span><strong>{formatDuration(summary.durationSeconds)}</strong></div>
          <div><Activity /><span>Confidence</span><strong>{(summary.averageConfidence * 100).toFixed(0)}%</strong></div>
          <div><ScanFace /><span>Readings</span><strong>{summary.samples}</strong></div>
        </div>

        <div className="summary-actions">
          <button type="button" className="summary-secondary" onClick={onClose}>Done</button>
          <button type="button" className="primary-control" onClick={onRestart}>
            <RotateCcw className="h-4 w-4" /> New session
          </button>
        </div>
      </section>
    </div>
  );
}
