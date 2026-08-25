"use client";

import {
  ChangeEvent,
  DragEvent,
  useRef,
  useState,
} from "react";

import {
  CheckCircle2,
  File,
  FileText,
  LoaderCircle,
  UploadCloud,
  X,
} from "lucide-react";

type UploadedDocument = {
  id: string;
  name: string;
  type: string;
  size: number;
  pages: number | null;
  characters: number;
  chunks: number;
  createdAt: string;
  preview: string;
};

const MAX_FILE_SIZE = 10 * 1024 * 1024;

export default function FileUpload() {
  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);

  const [uploadedDocument, setUploadedDocument] =
    useState<UploadedDocument | null>(null);

  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const inputRef = useRef<HTMLInputElement>(null);

  function validateFile(file: File): boolean {
    const fileName = file.name.toLowerCase();

    const validType =
      fileName.endsWith(".pdf") ||
      fileName.endsWith(".txt") ||
      fileName.endsWith(".md") ||
      fileName.endsWith(".markdown");

    if (!validType) {
      setError(
        "Only PDF, TXT and Markdown files are supported."
      );
      return false;
    }

    if (file.size > MAX_FILE_SIZE) {
      setError("The file cannot exceed 10 MB.");
      return false;
    }

    if (file.size === 0) {
      setError("The selected file is empty.");
      return false;
    }

    setError("");
    return true;
  }

  function selectFile(file: File) {
    if (!validateFile(file)) {
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
    setUploadedDocument(null);
  }

  function handleFileChange(
    event: ChangeEvent<HTMLInputElement>
  ) {
    const file = event.target.files?.[0];

    if (file) {
      selectFile(file);
    }
  }

  function handleDragOver(
    event: DragEvent<HTMLDivElement>
  ) {
    event.preventDefault();
    setDragging(true);
  }

  function handleDragLeave(
    event: DragEvent<HTMLDivElement>
  ) {
    event.preventDefault();
    setDragging(false);
  }

  function handleDrop(
    event: DragEvent<HTMLDivElement>
  ) {
    event.preventDefault();
    setDragging(false);

    const file = event.dataTransfer.files?.[0];

    if (file) {
      selectFile(file);
    }
  }

  function removeFile() {
    setSelectedFile(null);
    setUploadedDocument(null);
    setError("");

    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  async function uploadFile() {
    if (!selectedFile || uploading) {
      return;
    }

    setUploading(true);
    setError("");
    setUploadedDocument(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Upload failed."
        );
      }

      setUploadedDocument(data.document);
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Unable to upload the document."
      );
    } finally {
      setUploading(false);
    }
  }

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) {
      return `${bytes} bytes`;
    }

    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }

    return `${(
      bytes /
      (1024 * 1024)
    ).toFixed(1)} MB`;
  }

  return (
    <section className="upload-panel">
      {!selectedFile ? (
        <div
          className={`upload-drop-zone ${
            dragging ? "dragging" : ""
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.txt,.md,.markdown"
            onChange={handleFileChange}
            hidden
          />

          <div className="upload-icon">
            <UploadCloud size={34} />
          </div>

          <h2>Upload your knowledge</h2>

          <p>
            Drag and drop a document here, or click to
            browse.
          </p>

          <button type="button">
            Select document
          </button>

          <small>
            PDF, TXT or Markdown • Maximum 10 MB
          </small>
        </div>
      ) : (
        <div className="selected-document">
          <div className="selected-file-information">
            <div className="selected-file-icon">
              {selectedFile.name
                .toLowerCase()
                .endsWith(".pdf") ? (
                <FileText size={26} />
              ) : (
                <File size={26} />
              )}
            </div>

            <div>
              <strong>{selectedFile.name}</strong>

              <span>
                {formatFileSize(selectedFile.size)}
              </span>
            </div>
          </div>

          <button
            type="button"
            className="remove-file-button"
            onClick={removeFile}
            disabled={uploading}
            aria-label="Remove selected file"
          >
            <X size={19} />
          </button>

          <button
            type="button"
            className="process-document-button"
            onClick={uploadFile}
            disabled={uploading}
          >
            {uploading ? (
              <>
                <LoaderCircle
                  className="spinner"
                  size={19}
                />
                Extracting text...
              </>
            ) : (
              <>
                <UploadCloud size={19} />
                Process document
              </>
            )}
          </button>
        </div>
      )}

      {error && (
        <div className="upload-error">
          <X size={18} />
          {error}
        </div>
      )}

      {uploadedDocument && (
        <div className="upload-success">
          <div className="success-heading">
            <CheckCircle2 size={22} />

            <div>
              <strong>
                Document processed successfully
              </strong>

              <span>{uploadedDocument.name}</span>
            </div>
          </div>

          <div className="document-statistics">
            <div>
              <strong>
                {formatFileSize(uploadedDocument.size)}
              </strong>
              <span>File size</span>
            </div>

            <div>
              <strong>
                {uploadedDocument.pages ?? "N/A"}
              </strong>
              <span>Pages</span>
            </div>

            <div>
              <strong>
                {uploadedDocument.characters.toLocaleString()}
              </strong>
              <span>Characters</span>
            </div>

            <div>
              <strong>{uploadedDocument.chunks}</strong>
              <span>Knowledge chunks</span>
            </div>
          </div>

          <div className="text-preview">
            <strong>Extracted text preview</strong>
            <p>{uploadedDocument.preview}</p>
          </div>
        </div>
      )}
    </section>
  );
}