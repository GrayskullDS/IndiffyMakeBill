"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  BarChart3, TrendingUp, Globe, Activity, Bell,
  Settings, ChevronRight, Zap, LayoutDashboard,
} from "lucide-react";

const NAV_ITEMS = [
  {
    label: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    label: "Trader Mode",
    href: "/trader-mode",
    icon: Zap,
    highlight: true,
  },
  {
    label: "Macro Regime",
    href: "/regime",
    icon: Globe,
  },
  {
    label: "Asset Analysis",
    href: "/assets",
    icon: TrendingUp,
  },
  {
    label: "Indicators",
    href: "/indicators",
    icon: BarChart3,
  },
  {
    label: "Alerts",
    href: "/alerts",
    icon: Bell,
  },
];

const ASSET_SECTIONS = [
  { label: "Forex", href: "/assets?class=forex" },
  { label: "Indices", href: "/assets?class=equity_index" },
  { label: "Commodities", href: "/assets?class=commodity" },
  { label: "Bonds", href: "/assets?class=bond" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 flex-shrink-0 bg-card border-r border-border flex flex-col h-full">
      {/* Logo */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center">
            <Activity className="w-3.5 h-3.5 text-primary" />
          </div>
          <div>
            <span className="text-sm font-bold text-foreground tracking-tight">MacroIntel</span>
            <div className="text-[10px] text-muted-foreground font-medium">PRO</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));

          return (
            <Link key={item.href} href={item.href}>
              <div
                className={cn(
                  "nav-item",
                  isActive && "active",
                  item.highlight && !isActive && "text-primary/80 hover:text-primary"
                )}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span className="flex-1">{item.label}</span>
                {item.highlight && (
                  <span className="text-[10px] bg-primary/20 text-primary px-1.5 py-0.5 rounded font-semibold">
                    LIVE
                  </span>
                )}
              </div>
            </Link>
          );
        })}

        {/* Asset sections */}
        <div className="pt-3 pb-1">
          <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest px-3 mb-1">
            Markets
          </div>
          {ASSET_SECTIONS.map((s) => (
            <Link key={s.label} href={s.href}>
              <div
                className={cn(
                  "nav-item text-xs",
                  pathname + (typeof window !== "undefined" ? window.location.search : "") === s.href && "active"
                )}
              >
                <ChevronRight className="w-3 h-3 flex-shrink-0" />
                {s.label}
              </div>
            </Link>
          ))}
        </div>
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-border">
        <Link href="/settings">
          <div className="nav-item text-xs">
            <Settings className="w-3.5 h-3.5" />
            Settings
          </div>
        </Link>
        <div className="mt-2 px-3">
          <div className="text-[10px] text-muted-foreground">
            Data: FRED · CFTC · Yahoo Finance
          </div>
        </div>
      </div>
    </aside>
  );
}
