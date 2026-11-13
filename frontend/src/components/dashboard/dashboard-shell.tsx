import { TrendingUp } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { LogoutButton } from "@/components/auth/logout-button";
import { DashboardHeaderActions } from "@/components/dashboard/dashboard-header-actions";
import { MobileNav } from "@/components/dashboard/mobile-nav";
import { APP_NAME, navigationItems, type NavigationLabel } from "@/components/dashboard/navigation";
import { cn } from "@/lib/utils";

type DashboardShellProps = {
  userName: string;
  activeItem?: NavigationLabel;
  children: ReactNode;
};

export function DashboardShell({ userName, activeItem = "Dashboard", children }: DashboardShellProps) {
  return (
    <main className="dark min-h-screen bg-background text-foreground">
      <div className="flex min-h-screen">
        <aside className="sticky top-0 hidden h-screen w-60 shrink-0 border-r bg-card/80 lg:block">
          <div className="flex h-full flex-col">
            <Link href="/dashboard" className="flex h-16 items-center gap-3 border-b px-5">
              <span className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <TrendingUp className="h-5 w-5" aria-hidden="true" />
              </span>
              <span className="text-sm font-semibold">{APP_NAME}</span>
            </Link>
            <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4" aria-label="Main">
              {navigationItems.map((item) => (
                <Link
                  key={item.label}
                  href={item.href}
                  aria-current={item.label === activeItem ? "page" : undefined}
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
              <p className="mb-3 truncate text-sm font-medium">{userName}</p>
              <LogoutButton />
            </div>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 border-b bg-background/95 backdrop-blur">
            <MobileNav userName={userName} activeItem={activeItem} />
            <div className="hidden h-16 items-center justify-end px-6 lg:flex">
              <DashboardHeaderActions />
            </div>
          </header>

          <section className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8">{children}</section>
        </div>
      </div>
    </main>
  );
}
