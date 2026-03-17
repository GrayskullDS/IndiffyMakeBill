"""
Macro Regime Classifier.

Classifies the current macro environment into one of 10 regime types
based on composite scores derived from growth, inflation, labor,
monetary policy, and risk appetite indicators.

Regime Classification Matrix:
┌─────────────────┬──────────────┬────────────────────────────────┐
│ Growth          │ Inflation    │ Regime                         │
├─────────────────┼──────────────┼────────────────────────────────┤
│ Rising          │ Rising       │ Inflationary Boom              │
│ Rising          │ Falling      │ Risk-On Expansion              │
│ Falling         │ Rising       │ Stagflation                    │
│ Falling         │ Falling      │ Deflationary Slowdown          │
│ Any             │ Any          │ (modified by policy/liquidity) │
└─────────────────┴──────────────┴────────────────────────────────┘
"""
import logging
from datetime import date
from typing import Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class RegimeClassifier:
    """
    Classifies macro regime from normalized indicator scores.
    All inputs are normalized to 0-10 scale.
    """

    # Regime labels for display
    REGIME_LABELS = {
        "risk_on_expansion": "Risk-On Expansion",
        "risk_off_fear": "Risk-Off / Fear",
        "inflationary_boom": "Inflationary Boom",
        "deflationary_slowdown": "Deflationary Slowdown",
        "policy_tightening": "Policy Tightening Cycle",
        "policy_easing": "Policy Easing Cycle",
        "liquidity_expansion": "Liquidity Expansion",
        "liquidity_contraction": "Liquidity Contraction",
        "stagflation": "Stagflation",
        "recovery": "Recovery / Early Cycle",
    }

    # Assets that typically outperform per regime
    REGIME_ASSET_MAP = {
        "risk_on_expansion": {
            "favorable": ["SPX", "NDX", "EURUSD", "AUDUSD", "CRUDE_OIL", "COPPER"],
            "unfavorable": ["GOLD", "US10Y", "US30Y", "USDJPY", "USDCHF"],
            "description": "Strong growth, controlled inflation. Equities and risk assets lead. "
                           "Defensive assets underperform.",
        },
        "risk_off_fear": {
            "favorable": ["GOLD", "US10Y", "US30Y", "USDJPY", "USDCHF", "DXY"],
            "unfavorable": ["SPX", "NDX", "AUDUSD", "CRUDE_OIL", "COPPER"],
            "description": "Fear and uncertainty dominate. Safe-haven assets rally. "
                           "Risk assets sold off.",
        },
        "inflationary_boom": {
            "favorable": ["GOLD", "CRUDE_OIL", "SILVER", "COPPER", "EURUSD"],
            "unfavorable": ["US10Y", "US30Y", "SPX"],
            "description": "Strong growth AND rising inflation. Real assets and commodities "
                           "benefit. Bonds suffer from rate pressure.",
        },
        "deflationary_slowdown": {
            "favorable": ["US10Y", "US30Y", "GOLD", "USDJPY"],
            "unfavorable": ["CRUDE_OIL", "COPPER", "SPX", "AUDUSD"],
            "description": "Falling growth and falling inflation. Bonds rally on rate cut "
                           "expectations. Commodities and equities struggle.",
        },
        "policy_tightening": {
            "favorable": ["DXY", "USDCAD", "US2Y"],
            "unfavorable": ["GOLD", "SPX", "AUDUSD", "US10Y", "NDX"],
            "description": "Central bank hiking rates aggressively. Dollar and short-term "
                           "rates benefit. Growth assets and gold under pressure.",
        },
        "policy_easing": {
            "favorable": ["GOLD", "SPX", "EURUSD", "AUDUSD", "US10Y"],
            "unfavorable": ["DXY", "US2Y"],
            "description": "Central bank cutting rates or signaling easing. Equities and "
                           "gold benefit from lower rate expectations.",
        },
        "liquidity_expansion": {
            "favorable": ["SPX", "NDX", "GOLD", "CRUDE_OIL", "AUDUSD", "EURUSD"],
            "unfavorable": ["DXY"],
            "description": "Fed balance sheet growing (QE). Abundant liquidity supports "
                           "nearly all risk assets.",
        },
        "liquidity_contraction": {
            "favorable": ["DXY", "US2Y"],
            "unfavorable": ["SPX", "GOLD", "NDX", "AUDUSD"],
            "description": "Fed balance sheet shrinking (QT). Liquidity withdrawal creates "
                           "headwinds for most assets.",
        },
        "stagflation": {
            "favorable": ["GOLD", "SILVER", "CRUDE_OIL", "USDCHF"],
            "unfavorable": ["SPX", "NDX", "US10Y", "AUDUSD"],
            "description": "Falling growth + rising inflation. Gold and commodities are "
                           "stagflation hedges. Equities and bonds both suffer.",
        },
        "recovery": {
            "favorable": ["SPX", "NDX", "EURUSD", "AUDUSD", "CRUDE_OIL"],
            "unfavorable": ["US10Y", "GOLD"],
            "description": "Early economic recovery. Equities and cyclicals lead. "
                           "Bonds sell off as growth expectations recover.",
        },
    }

    def classify(
        self,
        growth_score: float,         # 0-10 (momentum, trend)
        inflation_score: float,      # 0-10 (inflationary pressure)
        labor_score: float,          # 0-10 (labor market strength)
        monetary_score: float,       # 0-10 (0=dovish/easing, 10=hawkish/tightening)
        risk_score: float,           # 0-10 (0=risk-off, 10=risk-on)
        liquidity_score: float,      # 0-10 (0=contracting, 10=expanding)
        growth_trend: str = "neutral",    # "rising", "falling", "neutral"
        inflation_trend: str = "neutral", # "rising", "falling", "neutral"
    ) -> dict:
        """
        Classify macro regime from component scores.
        Returns dict with regime_type, confidence, scores, narrative.
        """
        scores = {}

        # Score each regime based on indicator alignment
        # Each regime has ideal conditions; we score proximity to those conditions

        # Risk-On Expansion: growth rising, inflation moderate, risk-on
        scores["risk_on_expansion"] = self._score_regime(
            conditions=[
                (growth_score, 7, 2.0),        # High growth
                (inflation_score, 4, 1.5),      # Moderate inflation
                (risk_score, 8, 2.0),           # Risk-on
                (1 - monetary_score / 10, 0.3, 1.0),  # Not extreme tightening
            ]
        )

        # Risk-Off Fear: low risk, high volatility implied
        scores["risk_off_fear"] = self._score_regime(
            conditions=[
                (risk_score, 2, 2.5),           # Risk-off dominant
                (growth_score, 3, 1.5),          # Weak growth
                (monetary_score, 3, 0.5),        # Easing or neutral
            ]
        )

        # Inflationary Boom: high growth + high inflation
        scores["inflationary_boom"] = self._score_regime(
            conditions=[
                (growth_score, 8, 2.0),
                (inflation_score, 8, 2.5),
                (risk_score, 7, 1.0),
            ]
        )

        # Deflationary Slowdown: low growth + low inflation
        scores["deflationary_slowdown"] = self._score_regime(
            conditions=[
                (growth_score, 2, 2.0),
                (inflation_score, 2, 2.5),
                (risk_score, 3, 1.0),
            ]
        )

        # Policy Tightening: high monetary score (hawkish)
        scores["policy_tightening"] = self._score_regime(
            conditions=[
                (monetary_score, 8, 3.0),       # Dominant hawkish signal
                (inflation_score, 7, 1.5),
                (growth_score, 5, 0.5),
            ]
        )

        # Policy Easing: low monetary score (dovish)
        scores["policy_easing"] = self._score_regime(
            conditions=[
                (monetary_score, 2, 3.0),       # Dominant dovish signal
                (growth_score, 3, 1.5),
            ]
        )

        # Liquidity Expansion: Fed expanding balance sheet
        scores["liquidity_expansion"] = self._score_regime(
            conditions=[
                (liquidity_score, 9, 3.0),
                (risk_score, 7, 1.0),
            ]
        )

        # Liquidity Contraction: Fed shrinking balance sheet
        scores["liquidity_contraction"] = self._score_regime(
            conditions=[
                (liquidity_score, 1, 3.0),
                (monetary_score, 7, 1.5),
            ]
        )

        # Stagflation: low growth + high inflation
        scores["stagflation"] = self._score_regime(
            conditions=[
                (growth_score, 2, 2.0),
                (inflation_score, 8, 2.5),
                (risk_score, 3, 1.0),
            ]
        )

        # Recovery: growth improving from low base, inflation low
        scores["recovery"] = self._score_regime(
            conditions=[
                (growth_score, 6, 1.5),         # Improving but not peak
                (inflation_score, 3, 1.5),        # Inflation still low
                (risk_score, 6, 1.0),             # Risk appetite returning
                (labor_score, 5, 0.5),            # Labor recovering
            ]
        )

        # Apply trend overrides
        if growth_trend == "rising" and inflation_trend == "rising":
            scores["inflationary_boom"] *= 1.3
        elif growth_trend == "rising" and inflation_trend == "falling":
            scores["risk_on_expansion"] *= 1.3
        elif growth_trend == "falling" and inflation_trend == "rising":
            scores["stagflation"] *= 1.3
        elif growth_trend == "falling" and inflation_trend == "falling":
            scores["deflationary_slowdown"] *= 1.3

        # Strong monetary signal overrides
        if monetary_score >= 8:
            scores["policy_tightening"] *= 1.4
        elif monetary_score <= 2:
            scores["policy_easing"] *= 1.4

        # Normalize scores to probabilities
        total = sum(scores.values())
        if total > 0:
            probs = {k: v / total for k, v in scores.items()}
        else:
            probs = {k: 1 / len(scores) for k in scores}

        # Top regime
        regime_type = max(probs, key=probs.get)
        confidence = probs[regime_type]

        # Composite macro score (-10 to +10)
        macro_composite = (
            (growth_score - 5) * 0.3 +
            (5 - inflation_score) * 0.15 +
            (labor_score - 5) * 0.15 +
            (risk_score - 5) * 0.25 +
            (liquidity_score - 5) * 0.15
        ) * 2

        # Simple recession probability
        recession_prob = self._estimate_recession_probability(
            growth_score, labor_score, monetary_score, inflation_score
        )

        # Determine growth and inflation phase
        growth_phase = self._classify_growth_phase(growth_score, growth_trend)
        inflation_phase = self._classify_inflation_phase(inflation_score, inflation_trend)

        asset_context = self.REGIME_ASSET_MAP.get(regime_type, {})

        return {
            "regime_type": regime_type,
            "regime_label": self.REGIME_LABELS.get(regime_type, regime_type),
            "regime_confidence": round(confidence, 3),
            "scores": {
                "growth": round(growth_score, 2),
                "inflation": round(inflation_score, 2),
                "labor": round(labor_score, 2),
                "monetary": round(monetary_score, 2),
                "risk": round(risk_score, 2),
                "liquidity": round(liquidity_score, 2),
            },
            "probabilities": {k: round(v, 3) for k, v in probs.items()},
            "macro_composite_score": round(macro_composite, 2),
            "recession_probability": round(recession_prob, 3),
            "growth_phase": growth_phase,
            "inflation_phase": inflation_phase,
            "favorable_assets": asset_context.get("favorable", []),
            "unfavorable_assets": asset_context.get("unfavorable", []),
            "description": asset_context.get("description", ""),
        }

    def _score_regime(self, conditions: list[tuple]) -> float:
        """
        Score a regime based on how close current conditions are to ideal.
        Each condition: (actual_score, ideal_score, weight)
        Returns 0-10 regime fit score.
        """
        if not conditions:
            return 0.0
        total_weight = sum(w for _, _, w in conditions)
        weighted_score = sum(
            w * (1 - abs(actual - ideal) / 10)
            for actual, ideal, w in conditions
        )
        return weighted_score / total_weight * 10

    def _estimate_recession_probability(
        self,
        growth: float,
        labor: float,
        monetary: float,
        inflation: float,
    ) -> float:
        """
        Simple recession probability estimator.
        Based on classic indicators: yield curve inversion, growth deceleration,
        labor deterioration, tight monetary policy.
        """
        # Low growth + weak labor + tight money → high recession risk
        recession_score = (
            (5 - growth) / 5 * 0.40 +       # Growth below midpoint
            (5 - labor) / 5 * 0.30 +         # Labor weakness
            (monetary - 5) / 5 * 0.20 +      # Tight monetary policy
            (inflation - 5) / 5 * 0.10       # High inflation as a stressor
        )
        return max(0.0, min(1.0, recession_score))

    def _classify_growth_phase(self, growth_score: float, trend: str) -> str:
        if trend == "rising" and growth_score >= 6:
            return "expansion"
        elif trend == "falling" and growth_score >= 6:
            return "peak"
        elif trend == "falling" and growth_score < 5:
            return "contraction"
        elif trend == "rising" and growth_score < 5:
            return "trough"
        return "expansion" if growth_score >= 5 else "contraction"

    def _classify_inflation_phase(self, inflation_score: float, trend: str) -> str:
        if trend == "rising":
            return "rising"
        elif trend == "falling" and inflation_score >= 7:
            return "high_stable"
        elif trend == "falling":
            return "falling"
        return "low_stable" if inflation_score < 5 else "high_stable"

    def generate_regime_narrative(self, regime_result: dict) -> str:
        """Generate plain-language narrative for Trader Summary panel."""
        regime_label = regime_result["regime_label"]
        scores = regime_result["scores"]
        favorable = regime_result["favorable_assets"]
        unfavorable = regime_result["unfavorable_assets"]
        confidence_pct = int(regime_result["regime_confidence"] * 100)
        recession_pct = int(regime_result["recession_probability"] * 100)
        description = regime_result.get("description", "")

        favorable_str = ", ".join(favorable[:4]) if favorable else "None"
        unfavorable_str = ", ".join(unfavorable[:4]) if unfavorable else "None"

        narrative = (
            f"The current macro environment is classified as **{regime_label}** "
            f"with {confidence_pct}% confidence. {description}\n\n"
            f"**Growth Score:** {scores['growth']:.1f}/10 | "
            f"**Inflation Score:** {scores['inflation']:.1f}/10 | "
            f"**Risk Appetite:** {scores['risk']:.1f}/10\n\n"
            f"**Assets likely to outperform:** {favorable_str}\n"
            f"**Assets likely to underperform:** {unfavorable_str}\n\n"
            f"Recession probability estimate: {recession_pct}%."
        )
        return narrative


regime_classifier = RegimeClassifier()
