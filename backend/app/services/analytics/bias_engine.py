"""
Directional Bias Engine.

Generates directional bias (Bullish/Bearish/Neutral) with strength score
and confidence level for each tracked asset.

Component weights per asset class:
┌─────────────────────────┬────────┬──────────┬──────────┬──────────┬──────────┐
│ Component               │ Forex  │ Equities │ Gold     │ Bonds    │ Oil      │
├─────────────────────────┼────────┼──────────┼──────────┼──────────┼──────────┤
│ Macro alignment         │ 20%    │ 30%      │ 20%      │ 25%      │ 20%      │
│ Rate differential       │ 30%    │ 5%       │ 20%      │ 25%      │ 5%       │
│ Growth/inflation regime │ 10%    │ 20%      │ 15%      │ 15%      │ 20%      │
│ Risk sentiment          │ 15%    │ 20%      │ 20%      │ 15%      │ 20%      │
│ COT positioning         │ 15%    │ 10%      │ 15%      │ 10%      │ 20%      │
│ Seasonality             │ 5%     │ 10%      │ 5%       │ 5%       │ 10%      │
│ Technical (trend)       │ 5%     │ 5%       │ 5%       │ 5%       │ 5%       │
└─────────────────────────┴────────┴──────────┴──────────┴──────────┴──────────┘
"""
import logging
from typing import Optional
import pandas as pd
import numpy as np
from app.services.analytics.score_builder import ScoreBuilder

logger = logging.getLogger(__name__)

# Weights per asset class
WEIGHTS = {
    "forex": {
        "macro_alignment": 0.20,
        "rate_differential": 0.30,
        "growth_inflation": 0.10,
        "risk_sentiment": 0.15,
        "cot_positioning": 0.15,
        "seasonality": 0.05,
        "technical": 0.05,
    },
    "equity_index": {
        "macro_alignment": 0.30,
        "rate_differential": 0.05,
        "growth_inflation": 0.20,
        "risk_sentiment": 0.20,
        "cot_positioning": 0.10,
        "seasonality": 0.10,
        "technical": 0.05,
    },
    "commodity_gold": {
        "macro_alignment": 0.20,
        "rate_differential": 0.20,
        "growth_inflation": 0.15,
        "risk_sentiment": 0.20,
        "cot_positioning": 0.15,
        "seasonality": 0.05,
        "technical": 0.05,
    },
    "bond": {
        "macro_alignment": 0.25,
        "rate_differential": 0.25,
        "growth_inflation": 0.15,
        "risk_sentiment": 0.15,
        "cot_positioning": 0.10,
        "seasonality": 0.05,
        "technical": 0.05,
    },
    "commodity_oil": {
        "macro_alignment": 0.20,
        "rate_differential": 0.05,
        "growth_inflation": 0.20,
        "risk_sentiment": 0.20,
        "cot_positioning": 0.20,
        "seasonality": 0.10,
        "technical": 0.05,
    },
}

# Direction thresholds (0-10 composite score)
DIRECTION_THRESHOLDS = [
    (8.5, "strong_bullish"),
    (6.5, "bullish"),
    (5.5, "neutral_bullish"),
    (4.5, "neutral"),
    (3.5, "neutral_bearish"),
    (1.5, "bearish"),
    (0.0, "strong_bearish"),
]

DIRECTION_LABELS = {
    "strong_bullish": "Strong Bullish",
    "bullish": "Bullish",
    "neutral_bullish": "Neutral/Bullish",
    "neutral": "Neutral",
    "neutral_bearish": "Neutral/Bearish",
    "bearish": "Bearish",
    "strong_bearish": "Strong Bearish",
}


class BiasEngine:
    """
    Calculates directional bias for a given asset using macro, positioning,
    sentiment, and technical data.
    """

    def __init__(self):
        self.score_builder = ScoreBuilder()

    def calculate_bias(
        self,
        symbol: str,
        asset_class: str,                   # "forex", "equity_index", "bond", etc.
        regime_data: dict,                  # Output from RegimeClassifier
        rate_data: Optional[dict] = None,   # Interest rate differential data
        cot_score: float = 5.0,            # 0-10 from COTFetcher
        seasonality_score: float = 5.0,     # 0-10 from SeasonalityCalculator
        technical_score: float = 5.0,       # 0-10 from price/trend analysis
        vix_level: float = 20.0,
        credit_spread: float = 3.0,         # HY spread in %
    ) -> dict:
        """
        Calculate directional bias for a single asset.
        Returns bias dict with direction, strength, confidence, and context.
        """
        # Map asset_class to weights profile
        weight_key = self._get_weight_key(symbol, asset_class)
        weights = WEIGHTS.get(weight_key, WEIGHTS["equity_index"])

        # --- Calculate component scores (0-10) ---

        # 1. Macro alignment score
        macro_score = self._macro_alignment_score(symbol, regime_data, asset_class)

        # 2. Rate differential score
        rate_score = self._rate_differential_score(symbol, asset_class, rate_data, regime_data)

        # 3. Growth/inflation regime score
        gi_score = self._growth_inflation_score(symbol, asset_class, regime_data)

        # 4. Risk sentiment score
        risk_score = self._risk_sentiment_score(
            symbol, asset_class, regime_data, vix_level, credit_spread
        )

        # 5. COT positioning score (passed in)
        cot = max(0.0, min(10.0, cot_score))

        # 6. Seasonality score (passed in)
        seasonal = max(0.0, min(10.0, seasonality_score))

        # 7. Technical score (passed in)
        technical = max(0.0, min(10.0, technical_score))

        # --- Weighted composite ---
        composite = (
            weights["macro_alignment"] * macro_score +
            weights["rate_differential"] * rate_score +
            weights["growth_inflation"] * gi_score +
            weights["risk_sentiment"] * risk_score +
            weights["cot_positioning"] * cot +
            weights["seasonality"] * seasonal +
            weights["technical"] * technical
        )

        composite = max(0.0, min(10.0, composite))

        # --- Confidence: std dev of component scores (lower variance = higher confidence) ---
        components = [macro_score, rate_score, gi_score, risk_score, cot, seasonal, technical]
        std_dev = float(np.std(components))
        max_std = 5.0  # Max possible std for 0-10 range
        confidence = max(0.1, min(1.0, 1.0 - (std_dev / max_std)))

        # --- Determine direction ---
        direction = self._score_to_direction(composite)
        strength_score = round(composite, 1)

        # --- Timing classification ---
        timing_label = self._classify_timing(vix_level, regime_data)
        volatility_regime = self._classify_volatility(vix_level)

        # --- Build context ---
        macro_drivers = self._identify_macro_drivers(symbol, regime_data, asset_class)
        is_favorable = regime_data.get("regime_type") in self._favorable_regimes(symbol)

        summary = self._build_summary(
            symbol=symbol,
            direction=direction,
            strength=strength_score,
            confidence=confidence,
            regime=regime_data.get("regime_label", ""),
            macro_drivers=macro_drivers,
        )

        return {
            "symbol": symbol,
            "direction": direction,
            "direction_label": DIRECTION_LABELS.get(direction, direction),
            "strength_score": strength_score,
            "confidence": round(confidence, 2),
            "components": {
                "macro_alignment": round(macro_score, 2),
                "rate_differential": round(rate_score, 2),
                "growth_inflation": round(gi_score, 2),
                "risk_sentiment": round(risk_score, 2),
                "cot_positioning": round(cot, 2),
                "seasonality": round(seasonal, 2),
                "technical": round(technical, 2),
            },
            "timing_label": timing_label,
            "volatility_regime": volatility_regime,
            "is_favorable_environment": is_favorable,
            "macro_drivers": macro_drivers,
            "summary_text": summary,
        }

    def _get_weight_key(self, symbol: str, asset_class: str) -> str:
        """Map symbol/class to a weights profile key."""
        if symbol in ("GOLD", "XAUUSD", "SILVER"):
            return "commodity_gold"
        if symbol in ("CRUDE_OIL", "BRENT", "NATURAL_GAS"):
            return "commodity_oil"
        if "USD" in symbol or "EUR" in symbol or "GBP" in symbol or "JPY" in symbol:
            return "forex"
        if asset_class == "bond":
            return "bond"
        return "equity_index"

    def _macro_alignment_score(self, symbol: str, regime: dict, asset_class: str) -> float:
        """Score based on whether current regime favors this asset."""
        favorable = regime.get("favorable_assets", [])
        unfavorable = regime.get("unfavorable_assets", [])
        composite = regime.get("macro_composite_score", 0)

        if symbol in favorable:
            base = 7.0 + abs(composite) * 0.3
        elif symbol in unfavorable:
            base = 3.0 - abs(composite) * 0.3
        else:
            base = 5.0 + composite * 0.2

        return max(0.0, min(10.0, base))

    def _rate_differential_score(
        self,
        symbol: str,
        asset_class: str,
        rate_data: Optional[dict],
        regime: dict,
    ) -> float:
        """
        For forex: positive rate differential = bullish base currency.
        For gold: real rates rising = bearish gold.
        For bonds: rate expectations rising = bearish bonds.
        """
        monetary_score = regime.get("scores", {}).get("monetary", 5.0)

        if asset_class == "forex":
            if rate_data and symbol in rate_data:
                diff = rate_data[symbol].get("rate_differential", 0)
                # Positive diff (base has higher rates) → bullish base
                score = 5.0 + diff * 1.0
                return max(0.0, min(10.0, score))
            # Fall back to monetary policy stance
            if "JPY" in symbol or "CHF" in symbol:
                return 10 - monetary_score  # JPY/CHF benefit from low rates
            return monetary_score

        elif symbol in ("GOLD", "XAUUSD", "SILVER"):
            # Gold is inversely related to real rates
            # High real rates (monetary tight) → bearish gold
            return max(0.0, min(10.0, 10 - monetary_score))

        elif asset_class == "bond":
            # Rising rates (hawkish) = falling bond prices
            return max(0.0, min(10.0, 10 - monetary_score))

        elif asset_class == "equity_index":
            # Moderate rates OK, very high rates bad for equities
            if monetary_score > 7:
                return 3.0
            elif monetary_score > 5:
                return 5.0
            return 7.0

        return 5.0

    def _growth_inflation_score(self, symbol: str, asset_class: str, regime: dict) -> float:
        """Score asset based on growth and inflation regime."""
        growth = regime.get("scores", {}).get("growth", 5.0)
        inflation = regime.get("scores", {}).get("inflation", 5.0)
        regime_type = regime.get("regime_type", "")

        if asset_class == "equity_index":
            # Goldilocks (high growth, low inflation) best for equities
            score = growth * 0.6 - (inflation - 5) * 0.3 + 5 * 0.4
            return max(0.0, min(10.0, score))

        elif symbol in ("GOLD", "XAUUSD", "SILVER"):
            # Gold loves high inflation, risk-off, low real rates
            score = inflation * 0.5 + (10 - growth) * 0.2 + 5 * 0.3
            if regime_type == "stagflation":
                score += 2
            return max(0.0, min(10.0, score))

        elif symbol in ("CRUDE_OIL", "BRENT"):
            # Oil loves inflationary boom and strong growth
            score = growth * 0.5 + inflation * 0.3 + 5 * 0.2
            return max(0.0, min(10.0, score))

        elif asset_class == "bond":
            # Bonds love low growth and low inflation (deflation scenario)
            score = (10 - growth) * 0.5 + (10 - inflation) * 0.5
            return max(0.0, min(10.0, score))

        return 5.0

    def _risk_sentiment_score(
        self,
        symbol: str,
        asset_class: str,
        regime: dict,
        vix: float,
        credit_spread: float,
    ) -> float:
        """Score based on risk appetite (VIX, credit spreads, regime risk score)."""
        risk = regime.get("scores", {}).get("risk", 5.0)

        # VIX adjustment: high VIX = risk-off environment
        vix_penalty = 0
        if vix > 30:
            vix_penalty = -2
        elif vix > 20:
            vix_penalty = -1
        elif vix < 15:
            vix_penalty = +1

        # Credit spread adjustment
        spread_penalty = 0
        if credit_spread > 6:
            spread_penalty = -2
        elif credit_spread > 4:
            spread_penalty = -1

        if asset_class == "equity_index":
            score = risk + vix_penalty + spread_penalty
        elif symbol in ("GOLD", "XAUUSD", "USDJPY", "USDCHF"):
            # Safe havens benefit from risk-off
            score = 10 - risk - vix_penalty
        elif asset_class == "bond":
            score = 10 - risk + abs(vix_penalty)
        elif symbol in ("CRUDE_OIL", "BRENT", "AUDUSD", "NZDUSD"):
            # Risk assets
            score = risk + vix_penalty + spread_penalty
        else:
            score = risk + vix_penalty * 0.5

        return max(0.0, min(10.0, score))

    def _score_to_direction(self, composite: float) -> str:
        """Map composite score to direction label."""
        for threshold, label in DIRECTION_THRESHOLDS:
            if composite >= threshold:
                return label
        return "strong_bearish"

    def _classify_timing(self, vix: float, regime: dict) -> str:
        """Classify current trade timing environment."""
        risk_score = regime.get("scores", {}).get("risk", 5.0)
        if vix > 30:
            return "high_volatility_regime"
        if vix < 12:
            return "low_volatility_mean_reversion"
        if risk_score >= 7:
            return "trend_following_favorable"
        if risk_score <= 3:
            return "risk_off_defensive"
        return "mixed_environment"

    def _classify_volatility(self, vix: float) -> str:
        if vix > 35:
            return "extreme"
        if vix > 25:
            return "high"
        if vix > 18:
            return "elevated"
        if vix > 12:
            return "normal"
        return "low"

    def _favorable_regimes(self, symbol: str) -> list[str]:
        """Return regime types that historically favor this asset."""
        ASSET_REGIMES = {
            "SPX": ["risk_on_expansion", "recovery", "liquidity_expansion", "policy_easing"],
            "NDX": ["risk_on_expansion", "recovery", "liquidity_expansion"],
            "GOLD": ["risk_off_fear", "inflationary_boom", "stagflation", "policy_easing", "liquidity_expansion"],
            "CRUDE_OIL": ["risk_on_expansion", "inflationary_boom", "liquidity_expansion"],
            "US10Y": ["risk_off_fear", "deflationary_slowdown", "policy_easing"],
            "AUDUSD": ["risk_on_expansion", "inflationary_boom", "recovery"],
            "EURUSD": ["risk_on_expansion", "policy_easing"],
            "USDJPY": ["policy_tightening", "risk_on_expansion"],
        }
        return ASSET_REGIMES.get(symbol, [])

    def _identify_macro_drivers(self, symbol: str, regime: dict, asset_class: str) -> list[str]:
        """Identify top 3-4 macro drivers for this asset."""
        scores = regime.get("scores", {})
        drivers = []

        growth = scores.get("growth", 5)
        inflation = scores.get("inflation", 5)
        monetary = scores.get("monetary", 5)
        risk = scores.get("risk", 5)
        liquidity = scores.get("liquidity", 5)

        if monetary >= 7:
            drivers.append("Hawkish monetary policy / rate hike cycle active")
        elif monetary <= 3:
            drivers.append("Dovish Fed / rate cut cycle / easing policy")

        if growth >= 7:
            drivers.append("Strong economic growth momentum")
        elif growth <= 3:
            drivers.append("Deteriorating economic growth / contraction risk")

        if inflation >= 7:
            drivers.append("Elevated inflation pressures")
        elif inflation <= 3:
            drivers.append("Disinflationary / deflationary environment")

        if risk >= 7:
            drivers.append("Risk-on sentiment: equities bid, safe-havens sold")
        elif risk <= 3:
            drivers.append("Risk-off: flight to safety (gold, yen, bonds)")

        if liquidity >= 7:
            drivers.append("Expanding liquidity supports asset prices")
        elif liquidity <= 3:
            drivers.append("Tightening liquidity (QT) creating headwinds")

        return drivers[:4]

    def _build_summary(
        self,
        symbol: str,
        direction: str,
        strength: float,
        confidence: float,
        regime: str,
        macro_drivers: list[str],
    ) -> str:
        """Generate plain-language bias summary."""
        conf_pct = int(confidence * 100)
        dir_label = DIRECTION_LABELS.get(direction, direction)
        drivers_text = "; ".join(macro_drivers[:2]) if macro_drivers else "mixed macro signals"

        return (
            f"{symbol} shows a **{dir_label}** bias (strength: {strength}/10, "
            f"confidence: {conf_pct}%) in the current **{regime}** regime. "
            f"Key drivers: {drivers_text}."
        )


bias_engine = BiasEngine()
