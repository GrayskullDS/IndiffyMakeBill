/**
 * API client for MacroIntel backend.
 */
import axios from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// Types
export interface RegimeScores {
  growth: number;
  inflation: number;
  labor: number;
  monetary: number;
  risk: number;
  liquidity: number;
}

export interface MacroRegime {
  date: string;
  regime_type: string;
  regime_label: string;
  regime_confidence: number;
  regime_duration_days?: number;
  scores: RegimeScores;
  phases: { growth: string; inflation: string };
  macro_composite_score: number;
  recession_probability: number;
  favorable_assets: string[];
  unfavorable_assets: string[];
  regime_summary: string;
  key_drivers: string[];
  is_regime_change: boolean;
  previous_regime?: string;
}

export interface BiasSignal {
  symbol: string;
  name: string;
  asset_class: string;
  direction: string;
  strength_score: number;
  confidence: number;
  components?: {
    macro_alignment: number;
    rate_differential: number;
    growth_inflation: number;
    risk_sentiment: number;
    cot_positioning: number;
    seasonality: number;
    technical: number;
  };
  timing_label?: string;
  volatility_regime?: string;
  is_favorable_environment?: boolean;
  macro_drivers?: string[];
  summary_text?: string;
}

export interface TraderOverview {
  date: string;
  regime: {
    type: string;
    label: string;
    confidence: number;
    scores: RegimeScores;
    recession_probability: number;
    regime_summary: string;
  };
  trade_environment: {
    label: string;
    type: string;
    description: string;
    trade_style: string;
  };
  bias_signals: BiasSignal[];
  trader_summary: {
    what_is_happening: string;
    why_it_matters: string;
    assets_that_benefit: string[];
    assets_that_struggle: string[];
    trade_environment: string;
    recommended_style: string;
    recession_risk: string;
    key_watch: string;
  };
}

export interface COTReading {
  report_date: string;
  noncommercial_net: number;
  net_position_index: number;
  percentile_52w: number;
  positioning_extreme: boolean;
  open_interest: number;
}

export interface AssetContext {
  asset: { symbol: string; name: string; asset_class: string };
  bias: BiasSignal & {
    key_risks: string[];
  };
  cot_positioning: COTReading[];
  seasonality: Array<{
    month: number;
    avg_return: number;
    win_rate: number;
    std_dev: number;
    sample_size: number;
  }>;
  price_history: Array<{
    date: string;
    close: number;
    sma_20?: number;
    sma_50?: number;
    sma_200?: number;
    rsi_14?: number;
  }>;
}

// API functions
export const macroIntelApi = {
  // Regime
  getCurrentRegime: () => api.get<MacroRegime>("/regime/current").then(r => r.data),
  getRegimeHistory: (days = 365) =>
    api.get<MacroRegime[]>(`/regime/history?days=${days}`).then(r => r.data),
  getScoresHeatmap: (days = 180) =>
    api.get(`/regime/scores/heatmap?days=${days}`).then(r => r.data),

  // Trader Mode
  getTraderOverview: () => api.get<TraderOverview>("/trader/overview").then(r => r.data),
  getAllBiasSignals: (assetClass?: string) =>
    api.get<BiasSignal[]>(`/trader/bias${assetClass ? `?asset_class=${assetClass}` : ""}`).then(r => r.data),
  getAssetContext: (symbol: string) =>
    api.get<AssetContext>(`/trader/asset/${symbol}`).then(r => r.data),
  getBiasHistory: (symbol: string, days = 90) =>
    api.get(`/trader/bias/history/${symbol}?days=${days}`).then(r => r.data),

  // Macro
  getIndicators: (category?: string) =>
    api.get(`/macro/indicators${category ? `?category=${category}` : ""}`).then(r => r.data),
  getIndicatorSeries: (code: string, days = 365) =>
    api.get(`/macro/indicators/${code}/series?days=${days}`).then(r => r.data),
  getMacroDashboard: () => api.get("/macro/dashboard").then(r => r.data),

  // Alerts
  getAlerts: (days = 30) => api.get(`/alerts/?days=${days}`).then(r => r.data),

  // Pipeline
  runPipeline: (backfill = false) =>
    api.post(`/pipeline/run?backfill=${backfill}`).then(r => r.data),

  // Assets
  listAssets: () => api.get("/assets").then(r => r.data),
};
