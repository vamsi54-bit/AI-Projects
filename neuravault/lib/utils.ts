export function chunkText(
  text: string,
  chunkSize = 1000,
  overlap = 150
): string[] {
  const cleanText = text
    .replace(/\r\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  if (!cleanText) {
    return [];
  }

  if (overlap >= chunkSize) {
    throw new Error(
      "Chunk overlap must be smaller than chunk size."
    );
  }

  const chunks: string[] = [];
  let start = 0;

  while (start < cleanText.length) {
    let end = Math.min(
      start + chunkSize,
      cleanText.length
    );

    if (end < cleanText.length) {
      const paragraphBreak =
        cleanText.lastIndexOf("\n\n", end);

      const sentenceBreak =
        cleanText.lastIndexOf(". ", end);

      const bestBreak = Math.max(
        paragraphBreak,
        sentenceBreak
      );

      if (
        bestBreak > start + chunkSize * 0.5
      ) {
        end = bestBreak + 1;
      }
    }

    const chunk = cleanText
      .slice(start, end)
      .trim();

    if (chunk) {
      chunks.push(chunk);
    }

    if (end >= cleanText.length) {
      break;
    }

    start = Math.max(end - overlap, start + 1);
  }

  return chunks;
}