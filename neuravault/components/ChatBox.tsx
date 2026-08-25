"use client";

import {
  FormEvent,
  KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import {
  Bot,
  FileText,
  History,
  LoaderCircle,
  MessageSquare,
  Plus,
  Send,
  Sparkles,
  Trash2,
  User,
  X,
} from "lucide-react";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: string[];
};

type SavedConversation = {
  id: string;
  title: string;
  created_at?: string;
  updated_at?: string;
};

const suggestions = [
  {
    title: "Summarize documents",
    prompt: "Summarize the important points in my uploaded documents.",
  },
  {
    title: "Search memories",
    prompt: "What topics are covered in my uploaded documents?",
  },
  {
    title: "Explain my notes",
    prompt: "Explain the main concepts in my uploaded notes.",
  },
];

function normalizeMathMarkdown(content: string): string {
  return content
    .replace(/\\\[/g, "$$")
    .replace(/\\\]/g, "$$")
    .replace(/^\s*\[\s*$/gm, "$$")
    .replace(/^\s*\]\s*$/gm, "$$")
    .replace(/\\=/g, "=");
}

function makeId(): string {
  return `${Date.now()}-${Math.random()}`;
}

function asSources(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

export default function ChatBox() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<SavedConversation[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    void loadConversations();
  }, []);

  function createMessage(
    role: "user" | "assistant",
    content: string,
    sources: string[] = []
  ): Message {
    return { id: makeId(), role, content, sources };
  }

  async function readJson(response: Response) {
    const text = await response.text();
    if (!text) return null;
    try {
      return JSON.parse(text);
    } catch {
      throw new Error(`Server returned invalid JSON (${response.status}).`);
    }
  }

  async function loadConversations() {
    setHistoryLoading(true);
    setHistoryError("");

    try {
      const response = await fetch("/api/conversations", {
        method: "GET",
        cache: "no-store",
      });
      const data = await readJson(response);

      if (!response.ok) {
        throw new Error(data?.error || "Unable to load conversations.");
      }

      const list = Array.isArray(data)
        ? data
        : Array.isArray(data?.conversations)
          ? data.conversations
          : [];

      setConversations(list);
    } catch (error) {
      setHistoryError(
        error instanceof Error ? error.message : "Unable to load conversations."
      );
    } finally {
      setHistoryLoading(false);
    }
  }

  async function openConversation(id: string) {
    if (loading) return;

    setHistoryLoading(true);
    setHistoryError("");

    try {
      const response = await fetch(
        `/api/conversations?id=${encodeURIComponent(id)}`,
        { method: "GET", cache: "no-store" }
      );
      const data = await readJson(response);

      if (!response.ok) {
        throw new Error(data?.error || "Unable to open conversation.");
      }

      const savedMessages = Array.isArray(data)
        ? data
        : Array.isArray(data?.messages)
          ? data.messages
          : [];

      const restored: Message[] = savedMessages
        .filter(
          (item: unknown) =>
            typeof item === "object" &&
            item !== null &&
            ((item as { role?: unknown }).role === "user" ||
              (item as { role?: unknown }).role === "assistant") &&
            typeof (item as { content?: unknown }).content === "string"
        )
        .map((item: Record<string, unknown>) => ({
          id: typeof item.id === "string" ? item.id : String(item.id ?? makeId()),
          role: item.role as "user" | "assistant",
          content: item.content as string,
          sources: asSources(item.sources),
        }));

      setConversationId(id);
      setMessages(restored);
      setInput("");
      setHistoryOpen(false);
    } catch (error) {
      setHistoryError(
        error instanceof Error ? error.message : "Unable to open conversation."
      );
    } finally {
      setHistoryLoading(false);
    }
  }

  async function deleteConversation(id: string) {
    if (loading) return;

    try {
      const response = await fetch(
        `/api/conversations?id=${encodeURIComponent(id)}`,
        { method: "DELETE" }
      );
      const data = await readJson(response);

      if (!response.ok) {
        throw new Error(data?.error || "Unable to delete conversation.");
      }

      if (conversationId === id) startNewChat();
      await loadConversations();
    } catch (error) {
      setHistoryError(
        error instanceof Error ? error.message : "Unable to delete conversation."
      );
    }
  }

  function startNewChat() {
    setConversationId(null);
    setMessages([]);
    setInput("");
    setHistoryOpen(false);
  }

  async function sendMessage(messageText: string) {
    const cleanMessage = messageText.trim();
    if (!cleanMessage || loading) return;

    const history = messages.slice(-8).map((message) => ({
      role: message.role,
      content: message.content,
    }));

    setMessages((current) => [
      ...current,
      createMessage("user", cleanMessage),
    ]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: cleanMessage,
          history,
          conversationId,
        }),
      });
      const data = await readJson(response);

      if (!response.ok) {
        throw new Error(data?.error || "Unable to generate a response.");
      }
      if (!data?.answer) {
        throw new Error("The AI returned an empty response.");
      }

      if (typeof data.conversationId === "string") {
        setConversationId(data.conversationId);
      }

      setMessages((current) => [
        ...current,
        createMessage("assistant", data.answer, asSources(data.sources)),
      ]);

      await loadConversations();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error.";

      setMessages((current) => [
        ...current,
        createMessage(
          "assistant",
          `Sorry, something went wrong: ${errorMessage}`
        ),
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage(input);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendMessage(input);
    }
  }

  return (
    <section className="chat-container">
      <header className="chat-toolbar">
        <div className="assistant-information">
          <Bot size={20} />
          <div>
            <strong>NeuraVault Assistant</strong>
            <span className="assistant-status"><i />Online</span>
          </div>
        </div>

        <div className="chat-toolbar-actions">
          <button type="button" onClick={startNewChat} disabled={loading}>
            <Plus size={16} /> New chat
          </button>

          <div className="conversation-history-wrapper">
            <button
              type="button"
              onClick={() => {
                setHistoryOpen((current) => !current);
                if (!historyOpen) void loadConversations();
              }}
            >
              <History size={16} /> History
            </button>

            {historyOpen && (
              <div className="conversation-history-panel">
                <div className="history-panel-header">
                  <strong>Recent conversations</strong>
                  <button type="button" onClick={() => setHistoryOpen(false)} aria-label="Close history">
                    <X size={16} />
                  </button>
                </div>

                {historyLoading ? (
                  <div className="history-state"><LoaderCircle className="spinner" size={18} /> Loading...</div>
                ) : historyError ? (
                  <div className="history-error">{historyError}</div>
                ) : conversations.length === 0 ? (
                  <div className="history-state">No saved conversations yet.</div>
                ) : (
                  <div className="conversation-list">
                    {conversations.map((conversation) => (
                      <div
                        key={conversation.id}
                        className={`conversation-item ${conversation.id === conversationId ? "active" : ""}`}
                      >
                        <button type="button" onClick={() => void openConversation(conversation.id)}>
                          <MessageSquare size={16} />
                          <span>{conversation.title || "New conversation"}</span>
                        </button>
                        <button
                          type="button"
                          className="delete-conversation"
                          onClick={() => void deleteConversation(conversation.id)}
                          aria-label={`Delete ${conversation.title}`}
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="messages-area">
        {messages.length === 0 ? (
          <div className="chat-empty-state">
            <div className="assistant-logo"><Sparkles size={31} /></div>
            <h2>How can I help you?</h2>
            <p>Ask questions about your documents, notes and stored memories.</p>
            <div className="suggestion-grid">
              {suggestions.map((suggestion) => (
                <button
                  type="button"
                  key={suggestion.title}
                  disabled={loading}
                  onClick={() => void sendMessage(suggestion.prompt)}
                >
                  <FileText size={18} />
                  <span><strong>{suggestion.title}</strong><small>{suggestion.prompt}</small></span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="message-list">
            {messages.map((message) => (
              <article key={message.id} className={`chat-message ${message.role}`}>
                <div className="message-avatar">
                  {message.role === "user" ? <User size={19} /> : <Bot size={19} />}
                </div>
                <div className="message-content">
                  <strong>{message.role === "user" ? "You" : "NeuraVault"}</strong>
                  {message.role === "assistant" ? (
                    <div className="markdown-content">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm, remarkMath]}
                        rehypePlugins={[rehypeKatex]}
                      >
                        {normalizeMathMarkdown(message.content)}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <p>{message.content}</p>
                  )}
                  {message.sources && message.sources.length > 0 && (
                    <div className="message-sources">
                      <span>Sources:</span>
                      {message.sources.map((source, index) => (
                        <div key={`${source}-${index}`} className="source-badge">
                          <FileText size={13} />{source}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </article>
            ))}

            {loading && (
              <article className="chat-message assistant">
                <div className="message-avatar"><Bot size={19} /></div>
                <div className="message-content">
                  <strong>NeuraVault</strong>
                  <div className="typing-indicator">
                    <LoaderCircle size={18} className="spinner" /> Searching your vault...
                  </div>
                </div>
              </article>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <form className="chat-input-area" onSubmit={handleSubmit}>
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask NeuraVault anything..."
          rows={1}
          maxLength={4000}
          disabled={loading}
        />
        <button className="send-button" type="submit" disabled={!input.trim() || loading} aria-label="Send message">
          {loading ? <LoaderCircle size={19} className="spinner" /> : <Send size={19} />}
        </button>
      </form>

      <footer className="chat-footer">
        <span>Enter to send <strong> • </strong> Shift + Enter for a new line</span>
        <span>{input.length}/4000</span>
      </footer>
    </section>
  );
}