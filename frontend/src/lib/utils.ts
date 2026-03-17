import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatScore(score: number | null | undefined): string {
  if (score == null) return "—";
  return score.toFixed(1);
}

export function formatPct(value: number | null | undefined, decimals = 1): string {
  if (value == null) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(decimals)}%`;
}

export function formatNumber(value: number | null | undefined): string {
  if (value == null) return "—";
  if (Math.abs(value) >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (Math.abs(value) >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (Math.abs(value) >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (Math.abs(value) >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
  return value.toFixed(2);
}

export type BiasDirection =
  | "strong_bullish" | "bullish" | "neutral_bullish"
  | "neutral"
  | "neutral_bearish" | "bearish" | "strong_bearish";

export function getBiasColor(direction: BiasDirection | string): string {
  const map: Record<string, string> = {
    strong_bullish: "text-green-400",
    bullish: "text-green-400",
    neutral_bullish: "text-emerald-500",
    neutral: "text-slate-400",
    neutral_bearish: "text-orange-400",
    bearish: "text-red-400",
    strong_bearish: "text-red-500",
  };
  return map[direction] ?? "text-slate-400";
}

export function getBiasBg(direction: BiasDirection | string): string {
  const map: Record<string, string> = {
    strong_bullish: "bg-green-500/15 border-green-500/30 text-green-400",
    bullish: "bg-green-500/10 border-green-500/20 text-green-400",
    neutral_bullish: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400",
    neutral: "bg-slate-500/10 border-slate-500/20 text-slate-400",
    neutral_bearish: "bg-orange-500/10 border-orange-500/20 text-orange-400",
    bearish: "bg-red-500/10 border-red-500/20 text-red-400",
    strong_bearish: "bg-red-500/15 border-red-500/30 text-red-400",
  };
  return map[direction] ?? "bg-slate-500/10 border-slate-500/20 text-slate-400";
}

export function getBiasLabel(direction: string): string {
  const map: Record<string, string> = {
    strong_bullish: "Strong Bullish",
    bullish: "Bullish",
    neutral_bullish: "Neutral/Bullish",
    neutral: "Neutral",
    neutral_bearish: "Neutral/Bearish",
    bearish: "Bearish",
    strong_bearish: "Strong Bearish",
  };
  return map[direction] ?? direction;
}

export function getRegimeColor(regimeType: string): string {
  const map: Record<string, string> = {
    risk_on_expansion: "text-green-400",
    risk_off_fear: "text-red-400",
    inflationary_boom: "text-orange-400",
    deflationary_slowdown: "text-blue-400",
    policy_tightening: "text-purple-400",
    policy_easing: "text-cyan-400",
    liquidity_expansion: "text-emerald-400",
    liquidity_contraction: "text-rose-400",
    stagflation: "text-amber-400",
    recovery: "text-sky-400",
  };
  return map[regimeType] ?? "text-slate-400";
}

export function getRegimeBg(regimeType: string): string {
  const map: Record<string, string> = {
    risk_on_expansion: "bg-green-500/10 border-green-500/20 text-green-400",
    risk_off_fear: "bg-red-500/10 border-red-500/20 text-red-400",
    inflationary_boom: "bg-orange-500/10 border-orange-500/20 text-orange-400",
    deflationary_slowdown: "bg-blue-500/10 border-blue-500/20 text-blue-400",
    policy_tightening: "bg-purple-500/10 border-purple-500/20 text-purple-400",
    policy_easing: "bg-cyan-500/10 border-cyan-500/20 text-cyan-400",
    liquidity_expansion: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400",
    liquidity_contraction: "bg-rose-500/10 border-rose-500/20 text-rose-400",
    stagflation: "bg-amber-500/10 border-amber-500/20 text-amber-400",
    recovery: "bg-sky-500/10 border-sky-500/20 text-sky-400",
  };
  return map[regimeType] ?? "bg-slate-500/10 border-slate-500/20 text-slate-400";
}

export function getScoreColor(score: number): string {
  if (score >= 7.5) return "text-green-400";
  if (score >= 6.0) return "text-emerald-400";
  if (score >= 4.5) return "text-slate-300";
  if (score >= 3.0) return "text-orange-400";
  return "text-red-400";
}

export function getScoreBarColor(score: number): string {
  if (score >= 7.5) return "bg-green-500";
  if (score >= 6.0) return "bg-emerald-500";
  if (score >= 4.5) return "bg-slate-400";
  if (score >= 3.0) return "bg-orange-500";
  return "bg-red-500";
}

export function getVolatilityColor(regime: string): string {
  const map: Record<string, string> = {
    extreme: "text-red-400",
    high: "text-orange-400",
    elevated: "text-yellow-400",
    normal: "text-slate-400",
    low: "text-emerald-400",
  };
  return map[regime] ?? "text-slate-400";
}

export const MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];
