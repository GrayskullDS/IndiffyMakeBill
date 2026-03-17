"use client";
import { useQuery } from "@tanstack/react-query";
import { macroIntelApi } from "@/lib/api";
import { cn, getRegimeBg, getBiasBg, getBiasLabel, getScoreBarColor, getVolatilityColor } from "@/lib/utils";
import { ScoreGauge } from "@/components/shared/ScoreGauge";
import { BiasCard } from "@/components/shared/BiasCard";
import {
  Zap, AlertTriangle, TrendingUp, TrendingDown, Minus,
  ArrowUpRight, Brain, Target, Activity, Info,
} from "lucide-react";

const SCORE_DESCRIPTIONS = {
  growth: "GDP, PMI, industrial production momentum",
  inflation: "CPI, core CPI, PPI, inflation expectations",
  labor: "Unemployment, payrolls, wages",
  monetary: "Fed funds rate, yield curve, real rates",
  risk: "VIX, credit spreads, financial conditions",
  liquidity: "Fed balance sheet, M2, repo markets",
};

export default function TraderModePage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["trader-overview"],
    queryFn: macroIntelApi.getTraderOverview,
    refetchInterval: 5 * 60 * 1000,
  });

  if (isLoading) {
    return <TraderModeSkeleton />;
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="w-8 h-8 text-orange-400 mx-auto mb-2" />
          <p className="text-muted-foreground text-sm">
            No data available. Run the data pipeline to populate macro data.
          </p>
        </div>
      </div>
    );
  }

  const { regime, trade_environment, bias_signals, trader_summary } = data;
  const scores = regime.scores || {};

  // Separate by asset class
  const forexSignals = bias_signals.filter(b => b.asset_class === "forex").slice(0, 7);
  const equitySignals = bias_signals.filter(b => b.asset_class === "equity_index");
  const commoditySignals = bias_signals.filter(b => b.asset_class === "commodity");
  const bondSignals = bias_signals.filter(b => b.asset_class === "bond");

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary/15 border border-primary/20 flex items-center justify-center">
            <Zap className="w-4 h-4 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-bold">Trader Mode</h1>
            <p className="text-xs text-muted-foreground">
              Macro intelligence translated into actionable trading context
            </p>
          </div>
        </div>
        <div className="text-xs text-muted-foreground font-mono">
          Updated: {new Date(data.date).toLocaleDateString()}
        </div>
      </div>

      {/* === ROW 1: Regime + Trade Environment + Summary === */}
      <div className="grid grid-cols-12 gap-4">
        {/* Macro Regime Panel */}
        <div className="col-span-12 lg:col-span-4">
          <RegimePanel regime={regime} />
        </div>

        {/* Trade Environment */}
        <div className="col-span-12 lg:col-span-4">
          <TradeEnvironmentPanel environment={trade_environment} />
        </div>

        {/* Trader Summary */}
        <div className="col-span-12 lg:col-span-4">
          <TraderSummaryPanel summary={trader_summary} />
        </div>
      </div>

      {/* === ROW 2: Score Gauges === */}
      <div className="card-base">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="w-4 h-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Macro Score Dashboard</h2>
          <span className="text-xs text-muted-foreground">— 6 composite dimensions, each 0–10</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
          {(Object.keys(scores) as Array<keyof typeof scores>).map((key) => (
            <ScoreGauge
              key={key}
              label={key.charAt(0).toUpperCase() + key.slice(1)}
              score={scores[key]}
              description={SCORE_DESCRIPTIONS[key as keyof typeof SCORE_DESCRIPTIONS]}
            />
          ))}
        </div>
      </div>

      {/* === ROW 3: Directional Bias Grid === */}
      <div className="space-y-4">
        {/* Forex */}
        <AssetSection title="Forex Pairs" icon="💱" signals={forexSignals} />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Equity Indices */}
          <div className="lg:col-span-1">
            <AssetSection title="Equity Indices" icon="📈" signals={equitySignals} compact />
          </div>
          {/* Commodities */}
          <div className="lg:col-span-1">
            <AssetSection title="Commodities" icon="🥇" signals={commoditySignals} compact />
          </div>
          {/* Bonds */}
          <div className="lg:col-span-1">
            <AssetSection title="Bonds & Rates" icon="🏦" signals={bondSignals} compact />
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────

function RegimePanel({ regime }: { regime: any }) {
  return (
    <div className="card-base h-full">
      <div className="flex items-center gap-2 mb-3">
        <Brain className="w-4 h-4 text-muted-foreground" />
        <h3 className="text-sm font-semibold">Market Regime</h3>
      </div>

      <div className={cn(
        "regime-pill border inline-flex items-center gap-1.5 mb-3",
        getRegimeBg(regime.type ?? "")
      )}>
        <span className="w-1.5 h-1.5 rounded-full bg-current" />
        {regime.label ?? "Unknown"}
      </div>

      <div className="text-xs text-muted-foreground mb-3">
        {regime.regime_summary?.split("**").map((part: string, i: number) =>
          i % 2 === 0
            ? part
            : <strong key={i} className="text-foreground">{part}</strong>
        ) ?? "No summary available."}
      </div>

      <div className="space-y-1.5 pt-3 border-t border-border/50">
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Confidence</span>
          <span className="font-mono">
            {Math.round((regime.confidence ?? 0) * 100)}%
          </span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Recession Risk</span>
          <span className={cn(
            "font-mono",
            (regime.recession_probability ?? 0) > 0.5 ? "text-red-400" : "text-green-400"
          )}>
            {Math.round((regime.recession_probability ?? 0) * 100)}%
          </span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Growth Phase</span>
          <span className="font-mono capitalize">
            {regime.phases?.growth?.replace("_", " ") ?? "—"}
          </span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Inflation Phase</span>
          <span className="font-mono capitalize">
            {regime.phases?.inflation?.replace("_", " ") ?? "—"}
          </span>
        </div>
      </div>
    </div>
  );
}

function TradeEnvironmentPanel({ environment }: { environment: any }) {
  const ENV_COLORS: Record<string, string> = {
    high_volatility: "border-red-500/30 bg-red-500/5",
    trend_following: "border-green-500/30 bg-green-500/5",
    risk_off: "border-orange-500/30 bg-orange-500/5",
    tightening: "border-purple-500/30 bg-purple-500/5",
    mixed: "border-blue-500/30 bg-blue-500/5",
  };

  const colorClass = ENV_COLORS[environment?.type ?? "mixed"] ?? ENV_COLORS.mixed;

  return (
    <div className={cn("card-base border h-full", colorClass)}>
      <div className="flex items-center gap-2 mb-3">
        <Target className="w-4 h-4 text-muted-foreground" />
        <h3 className="text-sm font-semibold">Trade Environment</h3>
      </div>

      <div className="text-base font-bold text-foreground mb-2">
        {environment?.label ?? "Unknown"}
      </div>

      <p className="text-xs text-muted-foreground mb-4">
        {environment?.description ?? "No environment data available."}
      </p>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Recommended Style:</span>
          <span className="text-xs font-semibold text-foreground">
            {environment?.trade_style ?? "—"}
          </span>
        </div>
      </div>
    </div>
  );
}

function TraderSummaryPanel({ summary }: { summary: any }) {
  return (
    <div className="card-base h-full">
      <div className="flex items-center gap-2 mb-3">
        <Info className="w-4 h-4 text-muted-foreground" />
        <h3 className="text-sm font-semibold">Trader Summary</h3>
      </div>

      <div className="space-y-3 text-xs">
        <div>
          <div className="text-muted-foreground font-medium mb-1 uppercase tracking-wide text-[10px]">
            What is happening
          </div>
          <p className="text-foreground/90">
            {summary?.what_is_happening?.split("**").map((part: string, i: number) =>
              i % 2 === 0 ? part : <strong key={i}>{part}</strong>
            )}
          </p>
        </div>

        {summary?.assets_that_benefit?.length > 0 && (
          <div>
            <div className="text-muted-foreground font-medium mb-1 uppercase tracking-wide text-[10px]">
              Assets that benefit
            </div>
            <div className="flex flex-wrap gap-1">
              {summary.assets_that_benefit.map((a: string) => (
                <span key={a} className="badge-bullish">{a}</span>
              ))}
            </div>
          </div>
        )}

        {summary?.assets_that_struggle?.length > 0 && (
          <div>
            <div className="text-muted-foreground font-medium mb-1 uppercase tracking-wide text-[10px]">
              Assets that struggle
            </div>
            <div className="flex flex-wrap gap-1">
              {summary.assets_that_struggle.map((a: string) => (
                <span key={a} className="badge-bearish">{a}</span>
              ))}
            </div>
          </div>
        )}

        <div className="pt-2 border-t border-border/50">
          <div className="text-muted-foreground font-medium mb-1 uppercase tracking-wide text-[10px]">
            Key Watch
          </div>
          <p className="text-muted-foreground">{summary?.key_watch}</p>
        </div>
      </div>
    </div>
  );
}

function AssetSection({
  title,
  icon,
  signals,
  compact = false,
}: {
  title: string;
  icon: string;
  signals: any[];
  compact?: boolean;
}) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <span>{icon}</span>
        <h2 className="text-sm font-semibold">{title}</h2>
        <span className="text-xs text-muted-foreground">({signals.length})</span>
      </div>
      {signals.length === 0 ? (
        <div className="card-base text-center py-6 text-sm text-muted-foreground">
          No data available
        </div>
      ) : (
        <div className={cn(
          "grid gap-3",
          compact
            ? "grid-cols-1"
            : "grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7"
        )}>
          {signals.map((signal) => (
            <BiasCard key={signal.symbol} signal={signal} compact={compact} />
          ))}
        </div>
      )}
    </div>
  );
}

function TraderModeSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 w-48 bg-border rounded" />
      <div className="grid grid-cols-3 gap-4">
        {[1, 2, 3].map(i => (
          <div key={i} className="h-48 bg-card border border-border rounded-xl" />
        ))}
      </div>
      <div className="h-24 bg-card border border-border rounded-xl" />
      <div className="grid grid-cols-4 gap-3">
        {[1,2,3,4,5,6,7].map(i => (
          <div key={i} className="h-40 bg-card border border-border rounded-xl" />
        ))}
      </div>
    </div>
  );
}
