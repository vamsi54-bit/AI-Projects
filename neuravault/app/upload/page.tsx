import "./upload.css";

import Sidebar from "@/components/Sidebar";
import FileUpload from "@/components/FileUpload";

export default function UploadPage() {
  return (
    <div className="app-shell">
      <Sidebar />

      <main className="upload-page">
        <header className="page-header upload-header">
          <div>
            <p className="eyebrow">
              KNOWLEDGE INGESTION
            </p>

            <h1>Upload a document</h1>

            <p>
              Add documents to your NeuraVault knowledge
              system.
            </p>
          </div>
        </header>

        <FileUpload />
      </main>
    </div>
  );
}