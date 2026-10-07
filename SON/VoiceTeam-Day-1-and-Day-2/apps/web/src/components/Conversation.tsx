import { useEffect, useRef } from 'react';
import type { Message } from '../hooks/useConnection';
export function Conversation({ messages, error, generating }: { messages: Message[]; error: string; generating: boolean }) {
  const log = useRef<HTMLDivElement>(null);
  const following = useRef(true);
  useEffect(() => { if (following.current && log.current) log.current.scrollTop = log.current.scrollHeight; }, [messages, generating]);
  return <div className="conversation-content">
    <div className="message-log" role="log" aria-label="Conversation messages" aria-live="off" ref={log} onScroll={() => { const node = log.current!; following.current = node.scrollHeight - node.scrollTop - node.clientHeight < 60; }}>
      {messages.map(message => <article key={message.id} className={`message message-${message.role}`}>
        <div className="message-heading"><strong>{message.role === 'user' ? 'You' : 'Supervisor'}</strong>{message.status === 'streaming' && <span>Writing…</span>}{message.status === 'failed' && <span>Incomplete</span>}</div>
        <p>{message.text || (message.status === 'streaming' ? 'Thinking…' : 'No answer received.')}</p>
      </article>)}
    </div>
    <span className="sr-only" role="status">{generating ? 'Supervisor is writing an answer.' : messages.length ? 'Response finished. Read it in the conversation.' : ''}</span>
    {error && <p className="chat-error" role="alert">{error}</p>}
    <p className="conversation-note">Recent conversation stays in this session. Reconnecting starts fresh.</p>
  </div>;
}
