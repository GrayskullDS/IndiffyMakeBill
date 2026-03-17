"use client";
import { Bell, RefreshCw } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { macroIntelApi } from "@/lib/api";
import { cn, getRegimeBg } from "@/lib/utils";
import { useState } from "react";

export function TopBar() {
  const [refreshing, setRefreshing] = useState(false);

  const { data: regime } = useQuery({
    queryKey: ["regime-current"],
    queryFn: macroIntelApi.getCurrentRegime,
    refetchInterval: 5 * 60 * 1000, // 5 min
  });

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await macroIntelApi.runPipeline(false);
    } finally {
      setTimeout(() => setRefreshing(false), 2000);
    }
  };

  return (
    <header className="h-12 border-b border-border bg-card/50 backdrop-blur-sm flex items-center justify-between px-4 flex-shrink-0">
      {/* Left: live regime badge */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          <span className="text-xs text-muted-foreground">Live</span>
        </div>
        {regime && (
          <div
            className={cn(
              "regime-pill border text-xs",
              getRegimeBg(regime.regime_type)
            )}
          >
            {regime.regime_label}
          </div>
        )}
        {regime && (
          <div className="text-xs text-muted-foreground hidden md:block">
            Confidence: {Math.round(regime.regime_confidence * 100)}% ·
            Recession Risk: {Math.round(regime.recession_probability * 100)}%
          </div>
        )}
      </div>

      {/* Right: actions */}
      <div className="flex items-center gap-2">
        <button
          onClick={handleRefresh}
          className="p-1.5 rounded-lg hover:bg-white/5 text-muted-foreground hover:text-foreground transition-colors"
          title="Refresh data"
        >
          <RefreshCw className={cn("w-3.5 h-3.5", refreshing && "animate-spin")} />
        </button>
        <button className="p-1.5 rounded-lg hover:bg-white/5 text-muted-foreground hover:text-foreground transition-colors">
          <Bell className="w-3.5 h-3.5" />
        </button>
        <div className="text-xs text-muted-foreground font-mono">
          {new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
        </div>
      </div>
    </header>
  );
}
