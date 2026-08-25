import {
  NextRequest,
  NextResponse,
} from "next/server";

import { auth } from "@clerk/nextjs/server";

import { parseDocument } from "@/lib/parser";
import { saveDocument } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const MAX_FILE_SIZE = 4 * 1024 * 1024;

export async function POST(
  request: NextRequest
) {
  try {
    // Get the currently signed-in user
    const { userId } = await auth();

    if (!userId) {
      return NextResponse.json(
        {
          success: false,
          error:
            "You must be signed in to upload documents.",
        },
        {
          status: 401,
        }
      );
    }

    // Read uploaded file
    const formData =
      await request.formData();

    const uploadedFile =
      formData.get("file");

    if (!(uploadedFile instanceof File)) {
      return NextResponse.json(
        {
          success: false,
          error: "Please select a file.",
        },
        {
          status: 400,
        }
      );
    }

    if (uploadedFile.size === 0) {
      return NextResponse.json(
        {
          success: false,
          error:
            "The selected file is empty.",
        },
        {
          status: 400,
        }
      );
    }

    if (
      uploadedFile.size >
      MAX_FILE_SIZE
    ) {
      return NextResponse.json(
        {
          success: false,
          error:
            "The file cannot exceed 4 MB.",
        },
        {
          status: 400,
        }
      );
    }

    // Extract text from the uploaded file
    const parsedDocument =
      await parseDocument(uploadedFile);

    const documentText =
      parsedDocument.text.trim();

    if (!documentText) {
      return NextResponse.json(
        {
          success: false,
          error:
            "No readable text was found in the document.",
        },
        {
          status: 422,
        }
      );
    }

    const fileType =
      uploadedFile.type ||
      "application/octet-stream";

    const pages =
      parsedDocument.pages ?? null;

    const characterCount =
      documentText.length;

    // Save document, chunks and embeddings
    const savedDocument =
      await saveDocument({
        userId,
        name: uploadedFile.name,
        fileType,
        fileSize: uploadedFile.size,
        pages,
        content: documentText,
        characterCount,
      });

    return NextResponse.json(
      {
        success: true,
        document: {
          id: savedDocument.id,
          name: savedDocument.name,
          type: fileType,
          size: uploadedFile.size,
          pages,
          characters: characterCount,
          chunks:
            savedDocument.chunkCount,
          createdAt:
            savedDocument.createdAt,
          preview:
            documentText.slice(0, 1000),
        },
      },
      {
        status: 201,
      }
    );
  } catch (error) {
    console.error(
      "Upload error:",
      error
    );

    const errorMessage =
      error instanceof Error
        ? error.message
        : "Unable to process the document.";

    return NextResponse.json(
      {
        success: false,
        error: errorMessage,
      },
      {
        status: 500,
      }
    );
  }
}