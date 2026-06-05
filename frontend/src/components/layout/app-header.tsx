import { BarChart3 } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

type AppHeaderProps = {
  userName?: string;
  action?: ReactNode;
};

export function AppHeader({ userName, action }: AppHeaderProps) {
  return (
    <header className="border-b bg-card">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <BarChart3 className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-semibold">AI Stock Intelligence</p>
            <p className="text-xs text-muted-foreground">Portfolio research platform</p>
          </div>
        </div>
        <nav className="hidden items-center gap-5 text-sm text-muted-foreground md:flex" aria-label="Primary">
          <Link className="transition-colors hover:text-foreground" href="/dashboard">Dashboard</Link>
          <a className="transition-colors hover:text-foreground" href="#watchlist">Watchlist</a>
          <a className="transition-colors hover:text-foreground" href="#research">Research</a>
        </nav>
        <div className="flex items-center gap-3">
          {userName ? <span className="hidden text-sm text-muted-foreground sm:inline">{userName}</span> : null}
          {action ?? (
            <Button variant="outline" size="sm" asChild>
              <Link href="/login">Sign in</Link>
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
