import { BarChart3 } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type AuthShellProps = {
  title: string;
  description: string;
  footer: ReactNode;
  children: ReactNode;
};

export function AuthShell({ title, description, footer, children }: AuthShellProps) {
  return (
    <main className="dark flex min-h-screen items-center justify-center bg-background px-4 py-8 text-foreground">
      <section className="w-full max-w-md">
        <Link href="/" className="mb-6 flex items-center justify-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <BarChart3 className="h-5 w-5" aria-hidden="true" />
          </span>
          <span className="text-sm font-semibold">Stock Portfolio Analytics</span>
        </Link>
        <Card>
          <CardHeader>
            <CardTitle>{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </CardHeader>
          <CardContent>
            {children}
            <div className="mt-6 text-center text-sm text-muted-foreground">{footer}</div>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
