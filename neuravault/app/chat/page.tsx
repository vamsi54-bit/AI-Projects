import Sidebar from "@/components/Sidebar";
import ChatBox from "@/components/ChatBox";

export default function ChatPage() {
  return (
    <div className="app-shell">
      <Sidebar />

      <main className="chat-page">
        <header className="page-header">
          <div>
            <p className="eyebrow">AI ASSISTANT</p>
            <h1>Chat with NeuraVault</h1>
            <p>
              Ask questions about your documents and stored memories.
            </p>
          </div>

          <div className="model-status">
            <span />
            AI Ready
          </div>
        </header>

        <ChatBox />
      </main>
    </div>
  );
}