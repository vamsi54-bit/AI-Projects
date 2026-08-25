"use client";

import {
  Calendar,
  Database,
  FileText,
  Layers3,
  Trash2,
} from "lucide-react";

export type DocumentMemory = {
  id: string;
  name: string;
  fileType: string;
  fileSize: number;
  pages: number | null;
  characterCount: number;
  chunkCount: number;
  createdAt: string;
};

type MemoryCardProps = {
  document: DocumentMemory;
  deleting: boolean;
  onDelete: (document: DocumentMemory) => void;
};

export default function MemoryCard({
  document,
  deleting,
  onDelete,
}: MemoryCardProps) {
  function formatSize(bytes: number) {
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

  function formatDate(date: string) {
    return new Intl.DateTimeFormat("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(date));
  }

  return (
    <article className="memory-card">
      <div className="memory-card-header">
        <div className="memory-file-icon">
          <FileText size={25} />
        </div>

        <button
          type="button"
          className="memory-delete-button"
          onClick={() => onDelete(document)}
          disabled={deleting}
          aria-label={`Delete ${document.name}`}
        >
          <Trash2 size={17} />
        </button>
      </div>

      <h2 title={document.name}>
        {document.name}
      </h2>

      <p className="memory-file-type">
        {document.fileType}
      </p>

      <div className="memory-details">
        <div>
          <Database size={16} />
          <span>{formatSize(document.fileSize)}</span>
        </div>

        <div>
          <Layers3 size={16} />
          <span>
            {document.chunkCount} chunks
          </span>
        </div>

        <div>
          <FileText size={16} />
          <span>
            {document.pages
              ? `${document.pages} pages`
              : `${document.characterCount.toLocaleString()} characters`}
          </span>
        </div>
      </div>

      <footer className="memory-card-footer">
        <Calendar size={14} />
        <span>{formatDate(document.createdAt)}</span>
      </footer>
    </article>
  );
}