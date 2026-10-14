import {
  Activity,
  BarChart3,
  BrainCircuit,
  Briefcase,
  LayoutDashboard,
  Newspaper,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import Link from "next/link";

import { DemoLoginButton } from "@/components/auth/demo-login-button";
import { Button } from "@/components/ui/button";
import { getOptionalUser } from "@/lib/auth-server";

const features = [
  {
    icon: Activity,
    title: "Live market data",
    description: "Prices stream over a Finnhub WebSocket proxy, with market-session detection for pre-market and after-hours.",
  },
  {
    icon: Sparkles,
    title: "AI research assistant",
    description: "Ask about any stock. Answers combine price data, news, sentiment and web research, with cited sources.",
  },
  {
    icon: Newspaper,
    title: "News sentiment",
    description: "Headlines are classified as positive, neutral or negative by an LLM, batched and cached for speed.",
  },
  {
    icon: BrainCircuit,
    title: "Backtested predictions",
    description: "An XGBoost model forecasts next-day returns and shows its walk-forward track record against simple baselines.",
  },
  {
    icon: Briefcase,
    title: "Portfolio & watchlists",
    description: "Track holdings with live gain/loss and growth charts, and organise symbols into watchlists.",
  },
  {
    icon: ShieldCheck,
    title: "Production-minded",
    description: "JWT auth in HttpOnly cookies, background model retraining, Docker, and CI with tests, linting and builds.",
  },
];

const techStack = [
  "Next.js 15",
  "TypeScript",
  "Tailwind CSS",
  "FastAPI",
  "PostgreSQL",
  "SQLAlchemy",
  "XGBoost",
  "Groq LLM",
  "Finnhub",
  "Docker",
  "GitHub Actions",
];

export default async function Home() {
  const user = await getOptionalUser();

  return (
    <main className="dark min-h-screen bg-background text-foreground">
      <div className="mx-auto flex max-w-6xl flex-col px-4 sm:px-6">
        <header className="flex items-center justify-between py-6">
          <Link href="/" className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <BarChart3 className="h-5 w-5" aria-hidden="true" />
            </span>
            <span className="text-sm font-semibold">AI Stock Intelligence</span>
          </Link>
          <Button variant="ghost" size="sm" asChild>
            <Link href={user ? "/dashboard" : "/login"}>{user ? "Dashboard" : "Sign in"}</Link>
          </Button>
        </header>

        <section className="py-16 text-center sm:py-24">
          <p className="text-xs font-medium uppercase tracking-widest text-primary">Full-stack AI stock research platform</p>
          <h1 className="mx-auto mt-4 max-w-3xl text-4xl font-semibold tracking-tight sm:text-5xl">
            Live prices, AI research and honestly backtested predictions in one dashboard
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-base leading-7 text-muted-foreground">
            Search any US stock, follow it in real time, read news with sentiment, ask an AI assistant that cites its
            sources, and see how the prediction model has actually performed.
          </p>
          <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
            {user ? (
              <Button size="lg" asChild>
                <Link href="/dashboard">
                  <LayoutDashboard className="h-4 w-4" aria-hidden="true" />
                  Open your dashboard
                </Link>
              </Button>
            ) : (
              <DemoLoginButton size="lg" />
            )}
            <Button size="lg" variant="outline" asChild>
              <Link href="/register">Create an account</Link>
            </Button>
          </div>
          {user ? null : (
            <p className="mt-4 text-xs text-muted-foreground">No sign-up needed. The demo account comes with a sample portfolio.</p>
          )}
        </section>

        <section className="grid gap-4 pb-16 sm:grid-cols-2 lg:grid-cols-3">
          {features.map(({ icon: Icon, title, description }) => (
            <article key={title} className="rounded-lg border bg-card/70 p-5">
              <span className="flex h-9 w-9 items-center justify-center rounded-md bg-secondary text-primary">
                <Icon className="h-5 w-5" aria-hidden="true" />
              </span>
              <h2 className="mt-4 text-sm font-semibold">{title}</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
            </article>
          ))}
        </section>

        <section className="border-t py-10 text-center">
          <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Built with</p>
          <ul className="mt-4 flex flex-wrap justify-center gap-2">
            {techStack.map((tech) => (
              <li key={tech} className="rounded-full border bg-card/70 px-3 py-1 text-xs text-muted-foreground">
                {tech}
              </li>
            ))}
          </ul>
        </section>

        <footer className="border-t py-8 text-center text-xs leading-5 text-muted-foreground">
          For informational and educational purposes only. Not financial advice.
        </footer>
      </div>
    </main>
  );
}
