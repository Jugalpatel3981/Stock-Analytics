"use client";

import { useEffect } from "react";

import { useToast } from "@/components/ui/toast-provider";

type MarketStreamErrorToastProps = {
  error: string | null;
};

export function MarketStreamErrorToast({ error }: MarketStreamErrorToastProps) {
  const { showToast } = useToast();

  useEffect(() => {
    if (!error) {
      return;
    }

    showToast({ title: "Live market data", message: error });
  }, [error, showToast]);

  return null;
}
