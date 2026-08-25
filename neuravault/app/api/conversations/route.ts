import {
  NextRequest,
  NextResponse,
} from "next/server";

import {
  auth,
} from "@clerk/nextjs/server";

import {
  deleteConversation,
  getConversationMessages,
  getConversations,
} from "@/lib/memory";

export const runtime = "nodejs";
export const dynamic =
  "force-dynamic";

function isValidConversationId(
  value: string
): boolean {
  const uuidPattern =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

  return uuidPattern.test(value);
}

/* ========================================
   GET CONVERSATIONS OR MESSAGES
======================================== */

export async function GET(
  request: NextRequest
) {
  try {
    const { userId } =
      await auth();

    if (!userId) {
      return NextResponse.json(
        {
          success: false,
          error:
            "You must be signed in.",
        },
        {
          status: 401,
        }
      );
    }

    const conversationId =
      request.nextUrl.searchParams.get(
        "id"
      );

    /*
     * When an ID is supplied, return only
     * that user's conversation messages.
     */
    if (conversationId) {
      if (
        !isValidConversationId(
          conversationId
        )
      ) {
        return NextResponse.json(
          {
            success: false,
            error:
              "Invalid conversation ID.",
          },
          {
            status: 400,
          }
        );
      }

      const messages =
        await getConversationMessages(
          conversationId,
          userId
        );

      return NextResponse.json({
        success: true,
        messages,
      });
    }

    /*
     * When no ID is supplied, return the
     * signed-in user's conversation list.
     */
    const conversations =
      await getConversations(
        userId
      );

    return NextResponse.json({
      success: true,
      conversations,
    });
  } catch (error) {
    console.error(
      "Conversation GET error:",
      error
    );

    return NextResponse.json(
      {
        success: false,
        error:
          error instanceof Error
            ? error.message
            : "Unable to load conversations.",
      },
      {
        status: 500,
      }
    );
  }
}

/* ========================================
   DELETE USER CONVERSATION
======================================== */

export async function DELETE(
  request: NextRequest
) {
  try {
    const { userId } =
      await auth();

    if (!userId) {
      return NextResponse.json(
        {
          success: false,
          error:
            "You must be signed in.",
        },
        {
          status: 401,
        }
      );
    }

    const conversationId =
      request.nextUrl.searchParams.get(
        "id"
      );

    if (!conversationId) {
      return NextResponse.json(
        {
          success: false,
          error:
            "Conversation ID is required.",
        },
        {
          status: 400,
        }
      );
    }

    if (
      !isValidConversationId(
        conversationId
      )
    ) {
      return NextResponse.json(
        {
          success: false,
          error:
            "Invalid conversation ID.",
        },
        {
          status: 400,
        }
      );
    }

    const deleted =
      await deleteConversation(
        conversationId,
        userId
      );

    if (!deleted) {
      return NextResponse.json(
        {
          success: false,
          error:
            "Conversation not found.",
        },
        {
          status: 404,
        }
      );
    }

    return NextResponse.json({
      success: true,
      message:
        "Conversation deleted.",
    });
  } catch (error) {
    console.error(
      "Conversation DELETE error:",
      error
    );

    return NextResponse.json(
      {
        success: false,
        error:
          error instanceof Error
            ? error.message
            : "Unable to delete conversation.",
      },
      {
        status: 500,
      }
    );
  }
}