"use client";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import Link from "next/link";

import {
  ArrowRight,
  BrainCircuit,
  Database,
  FileText,
  LoaderCircle,
  MessageSquare,
  Search,
  Sparkles,
  Upload,
} from "lucide-react";

import Sidebar from "@/components/Sidebar";

type RecentDocument = {
  id: string;
  name: string;
  fileSize: number;
  pages: number | null;
  chunkCount: number;
  createdAt: string;
};

type DashboardData = {
  documentCount: number;
  chunkCount: number;
  characterCount: number;
  recentDocuments: RecentDocument[];
};

const emptyDashboard: DashboardData = {
  documentCount: 0,
  chunkCount: 0,
  characterCount: 0,
  recentDocuments: [],
};

const actions = [
  {
    title: "Chat with your knowledge",
    description:
      "Ask questions and receive answers from your uploaded documents.",
    href: "/chat",
    icon: MessageSquare,
  },
  {
    title: "Upload a document",
    description:
      "Add PDF, TXT and Markdown files to your knowledge vault.",
    href: "/upload",
    icon: Upload,
  },
  {
    title: "Browse memories",
    description:
      "View and manage documents remembered by NeuraVault.",
    href: "/memories",
    icon: BrainCircuit,
  },
];

export default function DashboardPage() {
  const [dashboard, setDashboard] =
    useState<DashboardData>(
      emptyDashboard
    );

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [search, setSearch] =
    useState("");

  useEffect(() => {
    async function loadDashboard() {
      try {
        setLoading(true);
        setError("");

        const response = await fetch(
          "/api/dashboard",
          {
            cache: "no-store",
          }
        );

        const responseText =
          await response.text();

        const data = responseText
          ? JSON.parse(responseText)
          : null;

        if (!response.ok) {
          throw new Error(
            data?.error ||
              "Unable to load dashboard."
          );
        }

        setDashboard({
          documentCount:
            data.documentCount ?? 0,
          chunkCount:
            data.chunkCount ?? 0,
          characterCount:
            data.characterCount ?? 0,
          recentDocuments:
            data.recentDocuments ?? [],
        });
      } catch (error) {
        setError(
          error instanceof Error
            ? error.message
            : "Unable to load dashboard."
        );
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  const filteredDocuments =
    useMemo(() => {
      const query =
        search.toLowerCase().trim();

      if (!query) {
        return dashboard.recentDocuments;
      }

      return dashboard.recentDocuments.filter(
        (document) =>
          document.name
            .toLowerCase()
            .includes(query)
      );
    }, [
      dashboard.recentDocuments,
      search,
    ]);

  function formatFileSize(bytes: number) {
    if (bytes < 1024) {
      return `${bytes} bytes`;
    }

    if (bytes < 1024 * 1024) {
      return `${(
        bytes / 1024
      ).toFixed(1)} KB`;
    }

    return `${(
      bytes /
      (1024 * 1024)
    ).toFixed(1)} MB`;
  }

  function formatDate(date: string) {
    return new Intl.DateTimeFormat(
      "en-IN",
      {
        dateStyle: "medium",
        timeStyle: "short",
      }
    ).format(new Date(date));
  }

  const statistics = [
    {
      title: "Stored Memories",
      value:
        dashboard.chunkCount.toLocaleString(),
      description:
        "Knowledge chunks available",
      icon: Database,
      color: "purple",
    },
    {
      title: "Documents",
      value:
        dashboard.documentCount.toLocaleString(),
      description:
        "Files stored in your vault",
      icon: FileText,
      color: "blue",
    },
    {
      title: "Characters Indexed",
      value:
        dashboard.characterCount.toLocaleString(),
      description:
        "Searchable text characters",
      icon: BrainCircuit,
      color: "green",
    },
  ];

  return (
    <div className="app-shell">
      <Sidebar />

      <main className="dashboard-content">
        <header className="dashboard-header">
          <div>
            <p className="eyebrow">
              <Sparkles size={16} />
              Personal AI Workspace
            </p>

            <h1>
              Welcome to your vault
            </h1>

            <p>
              Store, connect and retrieve
              your knowledge using AI.
            </p>
          </div>

          <Link
            href="/upload"
            className="header-button"
          >
            <Upload size={18} />
            Upload document
          </Link>
        </header>

        <section className="dashboard-search">
          <Search size={21} />

          <input
            type="search"
            value={search}
            onChange={(event) =>
              setSearch(
                event.target.value
              )
            }
            placeholder="Search recent documents..."
          />

          <span>Ctrl K</span>
        </section>

        {error && (
          <div className="dashboard-error">
            {error}
          </div>
        )}

        <section className="statistics-grid">
          {statistics.map(
            (statistic) => {
              const Icon =
                statistic.icon;

              return (
                <article
                  className="statistic-card"
                  key={statistic.title}
                >
                  <div
                    className={`card-icon ${statistic.color}`}
                  >
                    {loading ? (
                      <LoaderCircle
                        size={23}
                        className="spinner"
                      />
                    ) : (
                      <Icon size={23} />
                    )}
                  </div>

                  <div>
                    <p>
                      {statistic.title}
                    </p>

                    <h2>
                      {loading
                        ? "..."
                        : statistic.value}
                    </h2>

                    <span>
                      {
                        statistic.description
                      }
                    </span>
                  </div>
                </article>
              );
            }
          )}
        </section>

        <section>
          <div className="section-heading">
            <h2>Quick actions</h2>

            <p>
              Continue building your
              knowledge system.
            </p>
          </div>

          <div className="action-grid">
            {actions.map((action) => {
              const Icon = action.icon;

              return (
                <Link
                  href={action.href}
                  className="action-card"
                  key={action.title}
                >
                  <div className="action-icon">
                    <Icon size={24} />
                  </div>

                  <h3>{action.title}</h3>

                  <p>
                    {action.description}
                  </p>

                  <span>
                    Get started
                    <ArrowRight size={17} />
                  </span>
                </Link>
              );
            })}
          </div>
        </section>

        <section className="recent-documents-section">
          <div className="section-heading recent-heading">
            <div>
              <h2>Recent documents</h2>

              <p>
                Your latest knowledge
                uploads.
              </p>
            </div>

            <Link href="/memories">
              View all
              <ArrowRight size={16} />
            </Link>
          </div>

          {loading ? (
            <div className="recent-loading">
              <LoaderCircle
                size={24}
                className="spinner"
              />
              Loading documents...
            </div>
          ) : filteredDocuments.length >
            0 ? (
            <div className="recent-document-list">
              {filteredDocuments.map(
                (document) => (
                  <article
                    className="recent-document"
                    key={document.id}
                  >
                    <div className="recent-document-icon">
                      <FileText
                        size={21}
                      />
                    </div>

                    <div className="recent-document-name">
                      <strong>
                        {document.name}
                      </strong>

                      <span>
                        {formatDate(
                          document.createdAt
                        )}
                      </span>
                    </div>

                    <div className="recent-document-meta">
                      <span>
                        {formatFileSize(
                          document.fileSize
                        )}
                      </span>

                      <span>
                        {
                          document.chunkCount
                        }{" "}
                        chunks
                      </span>

                      {document.pages && (
                        <span>
                          {document.pages}{" "}
                          pages
                        </span>
                      )}
                    </div>
                  </article>
                )
              )}
            </div>
          ) : (
            <div className="empty-activity">
              <BrainCircuit size={38} />

              <h3>
                {search
                  ? "No matching documents"
                  : "Your vault is waiting"}
              </h3>

              <p>
                {search
                  ? "Try another search term."
                  : "Upload a document to create your first memory."}
              </p>

              {!search && (
                <Link href="/upload">
                  Add your first document
                </Link>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}