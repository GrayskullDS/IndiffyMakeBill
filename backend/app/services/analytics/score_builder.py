"""
Score Builder: converts raw macro readings into normalized 0-10 scores
for use by the Regime Classifier and Bias Engine.
"""
import logging
from typing import Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class ScoreBuilder:
    """
    Converts raw indicator values into comparable 0-10 scores.
    Uses z-score normalization with lookback windows.
    """

    def build_growth_score(
        self,
        gdp_growth: Optional[float],        # YoY % (latest)
        pmi_manufacturing: Optional[float], # Index level
        industrial_production_yoy: Optional[float],
        retail_sales_yoy: Optional[float],
        leading_index_trend: Optional[float],  # 3m change in LEI
    ) -> float:
        """
        Composite growth score (0=recession, 10=booming).
        """
        components = []
        weights = []

        if gdp_growth is not None:
            # Map GDP growth: -5% to +5% → 0-10
            score = np.clip((gdp_growth + 5) / 10 * 10, 0, 10)
            components.append(score)
            weights.append(3.0)

        if pmi_manufacturing is not None:
            # PMI: 40=0, 50=5, 60=10
            score = np.clip((pmi_manufacturing - 40) / 20 * 10, 0, 10)
            components.append(score)
            weights.append(2.5)

        if industrial_production_yoy is not None:
            score = np.clip((industrial_production_yoy + 10) / 20 * 10, 0, 10)
            components.append(score)
            weights.append(2.0)

        if retail_sales_yoy is not None:
            score = np.clip((retail_sales_yoy + 5) / 15 * 10, 0, 10)
            components.append(score)
            weights.append(1.5)

        if leading_index_trend is not None:
            score = np.clip((leading_index_trend + 2) / 4 * 10, 0, 10)
            components.append(score)
            weights.append(1.0)

        if not components:
            return 5.0

        return float(np.average(components, weights=weights))

    def build_inflation_score(
        self,
        cpi_yoy: Optional[float],
        core_cpi_yoy: Optional[float],
        ppi_yoy: Optional[float],
        breakeven_5y: Optional[float],
    ) -> float:
        """
        Composite inflation pressure score (0=deflation, 10=hyper).
        """
        components = []
        weights = []

        if cpi_yoy is not None:
            # 0% to 8%+ → 0-10
            score = np.clip(cpi_yoy / 8 * 10, 0, 10)
            components.append(score)
            weights.append(3.0)

        if core_cpi_yoy is not None:
            score = np.clip(core_cpi_yoy / 6 * 10, 0, 10)
            components.append(score)
            weights.append(2.5)

        if ppi_yoy is not None:
            score = np.clip(ppi_yoy / 10 * 10, 0, 10)
            components.append(score)
            weights.append(1.5)

        if breakeven_5y is not None:
            # 5Y breakeven: 0% to 4% → 0-10
            score = np.clip(breakeven_5y / 4 * 10, 0, 10)
            components.append(score)
            weights.append(2.0)

        if not components:
            return 5.0

        return float(np.average(components, weights=weights))

    def build_labor_score(
        self,
        unemployment_rate: Optional[float],
        nonfarm_payrolls_mom: Optional[float],    # Thousands
        wage_growth_yoy: Optional[float],
        jobless_claims: Optional[float],           # Weekly, thousands
    ) -> float:
        """
        Labor market strength score (0=severe weakness, 10=very tight).
        """
        components = []
        weights = []

        if unemployment_rate is not None:
            # 10% = 0, 3.5% = 10
            score = np.clip((10 - unemployment_rate) / 6.5 * 10, 0, 10)
            components.append(score)
            weights.append(3.0)

        if nonfarm_payrolls_mom is not None:
            # -500K to +500K → 0-10
            score = np.clip((nonfarm_payrolls_mom + 500) / 1000 * 10, 0, 10)
            components.append(score)
            weights.append(2.5)

        if wage_growth_yoy is not None:
            # 0% to 6% → 0-10 (higher wages = tighter labor)
            score = np.clip(wage_growth_yoy / 6 * 10, 0, 10)
            components.append(score)
            weights.append(2.0)

        if jobless_claims is not None:
            # 800K = 0, 200K = 10
            score = np.clip((800 - jobless_claims) / 600 * 10, 0, 10)
            components.append(score)
            weights.append(1.5)

        if not components:
            return 5.0

        return float(np.average(components, weights=weights))

    def build_monetary_score(
        self,
        fed_funds_rate: Optional[float],
        yield_curve_10y2y: Optional[float],  # In %
        real_rate_10y: Optional[float],
        fed_bs_change_yoy: Optional[float],  # YoY % change in Fed BS
    ) -> float:
        """
        Monetary policy hawkishness score.
        0 = extremely dovish (ZIRP/QE)
        10 = extremely hawkish (high rates/QT)
        """
        components = []
        weights = []

        if fed_funds_rate is not None:
            # 0% to 7%+ → 0-10
            score = np.clip(fed_funds_rate / 7 * 10, 0, 10)
            components.append(score)
            weights.append(3.0)

        if yield_curve_10y2y is not None:
            # Inverted curve (-1%) = hawkish tightening → high score
            # Steep curve (+2.5%) = easing/early cycle → lower score
            score = np.clip((1 - yield_curve_10y2y) / 2.5 * 10, 0, 10)
            components.append(score)
            weights.append(2.0)

        if real_rate_10y is not None:
            # Real rate: -2% to +3% → 0-10
            score = np.clip((real_rate_10y + 2) / 5 * 10, 0, 10)
            components.append(score)
            weights.append(2.5)

        if fed_bs_change_yoy is not None:
            # Negative change (QT) = hawkish = high score
            score = np.clip((-fed_bs_change_yoy + 20) / 40 * 10, 0, 10)
            components.append(score)
            weights.append(2.0)

        if not components:
            return 5.0

        return float(np.average(components, weights=weights))

    def build_risk_score(
        self,
        vix: Optional[float],
        hy_credit_spread: Optional[float],  # % basis points
        financial_conditions_index: Optional[float],  # NFCI (negative = loose)
        equity_trend: Optional[str],         # "uptrend", "downtrend", "sideways"
    ) -> float:
        """
        Risk appetite score.
        0 = extreme risk-off / fear
        10 = extreme risk-on / greed
        """
        components = []
        weights = []

        if vix is not None:
            # VIX 10=10, VIX 20=5, VIX 40+=0
            score = np.clip((40 - vix) / 30 * 10, 0, 10)
            components.append(score)
            weights.append(3.0)

        if hy_credit_spread is not None:
            # Tight spread (2%) = 10, wide spread (10%) = 0
            score = np.clip((10 - hy_credit_spread) / 8 * 10, 0, 10)
            components.append(score)
            weights.append(2.5)

        if financial_conditions_index is not None:
            # NFCI: more negative = looser = more risk-on
            score = np.clip((-financial_conditions_index + 2) / 4 * 10, 0, 10)
            components.append(score)
            weights.append(2.0)

        if equity_trend is not None:
            trend_scores = {"uptrend": 8.0, "sideways": 5.0, "downtrend": 2.0}
            components.append(trend_scores.get(equity_trend, 5.0))
            weights.append(2.0)

        if not components:
            return 5.0

        return float(np.average(components, weights=weights))

    def build_liquidity_score(
        self,
        fed_balance_sheet_yoy: Optional[float],   # YoY % change
        m2_growth_yoy: Optional[float],
        repo_rate_vs_fed_funds: Optional[float],   # Spread
    ) -> float:
        """
        Liquidity conditions score.
        0 = extreme tightening (QT)
        10 = extreme expansion (QE)
        """
        components = []
        weights = []

        if fed_balance_sheet_yoy is not None:
            # -20% (QT) to +40% (peak QE) → 0-10
            score = np.clip((fed_balance_sheet_yoy + 20) / 60 * 10, 0, 10)
            components.append(score)
            weights.append(3.0)

        if m2_growth_yoy is not None:
            # -5% to 25% → 0-10
            score = np.clip((m2_growth_yoy + 5) / 30 * 10, 0, 10)
            components.append(score)
            weights.append(2.0)

        if repo_rate_vs_fed_funds is not None:
            score = np.clip((1 - repo_rate_vs_fed_funds) / 2 * 10, 0, 10)
            components.append(score)
            weights.append(1.0)

        if not components:
            return 5.0

        return float(np.average(components, weights=weights))

    def compute_z_score(self, series: pd.Series, lookback: int = 36) -> float:
        """Compute z-score of the latest value against a rolling window."""
        if len(series) < lookback:
            return 0.0
        recent = series.tail(lookback)
        mean = recent.mean()
        std = recent.std()
        if std == 0:
            return 0.0
        return float((series.iloc[-1] - mean) / std)

    def compute_momentum(self, series: pd.Series, periods: int = 3) -> float:
        """
        Compute momentum as direction of change over N periods.
        Returns: 'rising', 'falling', or 'neutral'
        """
        if len(series) < periods + 1:
            return "neutral"
        change = series.iloc[-1] - series.iloc[-periods]
        std = series.tail(12).std()
        if std == 0:
            return "neutral"
        if change > 0.5 * std:
            return "rising"
        if change < -0.5 * std:
            return "falling"
        return "neutral"
