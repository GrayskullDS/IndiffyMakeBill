"""
Seasonality calculator.
Computes historical monthly return statistics per asset.
"""
import logging
from typing import Optional
import pandas as pd
import numpy as np
from calendar import month_abbr

logger = logging.getLogger(__name__)

MONTH_NAMES = {i: month_abbr[i] for i in range(1, 13)}


class SeasonalityCalculator:
    """Compute historical monthly seasonality patterns."""

    def compute_monthly_stats(
        self,
        price_df: pd.DataFrame,
        lookback_years: int = 10,
    ) -> dict:
        """
        Compute monthly return statistics from price history.
        Returns dict with stats per month (1-12).
        """
        if price_df.empty or "close" not in price_df.columns:
            return {}

        df = price_df.copy()
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        # Limit to lookback period
        cutoff = df.index.max() - pd.DateOffset(years=lookback_years)
        df = df[df.index >= cutoff]

        # Compute monthly returns
        monthly = df["close"].resample("ME").last()
        returns = monthly.pct_change() * 100

        stats_by_month = {}
        for month in range(1, 13):
            month_returns = returns[returns.index.month == month].dropna()
            if len(month_returns) < 2:
                stats_by_month[month] = self._empty_stats(month)
                continue

            stats_by_month[month] = {
                "month": month,
                "month_name": MONTH_NAMES[month],
                "avg_return": round(float(month_returns.mean()), 3),
                "median_return": round(float(month_returns.median()), 3),
                "win_rate": round(float((month_returns > 0).mean() * 100), 1),
                "std_dev": round(float(month_returns.std()), 3),
                "best_return": round(float(month_returns.max()), 3),
                "worst_return": round(float(month_returns.min()), 3),
                "sample_size": len(month_returns),
            }

        return stats_by_month

    def get_current_month_score(
        self,
        stats_by_month: dict,
        current_month: Optional[int] = None,
    ) -> float:
        """
        Get a 0-10 seasonality score for the current month.
        Based on average return and win rate.
        """
        if not stats_by_month:
            return 5.0

        from datetime import date
        month = current_month or date.today().month
        stats = stats_by_month.get(month, {})

        if not stats:
            return 5.0

        avg_ret = stats.get("avg_return", 0)
        win_rate = stats.get("win_rate", 50)

        # Normalize avg return: -3% to +3% → 0-10
        ret_score = np.clip((avg_ret + 3) / 6 * 10, 0, 10)
        # Win rate: 30% to 70% → 0-10
        wr_score = np.clip((win_rate - 30) / 40 * 10, 0, 10)

        return round(float(0.6 * ret_score + 0.4 * wr_score), 2)

    def get_seasonal_edge_label(self, score: float) -> str:
        """Convert seasonality score to a label."""
        if score >= 7.5:
            return "Strong Seasonal Tailwind"
        if score >= 6.0:
            return "Moderate Seasonal Tailwind"
        if score >= 4.5:
            return "Neutral Seasonality"
        if score >= 3.0:
            return "Moderate Seasonal Headwind"
        return "Strong Seasonal Headwind"

    def compute_multi_lookback(
        self,
        price_df: pd.DataFrame,
        lookback_years_list: list[int] = [5, 10, 20],
    ) -> dict:
        """Compute seasonality for multiple lookback periods."""
        result = {}
        for years in lookback_years_list:
            result[years] = self.compute_monthly_stats(price_df, lookback_years=years)
        return result

    def _empty_stats(self, month: int) -> dict:
        return {
            "month": month,
            "month_name": MONTH_NAMES[month],
            "avg_return": 0.0,
            "median_return": 0.0,
            "win_rate": 50.0,
            "std_dev": 0.0,
            "best_return": 0.0,
            "worst_return": 0.0,
            "sample_size": 0,
        }


seasonality_calc = SeasonalityCalculator()
