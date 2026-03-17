"""
FRED (Federal Reserve Economic Data) fetcher.
Pulls macro indicators: GDP, CPI, unemployment, rates, yield curve, etc.
"""
import logging
from datetime import date, datetime
from typing import Optional
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings

logger = logging.getLogger(__name__)

# Core FRED series for the platform
FRED_SERIES = {
    # Growth
    "GDP_REAL_QOQ": {
        "series_id": "A191RA1Q225SBEA",
        "name": "Real GDP Growth (QoQ %)",
        "category": "growth",
        "frequency": "quarterly",
        "unit": "percent",
    },
    "PMI_MANUFACTURING": {
        "series_id": "MANEMP",
        "name": "ISM Manufacturing PMI",
        "category": "growth",
        "frequency": "monthly",
        "unit": "index",
    },
    "INDUSTRIAL_PRODUCTION": {
        "series_id": "INDPRO",
        "name": "Industrial Production Index",
        "category": "growth",
        "frequency": "monthly",
        "unit": "index",
    },
    "RETAIL_SALES": {
        "series_id": "RSAFS",
        "name": "Retail Sales (Millions)",
        "category": "growth",
        "frequency": "monthly",
        "unit": "millions_usd",
    },
    "LEADING_INDEX": {
        "series_id": "USSLIND",
        "name": "Leading Economic Index",
        "category": "growth",
        "frequency": "monthly",
        "unit": "index",
    },

    # Inflation
    "CPI_YOY": {
        "series_id": "CPIAUCSL",
        "name": "CPI All Urban Consumers",
        "category": "inflation",
        "frequency": "monthly",
        "unit": "index",
    },
    "CORE_CPI_YOY": {
        "series_id": "CPILFESL",
        "name": "Core CPI (ex Food & Energy)",
        "category": "inflation",
        "frequency": "monthly",
        "unit": "index",
    },
    "PPI": {
        "series_id": "PPIACO",
        "name": "Producer Price Index",
        "category": "inflation",
        "frequency": "monthly",
        "unit": "index",
    },
    "INFLATION_EXPECTATIONS_5Y": {
        "series_id": "T5YIE",
        "name": "5-Year Breakeven Inflation Rate",
        "category": "inflation",
        "frequency": "daily",
        "unit": "percent",
    },
    "INFLATION_EXPECTATIONS_10Y": {
        "series_id": "T10YIE",
        "name": "10-Year Breakeven Inflation Rate",
        "category": "inflation",
        "frequency": "daily",
        "unit": "percent",
    },

    # Labor
    "UNEMPLOYMENT_RATE": {
        "series_id": "UNRATE",
        "name": "Unemployment Rate",
        "category": "labor",
        "frequency": "monthly",
        "unit": "percent",
    },
    "NONFARM_PAYROLLS": {
        "series_id": "PAYEMS",
        "name": "Nonfarm Payrolls",
        "category": "labor",
        "frequency": "monthly",
        "unit": "thousands",
    },
    "INITIAL_JOBLESS_CLAIMS": {
        "series_id": "ICSA",
        "name": "Initial Jobless Claims",
        "category": "labor",
        "frequency": "weekly",
        "unit": "number",
    },
    "WAGE_GROWTH": {
        "series_id": "CES0500000003",
        "name": "Average Hourly Earnings",
        "category": "labor",
        "frequency": "monthly",
        "unit": "dollars",
    },
    "PARTICIPATION_RATE": {
        "series_id": "CIVPART",
        "name": "Labor Force Participation Rate",
        "category": "labor",
        "frequency": "monthly",
        "unit": "percent",
    },

    # Monetary Policy
    "FED_FUNDS_RATE": {
        "series_id": "FEDFUNDS",
        "name": "Federal Funds Rate",
        "category": "monetary",
        "frequency": "monthly",
        "unit": "percent",
    },
    "YIELD_2Y": {
        "series_id": "DGS2",
        "name": "2-Year Treasury Yield",
        "category": "monetary",
        "frequency": "daily",
        "unit": "percent",
    },
    "YIELD_10Y": {
        "series_id": "DGS10",
        "name": "10-Year Treasury Yield",
        "category": "monetary",
        "frequency": "daily",
        "unit": "percent",
    },
    "YIELD_30Y": {
        "series_id": "DGS30",
        "name": "30-Year Treasury Yield",
        "category": "monetary",
        "frequency": "daily",
        "unit": "percent",
    },
    "YIELD_CURVE_10Y2Y": {
        "series_id": "T10Y2Y",
        "name": "10Y-2Y Treasury Spread (Yield Curve)",
        "category": "monetary",
        "frequency": "daily",
        "unit": "percent",
    },
    "FED_BALANCE_SHEET": {
        "series_id": "WALCL",
        "name": "Fed Balance Sheet Total Assets",
        "category": "monetary",
        "frequency": "weekly",
        "unit": "millions_usd",
    },
    "REAL_RATE_10Y": {
        "series_id": "DFII10",
        "name": "10-Year Real Treasury Yield (TIPS)",
        "category": "monetary",
        "frequency": "daily",
        "unit": "percent",
    },

    # Sentiment / Financial Conditions
    "VIX": {
        "series_id": "VIXCLS",
        "name": "CBOE VIX Volatility Index",
        "category": "sentiment",
        "frequency": "daily",
        "unit": "index",
    },
    "FINANCIAL_CONDITIONS": {
        "series_id": "NFCI",
        "name": "Chicago Fed National Financial Conditions Index",
        "category": "sentiment",
        "frequency": "weekly",
        "unit": "index",
    },
    "CREDIT_SPREAD_HY": {
        "series_id": "BAMLH0A0HYM2",
        "name": "ICE BofA US High Yield Spread",
        "category": "sentiment",
        "frequency": "daily",
        "unit": "percent",
    },
    "CREDIT_SPREAD_IG": {
        "series_id": "BAMLC0A0CM",
        "name": "ICE BofA US Corporate Spread",
        "category": "sentiment",
        "frequency": "daily",
        "unit": "percent",
    },
    "DXY_INDEX": {
        "series_id": "DTWEXBGS",
        "name": "US Dollar Index (Broad)",
        "category": "price",
        "frequency": "daily",
        "unit": "index",
    },
}


class FREDFetcher:
    """Fetches macro data from FRED API using fredapi library."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.FRED_API_KEY
        self._fred = None

    def _get_client(self):
        if self._fred is None:
            try:
                from fredapi import Fred
                self._fred = Fred(api_key=self.api_key)
            except ImportError:
                raise ImportError("fredapi not installed. Run: pip install fredapi")
        return self._fred

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_series(
        self,
        series_id: str,
        start_date: Optional[str] = "2000-01-01",
        end_date: Optional[str] = None,
    ) -> pd.Series:
        """Fetch a single FRED series as a pandas Series."""
        client = self._get_client()
        kwargs = {"observation_start": start_date}
        if end_date:
            kwargs["observation_end"] = end_date
        data = client.get_series(series_id, **kwargs)
        data.name = series_id
        data.index = pd.to_datetime(data.index).date
        return data.dropna()

    def fetch_all_indicators(
        self,
        start_date: str = "2000-01-01",
    ) -> dict[str, pd.Series]:
        """
        Fetch all configured FRED series.
        Returns dict of {code: pd.Series}.
        """
        results = {}
        for code, meta in FRED_SERIES.items():
            try:
                series = self.fetch_series(meta["series_id"], start_date=start_date)
                results[code] = series
                logger.info(f"Fetched FRED {code}: {len(series)} readings")
            except Exception as e:
                logger.error(f"Failed to fetch FRED {code} ({meta['series_id']}): {e}")
        return results

    def compute_yoy_change(self, series: pd.Series) -> pd.Series:
        """Compute year-over-year percentage change for monthly/quarterly series."""
        s = series.copy()
        s.index = pd.to_datetime(s.index)
        return s.pct_change(12) * 100  # 12 months for monthly

    def get_latest_value(self, series_id: str) -> Optional[float]:
        """Get the most recent value for a series."""
        try:
            series = self.fetch_series(series_id)
            return float(series.iloc[-1]) if len(series) > 0 else None
        except Exception as e:
            logger.error(f"Error fetching latest value for {series_id}: {e}")
            return None


fred_fetcher = FREDFetcher()
