import {
  clerkMiddleware,
} from "@clerk/nextjs/server";

const protectedRoutes = [
  "/dashboard",
  "/chat",
  "/upload",
  "/memories",

  "/api/chat",
  "/api/upload",
  "/api/memories",
  "/api/search",
  "/api/dashboard",
  "/api/conversations",
];

export default clerkMiddleware(
  async (
    auth,
    request
  ) => {
    const pathname =
      request.nextUrl.pathname;

    const isProtectedRoute =
      protectedRoutes.some(
        (route) =>
          pathname === route ||
          pathname.startsWith(
            `${route}/`
          )
      );

    /*
     * Public pages such as /, /sign-in
     * and /sign-up continue normally.
     */
    if (!isProtectedRoute) {
      return;
    }

    const {
      isAuthenticated,
      redirectToSignIn,
    } = await auth();

    if (!isAuthenticated) {
      return redirectToSignIn({
        returnBackUrl:
          request.url,
      });
    }
  }
);

export const config = {
  matcher: [
    /*
     * Run Clerk for application routes
     * while skipping Next.js internals
     * and ordinary static files.
     */
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",

    /*
     * Always run Clerk for API routes.
     */
    "/(api|trpc)(.*)",

    /*
     * Required by Clerk's frontend API.
     */
    "/__clerk/(.*)",
  ],
};