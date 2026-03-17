"use client";
import { useQuery } from "@tanstack/react-query";
import { macroIntelApi } from "@/lib/api";
import { cn, getRegimeBg, getScoreBarColor, getScoreColor, formatNumber } from "@/lib/utils";
import { ScoreGauge } from "@/components/shared/ScoreGauge";
import { BiasCard } from "@/components/shared/BiasCard";
import {
  Activity, TrendingUp, Globe, AlertTriangle, ArrowRight, Zap,
} from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const { data: regime, isLoading: regimeLoading } = useQuery({
    queryKey: ["regime-current"],
    queryFn: macroIntelApi.getCurrentRegime,
    refetchInterval: 5 * 60 * 1000,
  });

  const { data: traderData } = useQuery({
    queryKey: ["trader-overview"],
    queryFn: macroIntelApi.getTraderOverview,
    refetchInterval: 5 * 60 * 1000,
  });

  const { data: macroDash } = useQuery({
    queryKey: ["macro-dashboard"],
    queryFn: macroIntelApi.getMacroDashboard,
  });

  const { data: alerts } = useQuery({
    queryKey: ["alerts"],
    queryFn: () => macroIntelApi.getAlerts(7),
  });

  const topBiasSignals = traderData?.bias_signals?.slice(0, 8) ?? [];

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Dashboard</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Macro intelligence overview · {new Date().toLocaleDateString("en-US", {
              weekday: "long", month: "long", day: "numeric"
            })}
          </p>
        </div>
        <Link href="/trader-mode">
          <button className="flex items-center gap-2 bg-primary/10 hover:bg-primary/20 border border-primary/20 text-primary px-3 py-1.5 rounded-lg text-sm font-medium transition-colors">
            <Zap className="w-3.5 h-3.5" />
            Trader Mode
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </Link>
      </div>

      {/* Alert banner */}
      {alerts && alerts.length > 0 && (
        <div className="bg-orange-500/10 border border-orange-500/20 rounded-xl p-3 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-orange-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs">
            <span className="text-orange-400 font-semibold">{alerts[0].title}</span>
            <span className="text-muted-foreground ml-2">{alerts[0].message}</span>
          </div>
        </div>
      )}

      {/* Row 1: Regime + Scores */}
      <div className="grid grid-cols-12 gap-4">
        {/* Regime status card */}
        <div className="col-span-12 md:col-span-5">
          <div className="card-base h-full">
            <div className="flex items-center gap-2 mb-3">
              <Globe className="w-4 h-4 text-muted-foreground" />
              <h2 className="text-sm font-semibold">Current Macro Regime</h2>
            </div>
            {regimeLoading ? (
              <div className="space-y-2 animate-pulse">
                <div className="h-6 w-40 bg-border rounded" />
                <div className="h-4 w-full bg-border rounded" />
                <div className="h-4 w-3/4 bg-border rounded" />
              </div>
            ) : regime ? (
              <>
                <div className={cn(
                  "regime-pill border inline-flex items-center gap-1.5 mb-3 text-sm",
                  getRegimeBg(regime.regime_type)
                )}>
                  {regime.regime_label}
                </div>
                <p className="text-xs text-muted-foreground mb-4">
                  {regime.regime_summary?.slice(0, 200)}...
                </p>
                <div className="grid grid-cols-2 gap-3">
                  {["growth", "inflation", "risk", "monetary"].map((key) => (
                    <ScoreGauge
                      key={key}
                      label={key.charAt(0).toUpperCase() + key.slice(1)}
                      score={regime.scores?.[key as keyof typeof regime.scores]}
                      size="sm"
                    />
                  ))}
                </div>
                <div className="flex gap-4 pt-3 border-t border-border/50 mt-3">
                  <div className="text-xs">
                    <span className="text-muted-foreground">Confidence: </span>
                    <span className="font-mono">{Math.round(regime.regime_confidence * 100)}%</span>
                  </div>
                  <div className="text-xs">
                    <span className="text-muted-foreground">Recession: </span>
                    <span className={cn(
                      "font-mono",
                      regime.recession_probability > 0.5 ? "text-red-400" : "text-green-400"
                    )}>
                      {Math.round(regime.recession_probability * 100)}%
                    </span>
                  </div>
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                No regime data. Run the pipeline first.
              </p>
            )}
          </div>
        </div>

        {/* Macro indicators snapshot */}
        <div className="col-span-12 md:col-span-7">
          <MacroDashboardPanel data={macroDash} />
        </div>
      </div>

      {/* Row 2: Top Bias Signals */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold">Top Asset Biases</h2>
          </div>
          <Link href="/trader-mode" className="text-xs text-primary hover:text-primary/80 flex items-center gap-1">
            View all <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
        {topBiasSignals.length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
            {topBiasSignals.map((signal) => (
              <BiasCard key={signal.symbol} signal={signal} compact />
            ))}
          </div>
        ) : (
          <div className="card-base text-center py-8 text-sm text-muted-foreground">
            No bias signals available. Run the data pipeline to generate signals.
          </div>
        )}
      </div>

      {/* Row 3: Favorable / Unfavorable assets */}
      {regime && (
        <div className="grid grid-cols-2 gap-4">
          <div className="card-base">
            <h3 className="text-xs font-semibold text-green-400 mb-2 uppercase tracking-wider">
              Favorable in Current Regime
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {regime.favorable_assets.map((a) => (
                <span key={a} className="badge-bullish">{a}</span>
              ))}
            </div>
          </div>
          <div className="card-base">
            <h3 className="text-xs font-semibold text-red-400 mb-2 uppercase tracking-wider">
              Unfavorable in Current Regime
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {regime.unfavorable_assets.map((a) => (
                <span key={a} className="badge-bearish">{a}</span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function MacroDashboardPanel({ data }: { data: any }) {
  const KEY_INDICATORS = [
    { code: "FED_FUNDS_RATE", label: "Fed Funds Rate", unit: "%" },
    { code: "UNEMPLOYMENT_RATE", label: "Unemployment", unit: "%" },
    { code: "CPI_YOY", label: "CPI Index", unit: "" },
    { code: "YIELD_CURVE_10Y2Y", label: "10Y-2Y Spread", unit: "%" },
    { code: "VIX", label: "VIX", unit: "" },
    { code: "INFLATION_EXPECTATIONS_5Y", label: "5Y Breakeven", unit: "%" },
  ];

  return (
    <div className="card-base h-full">
      <div className="flex items-center gap-2 mb-3">
        <Activity className="w-4 h-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold">Key Indicators</h2>
      </div>
      <div className="space-y-0">
        {KEY_INDICATORS.map(({ code, label, unit }) => {
          // Find in dashboard data
          let value = null;
          let change = null;
          if (data) {
            for (const cat of Object.values(data as any)) {
              const row = (cat as any[]).find((r: any) => r.code === code);
              if (row) {
                value = row.value;
                change = row.change;
                break;
              }
            }
          }

          return (
            <div key={code} className="flex items-center justify-between py-2 border-b border-border/30 last:border-0">
              <span className="text-xs text-muted-foreground">{label}</span>
              <div className="flex items-center gap-2">
                {change !== null && change !== undefined && (
                  <span className={cn(
                    "text-[10px] font-mono",
                    change > 0 ? "text-green-400" : "text-red-400"
                  )}>
                    {change > 0 ? "▲" : "▼"} {Math.abs(change).toFixed(2)}
                  </span>
                )}
                <span className="text-sm font-mono font-semibold text-foreground">
                  {value !== null ? `${Number(value).toFixed(2)}${unit}` : "—"}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
