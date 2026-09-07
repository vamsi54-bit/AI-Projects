import { NextResponse } from "next/server";
import { z } from "zod";

const sessionSchema = z.object({
  durationSeconds: z.number().int().min(0).max(86_400),
  samples: z.number().int().min(1).max(1_000_000),
  averageConfidence: z.number().min(0).max(1),
  dominantEmotion: z.enum(["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]),
  distribution: z.record(z.string(), z.number().int().min(0)).refine(
    (value) => Object.keys(value).length <= 7,
    "Too many emotion labels.",
  ),
});

const responseHeaders = {
  "Cache-Control": "no-store",
  "X-Content-Type-Options": "nosniff",
};

export async function GET() {
  return NextResponse.json(
    { status: "ready", storage: "private-browser", version: 1 },
    { headers: responseHeaders },
  );
}

export async function POST(request: Request) {
  try {
    const payload: unknown = await request.json();
    const result = sessionSchema.safeParse(payload);
    if (!result.success) {
      return NextResponse.json(
        { error: "Invalid session data.", details: result.error.flatten().fieldErrors },
        { status: 400, headers: responseHeaders },
      );
    }

    return NextResponse.json(
      {
        session: {
          ...result.data,
          id: crypto.randomUUID(),
          createdAt: new Date().toISOString(),
        },
      },
      { status: 201, headers: responseHeaders },
    );
  } catch {
    return NextResponse.json(
      { error: "Request body must be valid JSON." },
      { status: 400, headers: responseHeaders },
    );
  }
}
