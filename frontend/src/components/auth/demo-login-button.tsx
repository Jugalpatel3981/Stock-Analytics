"use client";

import { PlayCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button, type ButtonProps } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast-provider";
import { demoLogin } from "@/lib/api";

export function DemoLoginButton({ className, size, variant }: Pick<ButtonProps, "className" | "size" | "variant">) {
  const router = useRouter();
  const { showToast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [isSlow, setIsSlow] = useState(false);

  async function handleClick() {
    setIsLoading(true);
    // Free hosting puts the API to sleep when idle; the first request can take a while.
    const slowTimer = window.setTimeout(() => setIsSlow(true), 4000);

    try {
      await demoLogin();
      router.push("/dashboard");
      router.refresh();
    } catch (caughtError) {
      setIsLoading(false);
      setIsSlow(false);
      showToast({ message: caughtError instanceof Error ? caughtError.message : "Demo is unavailable right now" });
    } finally {
      window.clearTimeout(slowTimer);
    }
  }

  const label = isSlow ? "Waking up the server..." : isLoading ? "Starting demo..." : "Try the live demo";

  return (
    <Button
      aria-live="polite"
      title={isSlow ? "The free-tier server sleeps when idle and can take up to a minute to start." : undefined}
      className={className}
      size={size}
      variant={variant}
      type="button"
      onClick={handleClick}
      disabled={isLoading}
    >
      <PlayCircle className="h-4 w-4" aria-hidden="true" />
      {label}
    </Button>
  );
}
