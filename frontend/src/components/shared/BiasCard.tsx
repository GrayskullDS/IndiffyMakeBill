"use client";
import { cn, getBiasBg, getBiasLabel, getScoreBarColor } from "@/lib/utils";
import type { BiasSignal } from "@/lib/api";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

interface BiasCardProps {
  signal: BiasSignal;
  compact?: boolean;
}

const ASSET_CLASS_ICONS: Record<string, string> = {
  forex: "💱",
  equity_index: "📈",
  commodity: "🥇",
  bond: "🏦",
  crypto: "₿",
};

const COMPONENT_LABELS: Record<string, string> = {
  macro_alignment: "Macro",
  rate_differential: "Rates",
  growth_inflation: "G/I",
  risk_sentiment: "Risk",
  cot_positioning: "COT",
  seasonality: "Season",
  technical: "Tech",
};

export function BiasCard({ signal, compact = false }: BiasCardProps) {
  const biasBg = getBiasBg(signal.direction);

  return (
    <div className="card-base hover:border-border/80 transition-all duration-200 group">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">
            {ASSET_CLASS_ICONS[signal.asset_class] ?? "📊"}
          </span>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-bold text-foreground font-mono">
                {signal.symbol}
              </span>
              <Link href={`/assets/${signal.symbol}`}>
                <ArrowUpRight className="w-3 h-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </Link>
            </div>
            <div className="text-[11px] text-muted-foreground">{signal.name}</div>
          </div>
        </div>
        <div className={cn("px-2 py-0.5 rounded-md border text-[11px] font-semibold", biasBg)}>
          {getBiasLabel(signal.direction)}
        </div>
      </div>

      {/* Score bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-muted-foreground">Strength</span>
          <span className="text-xs font-mono font-semibold text-foreground">
            {signal.strength_score?.toFixed(1) ?? "—"}/10
          </span>
        </div>
        <div className="score-bar h-2">
          <div
            className={cn("score-bar-fill", getScoreBarColor(signal.strength_score ?? 5))}
            style={{ width: `${((signal.strength_score ?? 5) / 10) * 100}%` }}
          />
        </div>
      </div>

      {/* Confidence */}
      <div className="flex items-center justify-between text-xs mb-3">
        <span className="text-muted-foreground">Confidence</span>
        <span className="font-mono text-foreground">
          {signal.confidence ? `${Math.round(signal.confidence * 100)}%` : "—"}
        </span>
      </div>

      {/* Component mini-bars (if not compact) */}
      {!compact && signal.components && (
        <div className="grid grid-cols-7 gap-1 pt-2 border-t border-border/50">
          {Object.entries(signal.components).map(([key, val]) => (
            <div key={key} className="flex flex-col items-center gap-1">
              <div className="w-full h-10 bg-border rounded-sm overflow-hidden flex flex-col justify-end">
                <div
                  className={cn("w-full transition-all duration-500", getScoreBarColor(val ?? 5))}
                  style={{ height: `${((val ?? 5) / 10) * 100}%` }}
                />
              </div>
              <span className="text-[9px] text-muted-foreground">
                {COMPONENT_LABELS[key] ?? key}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Timing label */}
      {signal.timing_label && (
        <div className="mt-2 pt-2 border-t border-border/50">
          <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
            {signal.timing_label?.replace(/_/g, " ")}
          </span>
        </div>
      )}
    </div>
  );
}
