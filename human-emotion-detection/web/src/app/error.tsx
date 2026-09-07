"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="route-error">
      <p>Emora Vision</p>
      <h1>Something interrupted the signal.</h1>
      <span>Your local session data is safe. Retry the page or return to detection.</span>
      <div><button type="button" onClick={reset}>Try again</button><Link href="/detect">Open detection</Link></div>
    </main>
  );
}
