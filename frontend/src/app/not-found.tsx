import { SearchX } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { Button } from "@/components/ui/button";

export const metadata: Metadata = { title: "Not found" };

export default function NotFound() {
  return (
    <main className="dark flex min-h-screen items-center justify-center bg-background px-4 text-foreground">
      <section className="w-full max-w-md rounded-lg border bg-card/80 p-8 text-center">
        <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-md bg-secondary text-primary">
          <SearchX className="h-5 w-5" aria-hidden="true" />
        </span>
        <h1 className="mt-5 text-lg font-semibold">Page or ticker not found</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Check the address, or search for a company or ticker from the Stocks page.
        </p>
        <div className="mt-6 flex flex-col justify-center gap-2 sm:flex-row">
          <Button asChild>
            <Link href="/stocks">Search stocks</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/">Home</Link>
          </Button>
        </div>
      </section>
    </main>
  );
}
