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
  "Live stock prices, stock research, market news, watchlists and portfolio tracking in one dashboard.";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Stock Intelligence",
    template: "%s · Stock Intelligence",
  },
  description,
  applicationName: "Stock Intelligence",
  openGraph: {
    type: "website",
    siteName: "Stock Intelligence",
    title: "Stock Intelligence",
    description,
  },
  twitter: {
    card: "summary_large_image",
    title: "Stock Intelligence",
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
