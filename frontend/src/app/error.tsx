"use client";

import { AlertTriangle, RotateCcw } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main className="dark flex min-h-screen items-center justify-center bg-background px-4 text-foreground">
      <section className="w-full max-w-md rounded-lg border bg-card/80 p-8 text-center">
        <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-md bg-secondary text-primary">
          <AlertTriangle className="h-5 w-5" aria-hidden="true" />
        </span>
        <h1 className="mt-5 text-lg font-semibold">Something went wrong loading this page</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          A market data provider may be busy, or the server may still be waking up. Please try again in a moment.
        </p>
        <div className="mt-6 flex flex-col justify-center gap-2 sm:flex-row">
          <Button onClick={reset}>
            <RotateCcw className="h-4 w-4" aria-hidden="true" />
            Try again
          </Button>
          <Button variant="outline" asChild>
            <Link href="/dashboard">Go to dashboard</Link>
          </Button>
        </div>
      </section>
    </main>
  );
}
