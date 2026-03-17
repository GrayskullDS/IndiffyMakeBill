"use client";
import { useQuery } from "@tanstack/react-query";
import { macroIntelApi } from "@/lib/api";
import { cn, getRegimeBg, getScoreBarColor, getScoreColor } from "@/lib/utils";
import { ScoreGauge } from "@/components/shared/ScoreGauge";
import { Globe } from "lucide-react";

const REGIME_DESCRIPTIONS: Record<string, { title: string; description: string; emoji: string }> = {
  risk_on_expansion: {
    title: "Risk-On Expansion",
    description: "Strong economic growth with controlled inflation. Equities, risk assets, and cyclicals lead. Safe-havens underperform.",
    emoji: "🟢",
  },
  risk_off_fear: {
    title: "Risk-Off / Fear",
    description: "Fear and uncertainty dominate markets. Flight to safety — gold, yen, bonds, and CHF rally. Risk assets sold.",
    emoji: "🔴",
  },
  inflationary_boom: {
    title: "Inflationary Boom",
    description: "Strong growth AND rising inflation. Real assets, commodities, and energy outperform. Bonds struggle from rate pressure.",
    emoji: "🟠",
  },
  deflationary_slowdown: {
    title: "Deflationary Slowdown",
    description: "Falling growth AND falling inflation. Bonds rally on rate cut expectations. Commodities and equities struggle.",
    emoji: "🔵",
  },
  policy_tightening: {
    title: "Policy Tightening Cycle",
    description: "Central bank hiking rates aggressively. Dollar positive. Short-term rates benefit. Growth assets and gold under pressure.",
    emoji: "🟣",
  },
  policy_easing: {
    title: "Policy Easing Cycle",
    description: "Central bank cutting rates or signaling easing. Equities, gold, and bonds rally on lower rate expectations.",
    emoji: "🩵",
  },
  liquidity_expansion: {
    title: "Liquidity Expansion",
    description: "Fed balance sheet growing (QE). Abundant liquidity supports nearly all risk assets and suppresses volatility.",
    emoji: "💚",
  },
  liquidity_contraction: {
    title: "Liquidity Contraction",
    description: "Fed balance sheet shrinking (QT). Liquidity withdrawal creates persistent headwinds for most assets.",
    emoji: "🌸",
  },
  stagflation: {
    title: "Stagflation",
    description: "Falling growth + rising inflation — worst macro scenario. Gold and commodities are stagflation hedges. Equities and bonds both suffer.",
    emoji: "🟡",
  },
  recovery: {
    title: "Recovery / Early Cycle",
    description: "Early economic recovery after recession. Equities and cyclicals lead. Inflation still low. Bonds sell off.",
    emoji: "🔷",
  },
};

export default function RegimePage() {
  const { data: regime, isLoading } = useQuery({
    queryKey: ["regime-current"],
    queryFn: macroIntelApi.getCurrentRegime,
  });

  const { data: history } = useQuery({
    queryKey: ["regime-history"],
    queryFn: () => macroIntelApi.getRegimeHistory(365),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Globe className="w-5 h-5 text-muted-foreground" />
        <h1 className="text-xl font-bold">Macro Regime Analysis</h1>
      </div>

      {/* Current regime detail */}
      {regime && !isLoading && (
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12 lg:col-span-5">
            <div className="card-base">
              <div className={cn(
                "regime-pill border inline-flex mb-3 text-sm",
                getRegimeBg(regime.regime_type)
              )}>
                {REGIME_DESCRIPTIONS[regime.regime_type]?.emoji} {regime.regime_label}
              </div>
              <p className="text-sm text-muted-foreground mb-4">
                {REGIME_DESCRIPTIONS[regime.regime_type]?.description}
              </p>
              <div className="space-y-3">
                <ScoreGauge label="Growth Score" score={regime.scores.growth}
                  description="GDP, PMI, industrial production" />
                <ScoreGauge label="Inflation Score" score={regime.scores.inflation}
                  description="CPI, core CPI, PPI, inflation expectations" />
                <ScoreGauge label="Labor Score" score={regime.scores.labor}
                  description="Unemployment, payrolls, wages" />
                <ScoreGauge label="Monetary Hawkishness" score={regime.scores.monetary}
                  description="Fed funds rate, yield curve, real rates" />
                <ScoreGauge label="Risk Appetite" score={regime.scores.risk}
                  description="VIX, credit spreads, financial conditions" />
                <ScoreGauge label="Liquidity Score" score={regime.scores.liquidity}
                  description="Fed balance sheet, M2 growth" />
              </div>
            </div>
          </div>

          <div className="col-span-12 lg:col-span-7 space-y-4">
            {/* Regime stats */}
            <div className="card-base">
              <h3 className="text-sm font-semibold mb-3">Regime Statistics</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Composite Score</div>
                  <div className={cn("text-2xl font-bold font-mono",
                    (regime.macro_composite_score ?? 0) > 0 ? "text-green-400" : "text-red-400"
                  )}>
                    {(regime.macro_composite_score ?? 0) > 0 ? "+" : ""}
                    {(regime.macro_composite_score ?? 0).toFixed(2)}
                  </div>
                  <div className="text-xs text-muted-foreground">-10 (bearish) to +10 (bullish)</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Recession Probability</div>
                  <div className={cn("text-2xl font-bold font-mono",
                    (regime.recession_probability ?? 0) > 0.5 ? "text-red-400" : "text-green-400"
                  )}>
                    {Math.round((regime.recession_probability ?? 0) * 100)}%
                  </div>
                  <div className="text-xs text-muted-foreground">Based on growth, labor & monetary</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Growth Phase</div>
                  <div className="text-base font-semibold capitalize">
                    {regime.phases?.growth?.replace("_", " ") ?? "—"}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Inflation Phase</div>
                  <div className="text-base font-semibold capitalize">
                    {regime.phases?.inflation?.replace("_", " ") ?? "—"}
                  </div>
                </div>
              </div>
            </div>

            {/* Asset performance expectations */}
            <div className="card-base">
              <h3 className="text-sm font-semibold mb-3">
                Asset Performance in <span className={cn(getRegimeBg(regime.regime_type).split(" ")[2])}>{regime.regime_label}</span>
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-xs text-green-400 font-semibold mb-2 uppercase tracking-wider">
                    Typically Outperform
                  </div>
                  <div className="space-y-1">
                    {regime.favorable_assets.map((a) => (
                      <div key={a} className="badge-bullish inline-flex mr-1 mb-1">{a}</div>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-red-400 font-semibold mb-2 uppercase tracking-wider">
                    Typically Underperform
                  </div>
                  <div className="space-y-1">
                    {regime.unfavorable_assets.map((a) => (
                      <div key={a} className="badge-bearish inline-flex mr-1 mb-1">{a}</div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* All regime types reference */}
      <div>
        <h2 className="text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wider">
          Regime Reference Guide
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
          {Object.entries(REGIME_DESCRIPTIONS).map(([key, val]) => (
            <div
              key={key}
              className={cn(
                "card-base border transition-all",
                regime?.regime_type === key
                  ? getRegimeBg(key)
                  : "border-border/50 opacity-70 hover:opacity-100"
              )}
            >
              <div className="text-lg mb-1">{val.emoji}</div>
              <div className="text-xs font-semibold mb-1">{val.title}</div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                {val.description.slice(0, 100)}...
              </p>
              {regime?.regime_type === key && (
                <div className="mt-2 text-[10px] font-semibold text-current uppercase tracking-wider">
                  ● Current Regime
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
