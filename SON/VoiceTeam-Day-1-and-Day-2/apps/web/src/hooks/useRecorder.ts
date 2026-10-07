import { useCallback, useEffect, useRef, useState } from 'react';
import { apiUrl } from './useConnection';

type RecordingStatus = 'idle' | 'requesting' | 'recording' | 'transcribing';
const MAX_SECONDS = 60, MAX_BYTES = 5 * 1024 * 1024;
export function useRecorder(enabled: boolean, sessionId: string | null, onTranscript: (text: string) => void) {
  const [status, setStatus] = useState<RecordingStatus>('idle');
  const [seconds, setSeconds] = useState(0);
  const [message, setMessage] = useState('');
  const statusRef = useRef<RecordingStatus>('idle');
  const generation = useRef(0);
  const resources = useRef<{ stream?: MediaStream; recorder?: MediaRecorder; context?: AudioContext; timer?: ReturnType<typeof setInterval>; limit?: ReturnType<typeof setTimeout>; request?: AbortController }>({});
  const transcriptRef = useRef(onTranscript); transcriptRef.current = onTranscript;
  const available = typeof MediaRecorder !== 'undefined' && !!navigator.mediaDevices?.getUserMedia && typeof AudioContext !== 'undefined' && window.isSecureContext;
  const setPhase = useCallback((next: RecordingStatus) => { statusRef.current = next; setStatus(next); }, []);
  const release = useCallback(() => {
    const current = resources.current;
    clearInterval(current.timer); clearTimeout(current.limit);
    if (current.recorder) {
      current.recorder.onstop = null; current.recorder.ondataavailable = null; current.recorder.onerror = null;
      if (current.recorder.state !== 'inactive') current.recorder.stop();
    }
    current.stream?.getTracks().forEach(track => { track.onended = null; track.stop(); });
    if (current.context && current.context.state !== 'closed') void current.context.close();
    current.request?.abort();
    resources.current = {};
  }, []);
  const cancel = useCallback(() => {
    generation.current++; release(); setPhase('idle'); setSeconds(0); setMessage('');
  }, [release, setPhase]);
  const stop = useCallback(() => {
    const recorder = resources.current.recorder;
    if (statusRef.current === 'recording' && recorder?.state === 'recording') {
      setPhase('transcribing'); recorder.stop();
    }
  }, [setPhase]);
  const start = useCallback(async () => {
    if (!enabled || !sessionId || !available || statusRef.current !== 'idle') return;
    const id = ++generation.current;
    setPhase('requesting'); setMessage(''); setSeconds(0);
    const live = () => generation.current === id;
    const reject = (message: string) => { if (live()) { release(); setPhase('idle'); setMessage(message); } };
    try {
      const context = new AudioContext(); resources.current.context = context;
      await context.resume();
      if (!live()) return;
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true }, video: false });
      if (!live()) { stream.getTracks().forEach(t => t.stop()); return; }
      resources.current.stream = stream;
      const mimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'].find(type => MediaRecorder.isTypeSupported(type));
      if (!mimeType) { reject('This browser cannot record supported audio. Use Chrome or Edge.'); return; }
      const recorder = new MediaRecorder(stream, { mimeType, audioBitsPerSecond: 64000 });
      resources.current.recorder = recorder;
      const analyser = context.createAnalyser(); analyser.fftSize = 2048;
      context.createMediaStreamSource(stream).connect(analyser);
      const samples = new Float32Array(analyser.fftSize);
      let audibleSamples = 0, bytes = 0;
      const chunks: Blob[] = [], started = performance.now();
      recorder.ondataavailable = event => {
        if (!live()) return;
        if (event.data.size) { chunks.push(event.data); bytes += event.data.size; }
        if (bytes > MAX_BYTES) reject('Recording is too large. Try a shorter question.');
      };
      recorder.onerror = () => reject('Recording failed. Check your microphone and try again.');
      stream.getAudioTracks().forEach(track => { track.onended = () => reject('Microphone disconnected. Reconnect it and try again.'); });
      recorder.onstop = async () => {
        if (!live()) return;
        clearInterval(resources.current.timer); clearTimeout(resources.current.limit);
        stream.getTracks().forEach(track => { track.onended = null; track.stop(); });
        if (context.state !== 'closed') void context.close();
        if (performance.now() - started < 600 || audibleSamples < 3) { reject('No clear audio detected. Speak closer to the microphone and try again.'); return; }
        const audio = new Blob(chunks, { type: recorder.mimeType });
        if (audio.size < 100 || audio.size > MAX_BYTES) { reject('Recording was empty or too large. Please try again.'); return; }
        setPhase('transcribing');
        const controller = new AbortController(); resources.current.request = controller;
        resources.current.limit = setTimeout(() => controller.abort(), 50000);
        try {
          const response = await fetch(`${apiUrl}/transcribe`, { method: 'POST', headers: { 'Content-Type': audio.type, Authorization: `Bearer ${sessionId}` }, body: audio, signal: controller.signal });
          const body: unknown = await response.json();
          if (!live()) return;
          if (!response.ok) {
            const detail = typeof body === 'object' && body && 'detail' in body ? body.detail : null;
            const error = typeof detail === 'string' ? detail : typeof detail === 'object' && detail && 'message' in detail && typeof detail.message === 'string' ? detail.message : 'Transcription failed. Try recording again.';
            reject(error); return;
          }
          if (!body || typeof body !== 'object' || !('text' in body) || typeof body.text !== 'string' || !body.text.trim() || body.text.length > 1200) { reject('No usable transcript received. Please try again.'); return; }
          release(); setPhase('idle'); setMessage('Transcript ready. Review it, then press Send.');
          transcriptRef.current(body.text);
        } catch {
          reject(controller.signal.aborted ? 'Transcription timed out. Try a shorter recording.' : 'Could not transcribe. Check the API connection and try again.');
        }
      };
      resources.current.timer = setInterval(() => {
        if (!live()) return;
        analyser.getFloatTimeDomainData(samples);
        const rms = Math.sqrt(samples.reduce((sum, value) => sum + value * value, 0) / samples.length);
        if (rms > 0.008) audibleSamples++;
        setSeconds(Math.min(MAX_SECONDS, Math.floor((performance.now() - started) / 1000)));
      }, 100);
      resources.current.limit = setTimeout(() => { if (live()) stop(); }, MAX_SECONDS * 1000);
      recorder.start(250); setPhase('recording');
    } catch (error) {
      const name = error instanceof DOMException ? error.name : '';
      reject(name === 'NotAllowedError' ? 'Microphone permission was denied. Allow it in your browser site settings, then try again.' : name === 'NotFoundError' ? 'No microphone found. Connect one and try again.' : 'Could not start recording. Check microphone permissions and close other recording apps.');
    }
  }, [enabled, sessionId, available, setPhase, release, stop]);
  useEffect(() => { if (!enabled) cancel(); }, [enabled, cancel]);
  useEffect(() => { cancel(); return () => { generation.current++; release(); }; }, [sessionId, cancel, release]);
  useEffect(() => {
    const hide = () => { if (document.hidden && statusRef.current !== 'idle') cancel(); };
    document.addEventListener('visibilitychange', hide);
    return () => document.removeEventListener('visibilitychange', hide);
  }, [cancel]);
  return { status, seconds, message, available, start, stop, cancel };
}
