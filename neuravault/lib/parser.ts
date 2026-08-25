import {
  extractText,
  getDocumentProxy,
} from "unpdf";

export type ParsedDocument = {
  text: string;
  pages: number | null;
  characters: number;
};

const textExtensions = [".txt", ".md", ".markdown"];

export async function parseDocument(
  file: File
): Promise<ParsedDocument> {
  const fileName = file.name.toLowerCase();

  if (fileName.endsWith(".pdf")) {
    return parsePDF(file);
  }

  if (
    textExtensions.some((extension) =>
      fileName.endsWith(extension)
    )
  ) {
    const text = await file.text();

    return {
      text: text.trim(),
      pages: null,
      characters: text.trim().length,
    };
  }

  throw new Error(
    "Unsupported file type. Upload a PDF, TXT or Markdown file."
  );
}

async function parsePDF(
  file: File
): Promise<ParsedDocument> {
  const arrayBuffer = await file.arrayBuffer();
  const bytes = new Uint8Array(arrayBuffer);

  const pdf = await getDocumentProxy(bytes, {
    maxImageSize: 16_777_216,
  });

  if (pdf.numPages > 100) {
    throw new Error(
      "The PDF cannot contain more than 100 pages."
    );
  }

  const result = await extractText(pdf, {
    mergePages: true,
  });

  const text = result.text.trim();

  return {
    text,
    pages: result.totalPages,
    characters: text.length,
  };
}