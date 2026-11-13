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
  "Track a stock portfolio against the S&P 500 with live prices, risk analytics, stock comparison and market news.";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Stock Portfolio Analytics",
    template: "%s · Stock Portfolio Analytics",
  },
  description,
  applicationName: "Stock Portfolio Analytics",
  openGraph: {
    type: "website",
    siteName: "Stock Portfolio Analytics",
    title: "Stock Portfolio Analytics",
    description,
  },
  twitter: {
    card: "summary_large_image",
    title: "Stock Portfolio Analytics",
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
