import { useState } from 'react';
import { Icon } from './Icon';
import { useRecorder } from '../hooks/useRecorder';
export function Dock({ enabled, generating, sessionId, sendMessage, preview }: { enabled: boolean; generating: boolean; sessionId: string | null; sendMessage: (text: string) => boolean; preview: boolean }) {
  const [draft, setDraft] = useState('');
  const recorder = useRecorder(enabled && !generating && !preview, sessionId, setDraft);
  const recording = recorder.status === 'recording';
  const busy = recorder.status !== 'idle';
  function send(event: React.FormEvent) {
    event.preventDefault();
    if (enabled && !busy && !generating && !preview && sendMessage(draft)) setDraft('');
  }
  return <div className="dock-wrap"><section className="control-dock backdrop-blur-xl" aria-label="Conversation controls" aria-describedby="dock-note">
    <form className="input-row" onSubmit={send}>
      <button type="button" disabled={recording ? false : !enabled || generating || preview || busy || !!draft.trim() || !recorder.available} onClick={recording ? recorder.stop : recorder.start} className={`mic-button bg-linear-to-br from-[#8B5CF6] to-[#EC4899] ${recording ? 'is-recording' : ''}`} aria-label={recording ? 'Stop recording and transcribe' : 'Record a question'} title={draft.trim() ? 'Send or clear your draft before recording' : 'Record up to 60 seconds'}>{recording ? <span className="record-stop"/> : <Icon name="mic" size={23}/>}</button>
      <label className="sr-only" htmlFor="message">Message the Supervisor</label>
      <input id="message" disabled={!enabled || generating || preview || busy} value={draft} onChange={event => setDraft(event.target.value)} maxLength={1200} type="text" placeholder={recording ? `Recording… ${recorder.seconds}s / 60s` : recorder.status === 'transcribing' ? 'Transcribing your question…' : 'Ask your Supervisor…'} autoComplete="off"/>
      <button type="button" disabled className="icon-button" aria-label="Attach a file unavailable" title="File uploads arrive in a later day"><Icon name="attach"/></button>
      <button type="submit" disabled={!enabled || generating || preview || busy || !draft.trim()} className="send-button" aria-label="Send message"><Icon name="arrow"/></button>
    </form>
    <div className="dock-bottom"><div className="preference-controls"><label>Mode<select disabled defaultValue="quick" aria-label="Conversation mode"><option value="quick">Quick</option><option value="team">Team</option></select></label><span className="dock-scope">Supervisor only</span></div><div className="playback-controls">{busy ? <button className="secondary-button" onClick={recorder.cancel}>Cancel recording</button> : <span className="draft-count">{draft.length}/1200</span>}<button disabled className="stop-button" title="Response interruption arrives later"><span/>Stop</button><button disabled className="icon-button" aria-label="Mute unavailable"><Icon name="sound" size={18}/></button><label className="sr-only" htmlFor="volume">Volume</label><input disabled id="volume" type="range" min="0" max="100" defaultValue="70"/></div></div>
    <p id="dock-note" role="status">{preview ? 'Avatar preview · return to Live workspace to chat.' : recording ? `Recording ${recorder.seconds}s / 60s · click the microphone to finish.` : recorder.status === 'requesting' ? 'Allow microphone access in your browser. You can cancel anytime.' : recorder.status === 'transcribing' ? 'Transcribing with Groq…' : recorder.message || (!enabled ? 'Connect the API with your Groq key to start.' : !recorder.available ? 'Voice needs a supported browser on localhost or HTTPS. Text chat is ready.' : 'Mic: record → review transcript → send. Audio goes to Groq for transcription.')}</p>
  </section></div>;
}
