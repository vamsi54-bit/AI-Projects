import {
  NextResponse,
} from "next/server";

import {
  auth,
} from "@clerk/nextjs/server";

import {
  getDashboardData,
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
          error:
            "You must be signed in.",
        },
        {
          status: 401,
        }
      );
    }

    const dashboardData =
      await getDashboardData(userId);

    return NextResponse.json({
      success: true,
      ...dashboardData,
    });
  } catch (error) {
    console.error(
      "Dashboard API error:",
      error
    );

    return NextResponse.json(
      {
        success: false,
        error:
          error instanceof Error
            ? error.message
            : "Unable to load dashboard.",
      },
      {
        status: 500,
      }
    );
  }
}