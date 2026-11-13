"use client";

import { Menu, Search, TrendingUp, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

import { LogoutButton } from "@/components/auth/logout-button";
import { APP_NAME, navigationItems, type NavigationLabel } from "@/components/dashboard/navigation";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type MobileNavProps = {
  userName: string;
  activeItem: NavigationLabel;
};

/** The phone header: the app name, a search shortcut and a menu that slides in. */
export function MobileNav({ userName, activeItem }: MobileNavProps) {
  const [isOpen, setIsOpen] = useState(false);
  const pathname = usePathname();

  // Close the menu after navigating.
  useEffect(() => {
    setIsOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  return (
    <div className="lg:hidden">
      <div className="flex h-14 items-center justify-between gap-3 px-4">
        <Link href="/dashboard" className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <TrendingUp className="h-4 w-4" aria-hidden="true" />
          </span>
          <span className="text-sm font-semibold">{APP_NAME}</span>
        </Link>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/stocks" aria-label="Search stocks">
              <Search className="h-5 w-5" aria-hidden="true" />
            </Link>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsOpen(true)}
            aria-label="Open menu"
            aria-expanded={isOpen}
            aria-controls="mobile-menu"
          >
            <Menu className="h-5 w-5" aria-hidden="true" />
          </Button>
        </div>
      </div>

      {/* Rendered on the page body: the blurred header would otherwise confine a fixed overlay. */}
      {isOpen
        ? createPortal(
        <div className="dark fixed inset-0 z-50 text-foreground lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <button
            type="button"
            className="absolute inset-0 bg-black/60"
            onClick={() => setIsOpen(false)}
            aria-label="Close menu"
            tabIndex={-1}
          />
          <nav
            id="mobile-menu"
            className="absolute inset-y-0 right-0 flex w-72 max-w-[85vw] flex-col border-l bg-card shadow-xl"
            aria-label="Main"
          >
            <div className="flex h-14 items-center justify-between border-b px-4">
              <span className="text-sm font-semibold">Menu</span>
              <Button variant="ghost" size="sm" onClick={() => setIsOpen(false)} aria-label="Close menu" autoFocus>
                <X className="h-5 w-5" aria-hidden="true" />
              </Button>
            </div>
            <div className="flex-1 space-y-1 overflow-y-auto p-3">
              {navigationItems.map((item) => (
                <Link
                  key={item.label}
                  href={item.href}
                  aria-current={item.label === activeItem ? "page" : undefined}
                  className={cn(
                    "flex h-11 items-center gap-3 rounded-md px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground",
                    item.label === activeItem && "bg-secondary text-foreground",
                  )}
                >
                  <item.icon className="h-4 w-4" aria-hidden="true" />
                  {item.label}
                </Link>
              ))}
            </div>
            <div className="border-t p-4">
              <p className="mb-3 truncate text-sm font-medium">{userName}</p>
              <LogoutButton />
            </div>
          </nav>
        </div>,
            document.body,
          )
        : null}
    </div>
  );
}
