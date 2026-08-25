import {
  sql,
} from "@/lib/db";

import {
  embeddingToVector,
  generateQueryEmbedding,
} from "@/lib/embeddings";

export type RetrievedChunk = {
  id: string;
  documentId: string;
  documentName: string;
  chunkIndex: number;
  content: string;
  score: number;
  retrievalType:
    | "semantic"
    | "keyword";
};

type ChunkDatabaseRow = {
  id: string;
  document_id: string;
  document_name: string;
  chunk_index: number;
  content: string;
  score: number | string;
};

const ignoredWords = new Set([
  "what",
  "which",
  "where",
  "when",
  "why",
  "who",
  "how",
  "are",
  "is",
  "was",
  "were",
  "the",
  "this",
  "that",
  "these",
  "those",
  "and",
  "or",
  "but",
  "for",
  "from",
  "with",
  "into",
  "about",
  "your",
  "you",
  "my",
  "me",
  "our",
  "document",
  "documents",
  "uploaded",
  "contain",
  "contains",
  "included",
  "information",
  "question",
  "questions",
  "tell",
  "give",
  "show",
  "explain",
  "please",
]);

function mapRows(
  rows: ChunkDatabaseRow[],
  retrievalType:
    | "semantic"
    | "keyword"
): RetrievedChunk[] {
  return rows.map((row) => ({
    id: String(row.id),

    documentId: String(
      row.document_id
    ),

    documentName:
      row.document_name,

    chunkIndex: Number(
      row.chunk_index
    ),

    content: row.content,

    score: Number(row.score),

    retrievalType,
  }));
}

function buildKeywordQuery(
  query: string
): string {
  const words = query
    .toLowerCase()
    .replace(
      /[^a-z0-9\s]/g,
      " "
    )
    .split(/\s+/)
    .map((word) => word.trim())
    .filter(
      (word) =>
        word.length >= 3 &&
        !ignoredWords.has(word)
    );

  return Array.from(
    new Set(words)
  ).join(" | ");
}

/* ========================================
   USER-SPECIFIC SEMANTIC SEARCH
======================================== */

async function semanticSearch(
  query: string,
  userId: string,
  limit: number
): Promise<RetrievedChunk[]> {
  const embedding =
    await generateQueryEmbedding(
      query
    );

  const vector =
    embeddingToVector(
      embedding
    );

  const rows = await sql`
    SELECT
      dc.id,
      dc.document_id,
      d.name AS document_name,
      dc.chunk_index,
      dc.content,

      1 - (
        dc.embedding
        <=> ${vector}::vector
      ) AS score

    FROM document_chunks dc

    INNER JOIN documents d
      ON d.id = dc.document_id

    WHERE
      d.user_id = ${userId}
      AND dc.embedding IS NOT NULL

    ORDER BY
      dc.embedding
      <=> ${vector}::vector

    LIMIT ${limit}
  `;

  return mapRows(
    rows as ChunkDatabaseRow[],
    "semantic"
  ).filter(
    (chunk) =>
      chunk.score >= 0.3
  );
}

/* ========================================
   USER-SPECIFIC KEYWORD SEARCH
======================================== */

async function keywordSearch(
  query: string,
  userId: string,
  limit: number
): Promise<RetrievedChunk[]> {
  const searchQuery =
    buildKeywordQuery(query);

  if (!searchQuery) {
    return [];
  }

  const rows = await sql`
    SELECT
      dc.id,
      dc.document_id,
      d.name AS document_name,
      dc.chunk_index,
      dc.content,

      ts_rank(
        to_tsvector(
          'english',
          dc.content
        ),
        to_tsquery(
          'english',
          ${searchQuery}
        )
      ) AS score

    FROM document_chunks dc

    INNER JOIN documents d
      ON d.id = dc.document_id

    WHERE
      d.user_id = ${userId}
      AND
      to_tsvector(
        'english',
        dc.content
      )
      @@
      to_tsquery(
        'english',
        ${searchQuery}
      )

    ORDER BY score DESC

    LIMIT ${limit}
  `;

  return mapRows(
    rows as ChunkDatabaseRow[],
    "keyword"
  );
}

/* ========================================
   HYBRID RETRIEVAL
======================================== */

export async function retrieveRelevantChunks(
  query: string,
  userId: string,
  limit = 5
): Promise<RetrievedChunk[]> {
  const cleanQuery =
    query.trim();

  if (!cleanQuery) {
    return [];
  }

  if (!userId) {
    throw new Error(
      "User ID is required for document retrieval."
    );
  }

  let semanticResults:
    RetrievedChunk[] = [];

  try {
    semanticResults =
      await semanticSearch(
        cleanQuery,
        userId,
        limit
      );
  } catch (error) {
    console.error(
      "Semantic search failed; using keyword fallback:",
      error
    );
  }

  const keywordResults =
    await keywordSearch(
      cleanQuery,
      userId,
      limit
    );

  const combined = [
    ...semanticResults,
    ...keywordResults,
  ];

  const uniqueChunks =
    new Map<
      string,
      RetrievedChunk
    >();

  for (const chunk of combined) {
    const existing =
      uniqueChunks.get(
        chunk.id
      );

    /*
     * Prefer the semantic version when the
     * same chunk appears in both searches.
     */
    if (
      !existing ||
      chunk.retrievalType ===
        "semantic"
    ) {
      uniqueChunks.set(
        chunk.id,
        chunk
      );
    }
  }

  return Array.from(
    uniqueChunks.values()
  ).slice(0, limit);
}

/* ========================================
   CREATE AI CONTEXT
======================================== */

export function createRAGContext(
  chunks: RetrievedChunk[]
): string {
  if (chunks.length === 0) {
    return "";
  }

  return chunks
    .map(
      (
        chunk,
        index
      ) => `
SOURCE ${index + 1}
Document: ${chunk.documentName}
Chunk: ${chunk.chunkIndex + 1}
Retrieval: ${chunk.retrievalType}
Relevance: ${chunk.score.toFixed(3)}

${chunk.content}
      `.trim()
    )
    .join(
      "\n\n---\n\n"
    );
}

/* ========================================
   COMPLETE USER-SPECIFIC RAG RESULT
======================================== */

export async function retrieveContext(
  query: string,
  userId: string
) {
  const chunks =
    await retrieveRelevantChunks(
      query,
      userId
    );

  return {
    chunks,

    context:
      createRAGContext(
        chunks
      ),

    sources: Array.from(
      new Set(
        chunks.map(
          (chunk) =>
            chunk.documentName
        )
      )
    ),
  };
}