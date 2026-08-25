import {
  NextRequest,
  NextResponse,
} from "next/server";

import { auth } from "@clerk/nextjs/server";

import {
  deleteDocument,
  getDocuments,
} from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const { userId } = await auth();

    if (!userId) {
      return NextResponse.json(
        {
          success: false,
          error: "You must be signed in.",
        },
        {
          status: 401,
        }
      );
    }

    const documents =
      await getDocuments(userId);

    return NextResponse.json({
      success: true,
      count: documents.length,
      documents,
    });
  } catch (error) {
    console.error(
      "Get memories error:",
      error
    );

    return NextResponse.json(
      {
        success: false,
        error:
          error instanceof Error
            ? error.message
            : "Unable to retrieve documents.",
      },
      {
        status: 500,
      }
    );
  }
}

export async function DELETE(
  request: NextRequest
) {
  try {
    const { userId } = await auth();

    if (!userId) {
      return NextResponse.json(
        {
          success: false,
          error: "You must be signed in.",
        },
        {
          status: 401,
        }
      );
    }

    const documentId =
      request.nextUrl.searchParams.get("id");

    if (!documentId) {
      return NextResponse.json(
        {
          success: false,
          error: "Document ID is required.",
        },
        {
          status: 400,
        }
      );
    }

    const deleted =
      await deleteDocument(
        documentId,
        userId
      );

    if (!deleted) {
      return NextResponse.json(
        {
          success: false,
          error:
            "Document not found or you do not have permission to delete it.",
        },
        {
          status: 404,
        }
      );
    }

    return NextResponse.json({
      success: true,
      message:
        "Document deleted successfully.",
    });
  } catch (error) {
    console.error(
      "Delete memory error:",
      error
    );

    return NextResponse.json(
      {
        success: false,
        error:
          error instanceof Error
            ? error.message
            : "Unable to delete the document.",
      },
      {
        status: 500,
      }
    );
  }
}