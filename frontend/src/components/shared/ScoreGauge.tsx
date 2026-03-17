"use client";
import { cn, getScoreColor, getScoreBarColor } from "@/lib/utils";

interface ScoreGaugeProps {
  label: string;
  score: number | null | undefined;
  description?: string;
  size?: "sm" | "md" | "lg";
  showBar?: boolean;
  invertColors?: boolean; // For monetary score: high=hawkish=bad for risk assets
}

export function ScoreGauge({
  label,
  score,
  description,
  size = "md",
  showBar = true,
  invertColors = false,
}: ScoreGaugeProps) {
  const s = score ?? 5;
  const displayScore = invertColors ? 10 - s : s;
  const colorScore = displayScore;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className={cn(
          "text-muted-foreground",
          size === "sm" ? "text-xs" : "text-sm"
        )}>
          {label}
        </span>
        <span className={cn(
          "font-mono font-semibold",
          size === "sm" ? "text-sm" : "text-base",
          getScoreColor(colorScore)
        )}>
          {s.toFixed(1)}
        </span>
      </div>
      {showBar && (
        <div className="score-bar">
          <div
            className={cn("score-bar-fill", getScoreBarColor(colorScore))}
            style={{ width: `${(s / 10) * 100}%` }}
          />
        </div>
      )}
      {description && (
        <p className="text-[11px] text-muted-foreground">{description}</p>
      )}
    </div>
  );
}
