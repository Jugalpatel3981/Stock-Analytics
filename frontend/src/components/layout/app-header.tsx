import { BarChart3 } from "lucide-react";

import { Button } from "@/components/ui/button";

export function AppHeader() {
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
          <a className="transition-colors hover:text-foreground" href="#">Dashboard</a>
          <a className="transition-colors hover:text-foreground" href="#">Watchlist</a>
          <a className="transition-colors hover:text-foreground" href="#">Research</a>
        </nav>
        <Button variant="outline" size="sm">Sign in</Button>
      </div>
    </header>
  );
}
