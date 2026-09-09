"use client";

import Link from "next/link";
import { Activity, Camera, Clock3, FileJson, FileText, ImagePlus, ScanFace, Trash2 } from "lucide-react";
import { useEffect, useState, type CSSProperties } from "react";
import { clearSessions, deleteSession, getSessions, type SessionRecord } from "@/lib/sessionStore";
import { exportSessionsJson, printSessionsPdf } from "@/lib/sessionReport";

const emotionColors: Record<string, string> = {
  angry: "#ff647c", disgust: "#a3e635", fear: "#c084fc", happy: "#fde047",
  neutral: "#67e8f9", sad: "#818cf8", surprise: "#fb923c",
};
const formatDuration = (seconds: number) => seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
const formatDate = (value: string) => new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));

export default function SessionAnalytics({ view }: { view: "dashboard" | "history" }) {
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [ready, setReady] = useState(false);
  const [reportError, setReportError] = useState("");
  useEffect(() => { setSessions(getSessions()); setReady(true); }, []);

  const totalSeconds = sessions.reduce((sum, item) => sum + item.durationSeconds, 0);
  const averageConfidence = sessions.length ? sessions.reduce((sum, item) => sum + item.averageConfidence, 0) / sessions.length : 0;
  const totals: Record<string, number> = {};
  sessions.forEach((session) => Object.entries(session.distribution).forEach(([emotion, count]) => { totals[emotion] = (totals[emotion] ?? 0) + count; }));
  const totalReadings = Object.values(totals).reduce((sum, value) => sum + value, 0);
  const leadingEmotion = Object.entries(totals).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "No data";
  const remove = (id: string) => { deleteSession(id); setSessions((items) => items.filter((item) => item.id !== id)); };
  const removeAll = () => { clearSessions(); setSessions([]); };
  const makePdf = () => { try { setReportError(""); printSessionsPdf(sessions); } catch (error) { setReportError(error instanceof Error ? error.message : "Could not open report."); } };

  return <main className="data-app"><div className="data-glow" />
    <header className="data-header"><Link href="/detect" className="data-brand" aria-label="Emora Vision detection"><span><ScanFace /></span><div><strong>Emora Vision</strong><small>Private expression intelligence</small></div></Link><nav aria-label="Primary navigation"><Link href="/detect">Detect</Link><Link href="/upload">Upload</Link><Link href="/dashboard" data-active={view === "dashboard"}>Dashboard</Link><Link href="/history" data-active={view === "history"}>History</Link></nav></header>
    <section className="data-content"><div className="data-title-row"><div><p className="data-kicker">Private analytics</p><h1>{view === "dashboard" ? "Session overview" : "Detection history"}</h1><p>Only expression statistics are saved in this browser. Camera frames are never stored.</p></div><div className="dashboard-actions"><Link href="/detect" className="data-primary"><Camera /> Live detection</Link><Link href="/upload" className="data-primary data-secondary"><ImagePlus /> Upload image</Link></div></div>
      <div className="metric-grid"><article><span><Activity /></span><small>Sessions</small><strong>{sessions.length}</strong><p>Completed locally</p></article><article><span><Clock3 /></span><small>Total runtime</small><strong>{formatDuration(totalSeconds)}</strong><p>Analysed on device</p></article><article><span><ScanFace /></span><small>Avg. confidence</small><strong>{(averageConfidence * 100).toFixed(0)}%</strong><p>Across all readings</p></article><article><span className="metric-orb" /><small>Top expression</small><strong className="capitalize">{leadingEmotion}</strong><p>{totalReadings.toLocaleString()} total readings</p></article></div>
      <div className="report-actions card-actions"><button type="button" onClick={() => exportSessionsJson(sessions)} disabled={!sessions.length}><FileJson /> Export JSON</button><button type="button" onClick={makePdf} disabled={!sessions.length}><FileText /> Save PDF</button>{view === "history" && <button type="button" className="danger-action" onClick={removeAll} disabled={!sessions.length}><Trash2 /> Clear all</button>}</div>{reportError && <p role="alert" className="report-error">{reportError}</p>}
      {view === "dashboard" ? <div className="data-two-column"><section className="data-card"><div className="card-heading"><div><small>Aggregate signals</small><h2>Emotion distribution</h2></div><span>{totalReadings} readings</span></div><div className="distribution-list">{Object.keys(emotionColors).map((emotion) => { const percentage = totalReadings ? ((totals[emotion] ?? 0) / totalReadings) * 100 : 0; return <div key={emotion}><div><span className="capitalize">{emotion}</span><strong>{percentage.toFixed(0)}%</strong></div><i><b style={{ width: `${percentage}%`, background: emotionColors[emotion] }} /></i></div>; })}</div></section><section className="data-card"><div className="card-heading"><div><small>Latest activity</small><h2>Recent sessions</h2></div><Link href="/history">View all</Link></div><SessionList sessions={sessions.slice(0, 4)} ready={ready} onDelete={remove} compact /></section></div>
      : <section className="data-card history-card"><div className="card-heading"><div><small>Browser storage</small><h2>All sessions</h2></div></div><SessionList sessions={sessions} ready={ready} onDelete={remove} /></section>}
    </section></main>;
}

function SessionList({ sessions, ready, onDelete, compact = false }: { sessions: SessionRecord[]; ready: boolean; onDelete: (id: string) => void; compact?: boolean }) {
  if (!ready) return <div className="empty-state"><span className="loading-mini" />Loading private sessions...</div>;
  if (!sessions.length) return <div className="empty-state"><ScanFace /><strong>No sessions yet</strong><p>Start live detection, then stop it to create your first private summary.</p><Link href="/detect">Run first session</Link></div>;
  return <div className="session-list">{sessions.map((session) => <article className="session-row" key={session.id}><span className="session-emotion" style={{ "--row-color": emotionColors[session.dominantEmotion] ?? "#67e8f9" } as CSSProperties}>{session.dominantEmotion.slice(0, 2).toUpperCase()}</span><div><strong className="capitalize">{session.dominantEmotion}</strong><small>{formatDate(session.createdAt)}</small></div><div className="session-stat"><small>Confidence</small><strong>{(session.averageConfidence * 100).toFixed(0)}%</strong></div><div className="session-stat"><small>Duration</small><strong>{formatDuration(session.durationSeconds)}</strong></div>{compact ? null : <div className="session-stat"><small>Readings</small><strong>{session.samples}</strong></div>}<button type="button" className="row-delete" onClick={() => onDelete(session.id)} aria-label={`Delete ${session.dominantEmotion} session`}><Trash2 /></button></article>)}</div>;
}
