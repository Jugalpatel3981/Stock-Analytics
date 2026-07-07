"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";

import { cn } from "@/lib/utils";

type ToastVariant = "error" | "success" | "info";

type ToastInput = {
  title?: string;
  message: string;
  variant?: ToastVariant;
  duration?: number;
};

type Toast = ToastInput & {
  id: number;
  variant: ToastVariant;
};

type ToastContextValue = {
  showToast: (toast: ToastInput) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

const toastStyles: Record<ToastVariant, string> = {
  error: "border-destructive/40 bg-destructive/10 text-destructive",
  success: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  info: "border-border bg-card text-foreground",
};

const toastIcons = {
  error: AlertCircle,
  success: CheckCircle2,
  info: Info,
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismissToast = useCallback((toastId: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== toastId));
  }, []);

  const showToast = useCallback(
    ({ title, message, variant = "error", duration = 4500 }: ToastInput) => {
      const id = Date.now() + Math.random();
      setToasts((current) => [...current, { id, title, message, variant }]);
      window.setTimeout(() => dismissToast(id), duration);
    },
    [dismissToast],
  );

  const value = useMemo(() => ({ showToast }), [showToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed right-4 top-4 z-50 flex w-[min(420px,calc(100vw-2rem))] flex-col gap-3" aria-live="polite">
        {toasts.map((toast) => {
          const Icon = toastIcons[toast.variant];

          return (
            <div
              key={toast.id}
              role="status"
              className={cn(
                "flex items-start gap-3 rounded-md border px-4 py-3 text-sm shadow-lg backdrop-blur",
                toastStyles[toast.variant],
              )}
            >
              <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <div className="min-w-0 flex-1">
                {toast.title ? <p className="font-semibold">{toast.title}</p> : null}
                <p className={cn("break-words", toast.title && "mt-1")}>{toast.message}</p>
              </div>
              <button
                type="button"
                className="rounded-sm p-1 opacity-70 transition hover:opacity-100"
                onClick={() => dismissToast(toast.id)}
                aria-label="Dismiss notification"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);

  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }

  return context;
}
