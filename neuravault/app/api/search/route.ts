import {
  NextRequest,
  NextResponse,
} from "next/server";

import {
  auth,
} from "@clerk/nextjs/server";

import {
  retrieveRelevantChunks,
} from "@/lib/rag";

export const runtime = "nodejs";
export const dynamic =
  "force-dynamic";

export async function GET(
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
          success: false,
          error:
            "You must be signed in to search.",
        },
        {
          status: 401,
        }
      );
    }

    /* =====================================
       QUERY VALIDATION
    ===================================== */

    const query =
      request.nextUrl.searchParams
        .get("q")
        ?.trim() || "";

    if (!query) {
      return NextResponse.json(
        {
          success: false,
          error:
            "A search query is required.",
        },
        {
          status: 400,
        }
      );
    }

    if (query.length > 4000) {
      return NextResponse.json(
        {
          success: false,
          error:
            "The search query cannot exceed 4000 characters.",
        },
        {
          status: 400,
        }
      );
    }

    /* =====================================
       USER-SPECIFIC SEARCH
    ===================================== */

    const chunks =
      await retrieveRelevantChunks(
        query,
        userId
      );

    return NextResponse.json({
      success: true,
      query,
      count: chunks.length,
      results: chunks,
    });
  } catch (error) {
    console.error(
      "Search error:",
      error
    );

    return NextResponse.json(
      {
        success: false,
        error:
          error instanceof Error
            ? error.message
            : "Search failed.",
      },
      {
        status: 500,
      }
    );
  }
}