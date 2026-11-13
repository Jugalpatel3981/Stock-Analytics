import {
  BriefcaseBusiness,
  ChartNoAxesCombined,
  GitCompareArrows,
  LayoutDashboard,
  ListChecks,
  Newspaper,
  TrendingUp,
} from "lucide-react";

export const navigationItems = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Stocks", href: "/stocks", icon: TrendingUp },
  { label: "Watchlists", href: "/watchlists", icon: ListChecks },
  { label: "Portfolio", href: "/portfolio", icon: BriefcaseBusiness },
  { label: "Analytics", href: "/analytics", icon: ChartNoAxesCombined },
  { label: "Compare", href: "/compare", icon: GitCompareArrows },
  { label: "News", href: "/news", icon: Newspaper },
] as const;

export type NavigationLabel = (typeof navigationItems)[number]["label"];

export const APP_NAME = "Stock Portfolio Analytics";
