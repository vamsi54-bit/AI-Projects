import {
  neon,
} from "@neondatabase/serverless";

import {
  chunkText,
} from "@/lib/utils";

import {
  embeddingToVector,
  generateDocumentEmbedding,
} from "@/lib/embeddings";

const databaseUrl =
  process.env.DATABASE_URL;

if (!databaseUrl) {
  throw new Error(
    "DATABASE_URL is missing. Add it to .env.local."
  );
}

export const sql = neon(databaseUrl);

/* ========================================
   SAVE DOCUMENT
======================================== */

type SaveDocumentInput = {
  userId: string;
  name: string;
  fileType: string;
  fileSize: number;
  pages: number | null;
  content: string;
  characterCount: number;
};

type SavedDocumentRow = {
  id: string;
  name: string;
  created_at: string;
};

export async function saveDocument(
  input: SaveDocumentInput
) {
  const rows = await sql`
    INSERT INTO documents (
      user_id,
      name,
      file_type,
      file_size,
      pages,
      content,
      character_count
    )
    VALUES (
      ${input.userId},
      ${input.name},
      ${input.fileType},
      ${input.fileSize},
      ${input.pages},
      ${input.content},
      ${input.characterCount}
    )
    RETURNING
      id,
      name,
      created_at
  `;

  const document =
    rows[0] as
      | SavedDocumentRow
      | undefined;

  if (!document) {
    throw new Error(
      "The document could not be saved."
    );
  }

  const chunks = chunkText(
    input.content
  );

  for (
    let index = 0;
    index < chunks.length;
    index++
  ) {
    const chunk = chunks[index];

    const embedding =
      await generateDocumentEmbedding(
        chunk,
        input.name
      );

    const vector =
      embeddingToVector(
        embedding
      );

    await sql`
      INSERT INTO document_chunks (
        document_id,
        chunk_index,
        content,
        embedding
      )
      VALUES (
        ${document.id},
        ${index},
        ${chunk},
        ${vector}::vector
      )
    `;
  }

  return {
    id: String(document.id),
    name: document.name,
    createdAt:
      document.created_at,
    chunkCount: chunks.length,
  };
}

/* ========================================
   GET USER DOCUMENTS
======================================== */

export type StoredDocument = {
  id: string;
  name: string;
  fileType: string;
  fileSize: number;
  pages: number | null;
  characterCount: number;
  chunkCount: number;
  createdAt: string;
};

type DocumentDatabaseRow = {
  id: string;
  name: string;
  file_type: string;
  file_size: number;
  pages: number | null;
  character_count: number;
  chunk_count: string;
  created_at: string;
};

export async function getDocuments(
  userId: string
): Promise<StoredDocument[]> {
  if (!userId) {
    throw new Error(
      "User ID is required."
    );
  }

  const rows = await sql`
    SELECT
      d.id,
      d.name,
      d.file_type,
      d.file_size,
      d.pages,
      d.character_count,
      d.created_at,
      COUNT(dc.id) AS chunk_count
    FROM documents d
    LEFT JOIN document_chunks dc
      ON dc.document_id = d.id
    WHERE d.user_id = ${userId}
    GROUP BY d.id
    ORDER BY d.created_at DESC
  `;

  return (
    rows as DocumentDatabaseRow[]
  ).map((row) => ({
    id: String(row.id),

    name: row.name,

    fileType:
      row.file_type,

    fileSize: Number(
      row.file_size
    ),

    pages:
      row.pages === null
        ? null
        : Number(row.pages),

    characterCount: Number(
      row.character_count
    ),

    chunkCount: Number(
      row.chunk_count
    ),

    createdAt:
      row.created_at,
  }));
}

/* ========================================
   DELETE USER DOCUMENT
======================================== */

export async function deleteDocument(
  documentId: string,
  userId: string
): Promise<boolean> {
  if (!/^\d+$/.test(documentId)) {
    throw new Error(
      "Invalid document ID."
    );
  }

  if (!userId) {
    throw new Error(
      "User ID is required."
    );
  }

  /*
   * The user_id condition prevents users
   * from deleting documents they do not own.
   *
   * Document chunks are removed through
   * the ON DELETE CASCADE foreign key.
   */
  const rows = await sql`
    DELETE FROM documents
    WHERE id = ${documentId}
      AND user_id = ${userId}
    RETURNING id
  `;

  return rows.length > 0;
}

/* ========================================
   DASHBOARD TYPES
======================================== */

export type DashboardData = {
  documentCount: number;
  chunkCount: number;
  characterCount: number;

  recentDocuments: {
    id: string;
    name: string;
    fileSize: number;
    pages: number | null;
    chunkCount: number;
    createdAt: string;
  }[];
};

type DashboardCountRow = {
  document_count: string;
  chunk_count: string;
  character_count: string;
};

type RecentDocumentRow = {
  id: string;
  name: string;
  file_size: number;
  pages: number | null;
  chunk_count: string;
  created_at: string;
};

/* ========================================
   GET USER DASHBOARD DATA
======================================== */

export async function getDashboardData(
  userId: string
): Promise<DashboardData> {
  if (!userId) {
    throw new Error(
      "User ID is required."
    );
  }

  /*
   * Count only the signed-in user's
   * documents, chunks and characters.
   */
  const countRows = await sql`
    SELECT
      (
        SELECT COUNT(*)
        FROM documents
        WHERE user_id = ${userId}
      ) AS document_count,

      (
        SELECT COUNT(*)
        FROM document_chunks dc
        INNER JOIN documents d
          ON d.id = dc.document_id
        WHERE d.user_id = ${userId}
      ) AS chunk_count,

      (
        SELECT COALESCE(
          SUM(character_count),
          0
        )
        FROM documents
        WHERE user_id = ${userId}
      ) AS character_count
  `;

  const counts =
    countRows[0] as
      | DashboardCountRow
      | undefined;

  if (!counts) {
    return {
      documentCount: 0,
      chunkCount: 0,
      characterCount: 0,
      recentDocuments: [],
    };
  }

  /*
   * Retrieve only the signed-in user's
   * five most recent documents.
   */
  const recentRows = await sql`
    SELECT
      d.id,
      d.name,
      d.file_size,
      d.pages,
      d.created_at,
      COUNT(dc.id) AS chunk_count
    FROM documents d
    LEFT JOIN document_chunks dc
      ON dc.document_id = d.id
    WHERE d.user_id = ${userId}
    GROUP BY d.id
    ORDER BY d.created_at DESC
    LIMIT 5
  `;

  return {
    documentCount: Number(
      counts.document_count
    ),

    chunkCount: Number(
      counts.chunk_count
    ),

    characterCount: Number(
      counts.character_count
    ),

    recentDocuments: (
      recentRows as RecentDocumentRow[]
    ).map((document) => ({
      id: String(document.id),

      name: document.name,

      fileSize: Number(
        document.file_size
      ),

      pages:
        document.pages === null
          ? null
          : Number(
              document.pages
            ),

      chunkCount: Number(
        document.chunk_count
      ),

      createdAt:
        document.created_at,
    })),
  };
}