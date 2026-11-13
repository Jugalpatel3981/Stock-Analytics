"use client";

import { Loader2, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { startTransition, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

const RETRY_SECONDS = 5;
const MAX_AUTOMATIC_RETRIES = 12;

// Counts retries across remounts of this page, so automatic retrying eventually stops.
let automaticRetries = 0;

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const router = useRouter();
  const [secondsLeft, setSecondsLeft] = useState(RETRY_SECONDS);
  const isRetryingAutomatically = automaticRetries < MAX_AUTOMATIC_RETRIES;

  function retry() {
    // Ask the server for the page again, then clear the error.
    startTransition(() => {
      router.refresh();
      reset();
    });
  }

  useEffect(() => {
    if (!isRetryingAutomatically) {
      return;
    }

    if (secondsLeft <= 0) {
      automaticRetries += 1;
      retry();
      return;
    }

    const timer = window.setTimeout(() => setSecondsLeft((current) => current - 1), 1000);
    return () => window.clearTimeout(timer);
    // `retry` only uses stable router functions.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isRetryingAutomatically, secondsLeft]);

  return (
    <main className="dark flex min-h-screen items-center justify-center bg-background px-4 text-foreground">
      <section className="w-full max-w-md rounded-lg border bg-card/80 p-8 text-center" role="status">
        <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-md bg-secondary text-primary">
          <Loader2 className={isRetryingAutomatically ? "h-5 w-5 animate-spin" : "h-5 w-5"} aria-hidden="true" />
        </span>
        <h1 className="mt-5 text-lg font-semibold">
          {isRetryingAutomatically ? "Waiting for the server" : "This page could not be loaded"}
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          {isRetryingAutomatically
            ? `The server did not respond. If it has just started, this usually clears within a minute or two. Trying again in ${Math.max(secondsLeft, 0)} seconds.`
            : "The server is still not responding. Check that it is running, then try again."}
        </p>
        <div className="mt-6 flex flex-col justify-center gap-2 sm:flex-row">
          <Button
            onClick={() => {
              automaticRetries = 0;
              setSecondsLeft(RETRY_SECONDS);
              retry();
            }}
          >
            <RotateCcw className="h-4 w-4" aria-hidden="true" />
            Try again now
          </Button>
          <Button variant="outline" asChild>
            <Link href="/">Go to home page</Link>
          </Button>
        </div>
      </section>
    </main>
  );
}
