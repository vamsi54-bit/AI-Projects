"use client";

import "./memories.css";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Database,
  LoaderCircle,
  Search,
  Upload,
} from "lucide-react";

import Link from "next/link";

import Sidebar from "@/components/Sidebar";
import MemoryCard, {
  type DocumentMemory,
} from "@/components/MemoryCard";

export default function MemoriesPage() {
  const [documents, setDocuments] = useState<
    DocumentMemory[]
  >([]);

  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] =
    useState<string | null>(null);

  const [error, setError] = useState("");

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        "/api/memories",
        {
          method: "GET",
          cache: "no-store",
        }
      );

      const responseText = await response.text();

      const data = responseText
        ? JSON.parse(responseText)
        : null;

      if (!response.ok) {
        throw new Error(
          data?.error ||
            "Unable to load documents."
        );
      }

      setDocuments(data?.documents ?? []);
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Unable to load documents."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const filteredDocuments = useMemo(() => {
    const query = search.toLowerCase().trim();

    if (!query) {
      return documents;
    }

    return documents.filter((document) =>
      document.name.toLowerCase().includes(query)
    );
  }, [documents, search]);

  async function deleteMemory(
    document: DocumentMemory
  ) {
    const confirmed = window.confirm(
      `Delete "${document.name}" and all of its knowledge chunks?`
    );

    if (!confirmed) {
      return;
    }

    setDeletingId(document.id);
    setError("");

    try {
      const response = await fetch(
        `/api/memories?id=${document.id}`,
        {
          method: "DELETE",
        }
      );

      const responseText = await response.text();

      const data = responseText
        ? JSON.parse(responseText)
        : null;

      if (!response.ok) {
        throw new Error(
          data?.error ||
            "Unable to delete the document."
        );
      }

      setDocuments((currentDocuments) =>
        currentDocuments.filter(
          (item) => item.id !== document.id
        )
      );
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Unable to delete the document."
      );
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="app-shell">
      <Sidebar />

      <main className="memories-page">
        <header className="memories-header">
          <div>
            <p className="eyebrow">MEMORY CORE</p>
            <h1>Your knowledge memories</h1>
            <p>
              Browse and manage documents stored in
              NeuraVault.
            </p>
          </div>

          <Link
            href="/upload"
            className="memory-upload-button"
          >
            <Upload size={18} />
            Upload document
          </Link>
        </header>

        <section className="memories-toolbar">
          <div className="memory-search">
            <Search size={19} />

            <input
              type="search"
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search documents..."
            />
          </div>

          <div className="memory-count">
            <Database size={17} />
            {documents.length} documents
          </div>
        </section>

        {error && (
          <div className="memories-error">
            {error}

            <button
              type="button"
              onClick={loadDocuments}
            >
              Try again
            </button>
          </div>
        )}

        {loading ? (
          <div className="memories-loading">
            <LoaderCircle
              size={29}
              className="spinner"
            />
            Loading memories...
          </div>
        ) : filteredDocuments.length > 0 ? (
          <section className="memories-grid">
            {filteredDocuments.map((document) => (
              <MemoryCard
                key={document.id}
                document={document}
                deleting={
                  deletingId === document.id
                }
                onDelete={deleteMemory}
              />
            ))}
          </section>
        ) : (
          <section className="memories-empty">
            <div>
              <Database size={33} />
            </div>

            <h2>
              {search
                ? "No matching documents"
                : "Your memory vault is empty"}
            </h2>

            <p>
              {search
                ? "Try a different search term."
                : "Upload a document to create your first knowledge memory."}
            </p>

            {!search && (
              <Link href="/upload">
                Upload your first document
              </Link>
            )}
          </section>
        )}
      </main>
    </div>
  );
}