import { useState } from 'react';
import type { CSSProperties } from 'react';
import { Dock } from './components/Dock';
import { Conversation } from './components/Conversation';
import { Icon } from './components/Icon';
import { Avatar } from './components/Avatar';
import { agents, previewStates, type AgentId, type AgentProfile, type AgentState, type PreviewState } from './lib/agents';
import { useMotion } from './hooks/useMotion';
import { useConnection } from './hooks/useConnection';

function AgentCard({ agent, state, preview, motion, onState }: { agent: AgentProfile; state: AgentState; preview: boolean; motion: boolean; onState: (state: PreviewState) => void }) {
  const status = state === 'unavailable' ? 'Not active' : state[0].toUpperCase() + state.slice(1);
  return <article className={`agent-card card-${agent.id}`} style={{ '--agent-from': agent.from, '--agent-to': agent.to } as CSSProperties} data-state={state}>
    <span className={`agent-status status-${state}`}><span aria-hidden="true">{state === 'error' ? '!' : state === 'working' ? '◌' : state === 'speaking' ? '≋' : '○'}</span>{preview ? 'Preview · ' : ''}{status}</span>
    <Avatar agent={agent} state={state} motion={motion}/>
    <div className="agent-copy"><h3>{agent.name}</h3><p className="agent-role">{agent.role}</p>{agent.id === 'supervisor' && <p className="agent-detail">{agent.detail}</p>}</div>
    {preview && <label className="agent-fixture"><span className="sr-only">{agent.name} preview state</span><select value={state} onChange={event => onState(event.target.value as PreviewState)}>{previewStates.map(s => <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>)}</select></label>}
    <div className={`card-accent ${agent.gradient}`} aria-hidden="true"/>
  </article>;
}
export default function App() {
  const [preview, setPreview] = useState(false);
  const [fixtures, setFixtures] = useState<Record<AgentId, PreviewState>>({ supervisor: 'idle', researcher: 'idle', solver: 'idle', verifier: 'idle' });
  const motion = useMotion();
  const connection = useConnection();
  const active = ['connected', 'checking', 'connecting'].includes(connection.status);
  function setAll(state: PreviewState) { setFixtures({ supervisor: state, researcher: state, solver: state, verifier: state }); }
  return <div className="app-shell" data-motion={motion.running ? 'on' : 'off'}>
    <a className="skip-link" href="#workspace">Skip to workspace</a>
    <header className="site-header"><div className="brand"><span className="brand-icon bg-linear-to-br from-[#8B5CF6] to-[#EC4899]"><Icon name="spark"/></span><span>VoiceTeam<span>.</span></span></div><div className="header-actions"><span className="build-tag">WORKSPACE / 06</span><button className="motion-button" onClick={motion.toggle} aria-pressed={motion.enabled} disabled={motion.reduced} aria-label="Enable animations" title={motion.reduced ? 'Reduced motion is enabled in your system settings.' : 'Turn decorative motion on or off'}><span className={`motion-track ${motion.enabled ? 'is-on' : ''}`} aria-hidden="true"><i/></span>Motion {motion.enabled ? 'on' : 'off'}</button></div></header>
    <main id="workspace" tabIndex={-1}>
      <section className="intro"><div><p className="eyebrow">FOUR PERSPECTIVES. ONE CONVERSATION.</p><h1>A little team.<br className="mobile-break"/> A world of possibility<span>.</span></h1><p className="intro-copy">A space to think out loud, find clarity, and follow your curiosity.</p></div><div className="intro-mark" aria-hidden="true"><span className="bg-linear-to-br from-[#8B5CF6] to-[#EC4899]"/><span className="bg-linear-to-br from-[#06B6D4] to-[#3B82F6]"/><span className="bg-linear-to-br from-[#F43F5E] to-[#F59E0B]"/><span className="bg-linear-to-br from-[#10B981] to-[#84CC16]"/></div></section>
      <div className="workspace-toolbar"><div className="view-switch" aria-label="Workspace view"><button aria-pressed={!preview} onClick={() => setPreview(false)}>Live workspace</button><button aria-pressed={preview} onClick={() => setPreview(true)}>Avatar preview</button></div><span className={`connection-badge connection-${connection.status}`} role="status"><i/>{connection.status === 'connected' ? 'API connected' : connection.status === 'checking' ? 'Checking API' : connection.status === 'connecting' ? 'Connecting' : connection.status === 'error' ? 'Connection error' : 'API disconnected'}</span></div>
      {motion.reduced && <p className="motion-note">Your system’s reduced-motion preference is active. Avatars stay still.</p>}
      {preview && <section className="preview-controls" aria-label="Avatar preview controls"><div><strong>Visual preview · no live agent activity</strong><p>Try each expression. Speaking motion is decorative; there is no audio.</p></div><div className="fixture-buttons" aria-label="Set all preview states">{previewStates.map(state => <button key={state} aria-label={`Preview all ${state}`} aria-pressed={Object.values(fixtures).every(value => value === state)} onClick={() => setAll(state)}>{state[0].toUpperCase() + state.slice(1)}</button>)}</div></section>}
      <div className="workspace-grid">
        <section className="stage-panel backdrop-blur-xl" aria-labelledby="team-title"><div className="panel-heading"><div><p className="eyebrow">YOUR CIRCLE OF IDEAS</p><h2 id="team-title">Meet your team</h2></div><span className="small-badge">{preview ? 'PREVIEW' : '4 AGENT ROLES'}</span></div>
          <div className="stage-canvas"><div className="stage-orbit" aria-hidden="true"/><div className="stage-glow" aria-hidden="true"/>{agents.map(agent => <AgentCard key={agent.id} agent={agent} state={preview ? fixtures[agent.id] : agent.id === 'supervisor' && connection.status === 'connected' && connection.providerReady ? (connection.generating ? 'working' : connection.chatError ? 'error' : 'idle') : 'unavailable'} preview={preview} motion={motion.running} onState={state => setFixtures(current => ({ ...current, [agent.id]: state }))}/>)}</div>
          <p className="stage-caption"><Icon name="spark" size={16}/>{preview ? 'Original SVG characters. Preview states stay in this view.' : 'Chat with your Supervisor. Specialist collaboration arrives in later days.'}</p>
        </section>
        <aside className="conversation-panel backdrop-blur-xl" aria-labelledby="conversation-title"><div className="conversation-heading"><div className="flex items-center gap-3"><Icon name="chat" size={19}/><h2 id="conversation-title">Conversation</h2></div><span className="small-badge">{preview ? 'PREVIEW' : 'SUPERVISOR CHAT'}</span></div>
          {!preview && connection.messages.length > 0 ? <Conversation messages={connection.messages} error={connection.chatError} generating={connection.generating}/> : <div className="conversation-empty"><span className="empty-icon"><Icon name="spark" size={32}/></span><p className="eyebrow">LEAVE A LITTLE ROOM FOR WONDER</p><h3>What’s on your mind?</h3><p>{preview ? 'Explore your team’s personality here. Preview expressions never create messages or research results.' : 'Connect your API, then type a question or record your voice. Your Supervisor will answer here.'}</p><div className="suggestion-tags"><span>Explore a topic</span><span>Untangle an idea</span></div></div>}
          {!preview && <section className="connection-panel" aria-labelledby="connection-title"><div className="connection-title"><h3 id="connection-title">Local connection</h3><span className="port-tag">PORT 8010</span></div><p className="connection-message" role="status">{connection.message}</p><div className="connection-actions"><button className="primary-button" onClick={active ? connection.disconnect : connection.connect}>{active ? 'Disconnect' : connection.events.length ? 'Reconnect API' : 'Connect API'}<Icon name="arrow" size={16}/></button><button className="secondary-button" disabled={connection.status !== 'connected'} onClick={connection.checkHealth}>Check health</button></div>{connection.latency !== null && <p className="session-meta">Health round trip: {connection.latency} ms <span>· Session {connection.sessionId?.slice(0, 8)}</span></p>}
            {connection.events.length > 0 && <details className="event-log"><summary>Connection events ({connection.events.length})</summary><ol aria-label="Actual connection events">{connection.events.map(event => <li key={event.event_id}><span>{event.type === 'session.ready' ? 'Session opened' : event.type === 'health.pong' ? 'Health response received' : 'Protocol error'}</span><time dateTime={event.timestamp}>{new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</time></li>)}</ol></details>}
          </section>}
          <div className="attachment-placeholder"><Icon name="attach" size={18}/><div><strong>No attachment</strong><p>Image and PDF inputs arrive in later builds.</p></div></div>
        </aside>
      </div>
      <footer><span>Made for curious minds.</span><span>DAY 05 + 06 <span className="footer-dot">/</span> LOCAL DEVELOPMENT</span></footer>
    </main>
    <Dock enabled={connection.status === 'connected' && connection.providerReady} generating={connection.generating} sessionId={connection.sessionId} sendMessage={connection.sendMessage} preview={preview}/>
  </div>;
}
