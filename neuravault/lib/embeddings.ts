import { GoogleGenAI } from "@google/genai";

const apiKey =
  process.env.GEMINI_API_KEY;

const embeddingModel =
  process.env.GEMINI_EMBEDDING_MODEL ||
  "gemini-embedding-2";

if (!apiKey) {
  throw new Error(
    "GEMINI_API_KEY is missing. Add it to .env.local."
  );
}

const gemini = new GoogleGenAI({
  apiKey,
});

async function generateEmbedding(
  content: string
): Promise<number[]> {
  const cleanContent = content.trim();

  if (!cleanContent) {
    throw new Error(
      "Cannot generate an embedding for empty text."
    );
  }

  const response =
    await gemini.models.embedContent({
      model: embeddingModel,
      contents: cleanContent,
      config: {
        outputDimensionality: 768,
      },
    });

  const embedding =
    response.embeddings?.[0]?.values;

  if (
    !embedding ||
    embedding.length !== 768
  ) {
    throw new Error(
      "Gemini returned an invalid embedding."
    );
  }

  return embedding;
}

export async function generateDocumentEmbedding(
  content: string,
  documentName: string
): Promise<number[]> {
  const preparedContent = `
title: ${documentName} | text: ${content}
  `.trim();

  return generateEmbedding(
    preparedContent
  );
}

export async function generateQueryEmbedding(
  query: string
): Promise<number[]> {
  const preparedQuery = `
task: question answering | query: ${query}
  `.trim();

  return generateEmbedding(
    preparedQuery
  );
}

export function embeddingToVector(
  embedding: number[]
): string {
  if (embedding.length !== 768) {
    throw new Error(
      "Embedding must contain 768 values."
    );
  }

  return `[${embedding.join(",")}]`;
}