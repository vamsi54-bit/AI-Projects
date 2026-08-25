import {
  NextRequest,
  NextResponse,
} from "next/server";

import {
  auth,
} from "@clerk/nextjs/server";

import {
  generateAIResponse,
  type ConversationMessage,
} from "@/lib/ai";

import {
  retrieveContext,
} from "@/lib/rag";

import {
  createConversation,
  saveChatMessage,
} from "@/lib/memory";

export const runtime = "nodejs";
export const dynamic =
  "force-dynamic";

function parseHistory(
  value: unknown
): ConversationMessage[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter((item) => {
      if (
        typeof item !== "object" ||
        item === null
      ) {
        return false;
      }

      const message = item as {
        role?: unknown;
        content?: unknown;
      };

      return (
        (message.role === "user" ||
          message.role ===
            "assistant") &&
        typeof message.content ===
          "string"
      );
    })
    .slice(-8)
    .map((item) => {
      const message = item as {
        role: "user" | "assistant";
        content: string;
      };

      return {
        role: message.role,

        content:
          message.content.slice(
            0,
            4000
          ),
      };
    });
}

function parseConversationId(
  value: unknown
): string | null {
  if (typeof value !== "string") {
    return null;
  }

  const id = value.trim();

  const uuidPattern =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

  return uuidPattern.test(id)
    ? id
    : null;
}

export async function POST(
  request: NextRequest
) {
  try {
    /* =====================================
       AUTHENTICATION
    ===================================== */

    const { userId } =
      await auth();

    if (!userId) {
      return NextResponse.json(
        {
          error:
            "You must be signed in to use chat.",
        },
        {
          status: 401,
        }
      );
    }

    /* =====================================
       READ AND VALIDATE REQUEST
    ===================================== */

    const body =
      await request.json();

    const message =
      typeof body.message ===
      "string"
        ? body.message.trim()
        : "";

    if (!message) {
      return NextResponse.json(
        {
          error:
            "Please enter a message.",
        },
        {
          status: 400,
        }
      );
    }

    if (message.length > 4000) {
      return NextResponse.json(
        {
          error:
            "The message cannot exceed 4000 characters.",
        },
        {
          status: 400,
        }
      );
    }

    const history =
      parseHistory(
        body.history
      );

    /*
     * Use an existing conversation when
     * the client sends a valid UUID.
     */
    let conversationId =
      parseConversationId(
        body.conversationId
      );

    /* =====================================
       CREATE CONVERSATION
    ===================================== */

    if (!conversationId) {
      const conversation =
        await createConversation(
          userId,
          message
        );

      conversationId =
        conversation.id;
    }

    /* =====================================
       SAVE USER MESSAGE
    ===================================== */

    await saveChatMessage(
      conversationId,
      userId,
      "user",
      message,
      []
    );

    /* =====================================
       BUILD RETRIEVAL QUERY
    ===================================== */

    const recentUserQuestions =
      history
        .filter(
          (item) =>
            item.role === "user"
        )
        .slice(-2)
        .map(
          (item) =>
            item.content
        );

    const retrievalQuery = [
      ...recentUserQuestions,
      message,
    ].join(" ");

    /* =====================================
       USER-SPECIFIC RAG RETRIEVAL
    ===================================== */

    const retrieval =
      await retrieveContext(
        retrievalQuery,
        userId
      );

    /* =====================================
       GENERATE AI ANSWER
    ===================================== */

    const answer =
      await generateAIResponse(
        message,
        retrieval.context,
        history
      );

    /* =====================================
       SAVE ASSISTANT MESSAGE
    ===================================== */

    await saveChatMessage(
      conversationId,
      userId,
      "assistant",
      answer,
      retrieval.sources
    );

    return NextResponse.json({
      success: true,
      answer,
      conversationId,
      sources:
        retrieval.sources,

      retrievedChunks:
        retrieval.chunks.length,

      usedDocumentContext:
        retrieval.chunks.length > 0,
    });
  } catch (error) {
    console.error(
      "RAG chat error:",
      error
    );

    return NextResponse.json(
      {
        success: false,

        error:
          error instanceof Error
            ? error.message
            : "Unable to generate an answer.",
      },
      {
        status: 500,
      }
    );
  }
}