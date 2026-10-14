import type { Metadata } from "next";

import { ToastProvider } from "@/components/ui/toast-provider";
import "./globals.css";

// Vercel sets VERCEL_PROJECT_PRODUCTION_URL; SITE_URL overrides it (e.g. a custom domain).
const siteUrl =
  process.env.SITE_URL ??
  (process.env.VERCEL_PROJECT_PRODUCTION_URL
    ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`
    : "http://localhost:3000");

const description =
  "Live stock prices, an AI research assistant with cited sources, news sentiment, portfolio tracking and backtested ML predictions.";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "AI Stock Intelligence",
    template: "%s · AI Stock Intelligence",
  },
  description,
  applicationName: "AI Stock Intelligence",
  openGraph: {
    type: "website",
    siteName: "AI Stock Intelligence",
    title: "AI Stock Intelligence",
    description,
  },
  twitter: {
    card: "summary_large_image",
    title: "AI Stock Intelligence",
    description,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
