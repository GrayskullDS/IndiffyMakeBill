"use client";
import { useQuery } from "@tanstack/react-query";
import { macroIntelApi } from "@/lib/api";
import { cn, getBiasBg, getBiasLabel, getScoreBarColor, getScoreColor, MONTH_NAMES } from "@/lib/utils";
import { ScoreGauge } from "@/components/shared/ScoreGauge";
import { useParams } from "next/navigation";
import {
  ArrowLeft, TrendingUp, TrendingDown, BarChart2,
  Calendar, Users, AlertCircle
} from "lucide-react";
import Link from "next/link";

export default function AssetDetailPage() {
  const params = useParams();
  const symbol = (params.symbol as string).toUpperCase();

  const { data, isLoading, error } = useQuery({
    queryKey: ["asset-context", symbol],
    queryFn: () => macroIntelApi.getAssetContext(symbol),
  });

  if (isLoading) return <div className="animate-pulse space-y-4">
    {[1,2,3].map(i => <div key={i} className="h-40 bg-card border border-border rounded-xl" />)}
  </div>;

  if (error || !data) return (
    <div className="text-center py-12 text-muted-foreground">
      <AlertCircle className="w-8 h-8 mx-auto mb-2 text-orange-400" />
      Asset not found or no data available.
    </div>
  );

  const { asset, bias, cot_positioning, seasonality, price_history } = data;
  const currentMonth = new Date().getMonth() + 1;
  const currentSeason = seasonality.find(s => s.month === currentMonth);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/assets">
          <button className="p-1.5 hover:bg-white/5 rounded-lg text-muted-foreground">
            <ArrowLeft className="w-4 h-4" />
          </button>
        </Link>
        <div>
          <h1 className="text-xl font-bold font-mono">{asset.symbol}</h1>
          <p className="text-xs text-muted-foreground capitalize">{asset.asset_class}</p>
        </div>
        {bias.direction && (
          <div className={cn("regime-pill border ml-auto", getBiasBg(bias.direction))}>
            {getBiasLabel(bias.direction)}
          </div>
        )}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-12 gap-4">
        {/* Bias & Components */}
        <div className="col-span-12 lg:col-span-4 space-y-4">
          {/* Bias overview */}
          <div className="card-base">
            <h3 className="text-sm font-semibold mb-3">Directional Bias</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Strength</span>
                <span className={cn("text-xl font-bold font-mono", getScoreColor(bias.strength_score ?? 5))}>
                  {bias.strength_score?.toFixed(1)}/10
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Confidence</span>
                <span>{bias.confidence ? `${Math.round(bias.confidence * 100)}%` : "—"}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Timing</span>
                <span className="capitalize">{bias.timing_label?.replace(/_/g, " ") ?? "—"}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Volatility Regime</span>
                <span className="capitalize">{bias.volatility_regime ?? "—"}</span>
              </div>
            </div>
          </div>

          {/* Component scores */}
          {bias.components && (
            <div className="card-base">
              <h3 className="text-sm font-semibold mb-3">Bias Components</h3>
              <div className="space-y-3">
                {Object.entries(bias.components).map(([key, val]) => (
                  <ScoreGauge
                    key={key}
                    label={key.split("_").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ")}
                    score={val as number}
                    size="sm"
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* COT + Seasonality + Macro Drivers */}
        <div className="col-span-12 lg:col-span-4 space-y-4">
          {/* COT Positioning */}
          <div className="card-base">
            <div className="flex items-center gap-2 mb-3">
              <Users className="w-4 h-4 text-muted-foreground" />
              <h3 className="text-sm font-semibold">Smart Money (COT)</h3>
            </div>
            {cot_positioning.length > 0 ? (
              <>
                {cot_positioning.slice(0, 1).map((cot) => (
                  <div key={cot.report_date} className="space-y-3">
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">Report Date</span>
                      <span className="font-mono">{cot.report_date}</span>
                    </div>
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-muted-foreground">Net Position Index</span>
                        <span className={cn(
                          "font-mono font-semibold",
                          (cot.net_position_index ?? 0) > 0 ? "text-green-400" : "text-red-400"
                        )}>
                          {cot.net_position_index?.toFixed(1) ?? "—"}
                        </span>
                      </div>
                      <div className="score-bar h-2">
                        <div
                          className={cn(
                            "score-bar-fill",
                            (cot.net_position_index ?? 0) > 0 ? "bg-green-500" : "bg-red-500"
                          )}
                          style={{
                            width: `${Math.min(100, Math.abs((cot.net_position_index ?? 0) + 100) / 2)}%`
                          }}
                        />
                      </div>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">52w Percentile</span>
                      <span className={cn(
                        "font-mono",
                        (cot.percentile_52w ?? 50) > 80 ? "text-green-400" :
                        (cot.percentile_52w ?? 50) < 20 ? "text-red-400" : "text-slate-400"
                      )}>
                        {cot.percentile_52w?.toFixed(0) ?? "—"}th
                      </span>
                    </div>
                    {cot.positioning_extreme && (
                      <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-2 text-xs text-orange-400">
                        ⚠ Positioning Extreme Detected
                      </div>
                    )}
                  </div>
                ))}
              </>
            ) : (
              <p className="text-xs text-muted-foreground">No COT data available</p>
            )}
          </div>

          {/* Macro Drivers */}
          <div className="card-base">
            <h3 className="text-sm font-semibold mb-3">Macro Drivers</h3>
            {bias.macro_drivers && bias.macro_drivers.length > 0 ? (
              <ul className="space-y-2">
                {bias.macro_drivers.map((driver, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                    <span className="text-primary mt-0.5 flex-shrink-0">▸</span>
                    {driver}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-muted-foreground">No macro drivers identified</p>
            )}
          </div>
        </div>

        {/* Seasonality */}
        <div className="col-span-12 lg:col-span-4">
          <div className="card-base h-full">
            <div className="flex items-center gap-2 mb-3">
              <Calendar className="w-4 h-4 text-muted-foreground" />
              <h3 className="text-sm font-semibold">Seasonality (10-Year)</h3>
            </div>

            {currentSeason && (
              <div className="mb-4 p-3 bg-primary/5 border border-primary/10 rounded-lg">
                <div className="text-xs text-muted-foreground mb-1">Current Month ({MONTH_NAMES[currentMonth-1]})</div>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <div className="text-muted-foreground">Avg Return</div>
                    <div className={cn("font-mono font-semibold",
                      (currentSeason.avg_return ?? 0) > 0 ? "text-green-400" : "text-red-400"
                    )}>
                      {(currentSeason.avg_return ?? 0) > 0 ? "+" : ""}
                      {(currentSeason.avg_return ?? 0).toFixed(2)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Win Rate</div>
                    <div className="font-mono font-semibold">
                      {(currentSeason.win_rate ?? 0).toFixed(0)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Samples</div>
                    <div className="font-mono">{currentSeason.sample_size ?? 0}</div>
                  </div>
                </div>
              </div>
            )}

            {/* Monthly seasonality bars */}
            <div className="flex items-end gap-1 h-24">
              {MONTH_NAMES.map((month, i) => {
                const s = seasonality.find(x => x.month === i + 1);
                const ret = s?.avg_return ?? 0;
                const maxAbs = Math.max(...seasonality.map(x => Math.abs(x.avg_return ?? 0)), 1);
                const barHeight = (Math.abs(ret) / maxAbs) * 80;
                const isCurrent = i + 1 === currentMonth;

                return (
                  <div key={month} className="flex flex-col items-center gap-0.5 flex-1">
                    <div className="w-full flex flex-col justify-end" style={{ height: "80px" }}>
                      <div
                        className={cn(
                          "w-full rounded-t-sm transition-all",
                          ret > 0 ? "bg-green-500/60" : "bg-red-500/60",
                          isCurrent && "ring-1 ring-primary brightness-125"
                        )}
                        style={{ height: `${barHeight}px` }}
                      />
                    </div>
                    <span className={cn(
                      "text-[9px]",
                      isCurrent ? "text-primary font-semibold" : "text-muted-foreground"
                    )}>
                      {month}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Summary */}
      {bias.summary_text && (
        <div className="card-base">
          <h3 className="text-sm font-semibold mb-2">Analysis Summary</h3>
          <p className="text-sm text-muted-foreground">
            {bias.summary_text.split("**").map((part: string, i: number) =>
              i % 2 === 0 ? part : <strong key={i} className="text-foreground">{part}</strong>
            )}
          </p>
        </div>
      )}
    </div>
  );
}
