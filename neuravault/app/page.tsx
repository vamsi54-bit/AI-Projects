export default function HomePage() {
  return (
    <main className="home">
      <div className="hero">
        <span className="badge">AI-Powered Knowledge System</span>

        <h1>
          Welcome to <span>NeuraVault</span>
        </h1>

        <p>
          Upload your documents, store important memories and chat with your
          personal AI knowledge base.
        </p>

        <a href="/dashboard" className="primary-button">
          Open Dashboard
        </a>
      </div>
    </main>
  );
}