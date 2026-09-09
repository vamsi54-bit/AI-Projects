import type { SessionRecord } from "@/lib/sessionStore";

const COLORS: Record<string, string> = {
  angry: "#ff647c", disgust: "#a3e635", fear: "#c084fc",
  happy: "#fde047", neutral: "#67e8f9", sad: "#818cf8", surprise: "#fb923c",
};

function summary(sessions: SessionRecord[]) {
  const distribution: Record<string, number> = {};
  let totalSeconds = 0;
  let confidenceTotal = 0;
  for (const session of sessions) {
    totalSeconds += session.durationSeconds;
    confidenceTotal += session.averageConfidence;
    for (const [emotion, count] of Object.entries(session.distribution)) {
      distribution[emotion] = (distribution[emotion] ?? 0) + count;
    }
  }
  const readings = Object.values(distribution).reduce((sum, value) => sum + value, 0);
  const dominantEmotion = Object.entries(distribution).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "No data";
  return {
    sessions: sessions.length,
    totalSeconds,
    readings,
    averageConfidence: sessions.length ? confidenceTotal / sessions.length : 0,
    dominantEmotion,
    distribution,
  };
}

function download(content: string, type: string, filename: string) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function escapeHtml(value: unknown) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
  })[character] ?? character);
}

export function exportSessionsJson(sessions: SessionRecord[]) {
  const date = new Date().toISOString().slice(0, 10);
  download(JSON.stringify({ generatedAt: new Date().toISOString(), summary: summary(sessions), sessions }, null, 2),
    "application/json", `emora-report-${date}.json`);
}

export function printSessionsPdf(sessions: SessionRecord[]) {
  const stats = summary(sessions);
  const total = Math.max(1, stats.readings);
  const distribution = Object.keys(COLORS).map((emotion) => {
    const count = stats.distribution[emotion] ?? 0;
    const percentage = count / total * 100;
    return `<div class="bar-row"><div><b>${escapeHtml(emotion)}</b><span>${percentage.toFixed(1)}% · ${count}</span></div><div class="track"><i style="width:${percentage}%;background:${COLORS[emotion]}"></i></div></div>`;
  }).join("");
  const timeline = [...sessions].reverse().map((session) => {
    const height = Math.max(12, Math.round(session.averageConfidence * 100));
    const color = COLORS[session.dominantEmotion] ?? COLORS.neutral;
    return `<div class="timeline-item"><div class="timeline-bar" style="height:${height}px;background:${color}"></div><small>${escapeHtml(session.dominantEmotion.slice(0, 3).toUpperCase())}</small></div>`;
  }).join("");
  const rows = sessions.map((session) => `<tr><td>${escapeHtml(new Date(session.createdAt).toLocaleString())}</td><td class="capitalize">${escapeHtml(session.dominantEmotion)}</td><td>${Math.round(session.averageConfidence * 100)}%</td><td>${session.durationSeconds}s</td><td>${session.samples}</td></tr>`).join("");
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>Emora Vision Report</title><style>
    *{box-sizing:border-box}body{font-family:Arial,sans-serif;color:#111827;margin:0;padding:32px;background:#fff}header{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid #111827;padding-bottom:18px}h1{margin:0;font-size:30px}h2{font-size:18px;margin:28px 0 14px}.muted{color:#64748b;font-size:12px}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:24px}.metric{border:1px solid #dbe2ea;border-radius:12px;padding:15px}.metric small{display:block;color:#64748b;text-transform:uppercase;font-size:10px;letter-spacing:1px}.metric b{font-size:24px;display:block;margin-top:8px}.capitalize{text-transform:capitalize}.grid{display:grid;grid-template-columns:1fr 1fr;gap:26px}.bar-row{margin:10px 0}.bar-row>div:first-child{display:flex;justify-content:space-between;text-transform:capitalize;font-size:12px}.track{height:7px;background:#e8edf3;border-radius:9px;margin-top:5px;overflow:hidden}.track i{display:block;height:100%}.timeline{height:130px;border-bottom:1px solid #cbd5e1;display:flex;align-items:flex-end;gap:5px;padding:0 5px}.timeline-item{flex:1;text-align:center;min-width:5px}.timeline-bar{width:100%;border-radius:4px 4px 0 0}.timeline-item small{font-size:7px;color:#64748b}table{border-collapse:collapse;width:100%;font-size:11px}th,td{text-align:left;border-bottom:1px solid #e2e8f0;padding:9px 6px}th{color:#475569}footer{margin-top:28px;padding-top:12px;border-top:1px solid #e2e8f0;font-size:10px;color:#64748b}@media print{body{padding:15mm}.no-print{display:none}}
  </style></head><body><header><div><h1>Emora Vision</h1><p>Private emotion-analysis session report</p></div><div class="muted">Generated ${escapeHtml(new Date().toLocaleString())}<br>Processing performed on-device</div></header>
  <section class="metrics"><div class="metric"><small>Sessions</small><b>${stats.sessions}</b></div><div class="metric"><small>Total runtime</small><b>${stats.totalSeconds}s</b></div><div class="metric"><small>Average confidence</small><b>${Math.round(stats.averageConfidence * 100)}%</b></div><div class="metric"><small>Top expression</small><b class="capitalize">${escapeHtml(stats.dominantEmotion)}</b></div></section>
  <div class="grid"><section><h2>Emotion distribution</h2>${distribution}</section><section><h2>Session timeline</h2><div class="timeline">${timeline || '<p class="muted">No sessions</p>'}</div></section></div>
  <section><h2>Confidence summary</h2><p>${stats.readings.toLocaleString()} readings across ${stats.sessions} sessions, with ${Math.round(stats.averageConfidence * 100)}% average confidence.</p></section>
  <section><h2>Session details</h2><table><thead><tr><th>Date</th><th>Dominant emotion</th><th>Confidence</th><th>Duration</th><th>Readings</th></tr></thead><tbody>${rows}</tbody></table></section>
  <footer>This report describes model estimates, not medical or psychological conclusions. Camera frames were not stored.</footer><script>window.addEventListener('load',()=>setTimeout(()=>window.print(),250));<\/script></body></html>`;
  const url = URL.createObjectURL(new Blob([html], { type: "text/html" }));
  const report = window.open(url, "_blank");
  if (!report) {
    URL.revokeObjectURL(url);
    throw new Error("Allow pop-ups to generate the PDF report.");
  }
  report.opener = null;
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
