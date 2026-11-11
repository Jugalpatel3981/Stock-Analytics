import {
  BriefcaseBusiness,
  LayoutDashboard,
  ListChecks,
  Newspaper,
  TrendingUp,
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { LogoutButton } from "@/components/auth/logout-button";
import { DashboardHeaderActions } from "@/components/dashboard/dashboard-header-actions";
import { cn } from "@/lib/utils";

const navigationItems = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Stocks", href: "/stocks", icon: TrendingUp },
  { label: "Watchlists", href: "/watchlists", icon: ListChecks },
  { label: "Portfolio", href: "/portfolio", icon: BriefcaseBusiness },
  { label: "News", href: "/news", icon: Newspaper },
];

type DashboardShellProps = {
  userName: string;
  activeItem?: "Dashboard" | "Stocks" | "Watchlists" | "Portfolio" | "News";
  children: ReactNode;
};

export function DashboardShell({ userName, activeItem = "Dashboard", children }: DashboardShellProps) {
  return (
    <main className="dark min-h-screen bg-background text-foreground">
      <div className="flex min-h-screen">
        <aside className="hidden w-64 shrink-0 border-r bg-card/80 lg:block">
          <div className="flex h-full flex-col">
            <div className="border-b px-5 py-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
                  <TrendingUp className="h-5 w-5" aria-hidden="true" />
                </div>
                <div>
                  <p className="text-sm font-semibold">Stock Intel</p>
                  <p className="text-xs text-muted-foreground">Research workspace</p>
                </div>
              </div>
            </div>
            <nav className="flex-1 space-y-1 px-3 py-4" aria-label="Sidebar">
              {navigationItems.map((item) => (
                <Link
                  key={item.label}
                  href={item.href}
                  className={cn(
                    "flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground",
                    item.label === activeItem && "bg-secondary text-foreground",
                  )}
                >
                  <item.icon className="h-4 w-4" aria-hidden="true" />
                  {item.label}
                </Link>
              ))}
            </nav>
            <div className="border-t p-4">
              <div className="mb-3">
                <p className="text-sm font-medium">{userName}</p>
                <p className="text-xs text-muted-foreground">Authenticated session</p>
              </div>
              <LogoutButton />
            </div>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 border-b bg-background/95 backdrop-blur">
            <div className="flex min-h-16 flex-col gap-3 px-4 py-3 lg:flex-row lg:items-center lg:justify-between lg:px-6">
              <div>
                <p className="text-xs font-medium uppercase text-muted-foreground">Market command center</p>
                <h1 className="text-xl font-semibold tracking-normal sm:text-2xl">{activeItem}</h1>
              </div>
              <div className="flex items-center gap-2">
                <DashboardHeaderActions />
                <div className="lg:hidden">
                  <LogoutButton />
                </div>
              </div>
            </div>
            <nav className="flex gap-2 overflow-x-auto border-t px-4 py-2 lg:hidden" aria-label="Mobile">
              {navigationItems.map((item) => (
                <Link
                  key={item.label}
                  href={item.href}
                  className={cn(
                    "flex h-9 shrink-0 items-center gap-2 rounded-md px-3 text-xs font-medium text-muted-foreground",
                    item.label === activeItem && "bg-secondary text-foreground",
                  )}
                >
                  <item.icon className="h-4 w-4" aria-hidden="true" />
                  {item.label}
                </Link>
              ))}
            </nav>
          </header>

          <section className="flex-1 px-4 py-5 sm:px-6 lg:px-8">{children}</section>
        </div>
      </div>
    </main>
  );
}
