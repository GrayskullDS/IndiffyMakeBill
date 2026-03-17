"""
Price data fetcher using yfinance.
Fetches OHLCV for forex, indices, commodities, bonds.
Also computes technical indicators on the fly.
"""
import logging
from datetime import date, timedelta
from typing import Optional
import pandas as pd
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Asset ticker map: symbol -> yfinance ticker
ASSET_TICKERS = {
    # Forex pairs
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "USDCHF": "USDCHF=X",
    "AUDUSD": "AUDUSD=X",
    "NZDUSD": "NZDUSD=X",
    "USDCAD": "USDCAD=X",
    "XAUUSD": "GC=F",         # Gold (spot proxy)
    # Equity Indices
    "SPX": "^GSPC",
    "NDX": "^NDX",
    "DJI": "^DJI",
    "DAX": "^GDAXI",
    "FTSE": "^FTSE",
    "NIKKEI": "^N225",
    "HSI": "^HSI",
    # Commodities
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "CRUDE_OIL": "CL=F",
    "BRENT": "BZ=F",
    "NATURAL_GAS": "NG=F",
    "COPPER": "HG=F",
    # Bonds
    "US10Y": "^TNX",
    "US2Y": "^IRX",
    "US30Y": "^TYX",
    # Volatility
    "VIX": "^VIX",
    "MOVE": "^MOVE",         # Bond volatility
    # DXY proxy
    "DXY": "DX-Y.NYB",
}


class PriceFetcher:
    """Fetches OHLCV price data and computes technical indicators."""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_ohlcv(
        self,
        ticker: str,
        start_date: str = "2010-01-01",
        end_date: Optional[str] = None,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a single ticker.
        Returns DataFrame with columns: open, high, low, close, volume, adj_close.
        """
        import yfinance as yf
        end = end_date or date.today().isoformat()
        data = yf.download(
            ticker,
            start=start_date,
            end=end,
            interval=interval,
            auto_adjust=False,
            progress=False,
        )
        if data.empty:
            logger.warning(f"No data returned for ticker {ticker}")
            return pd.DataFrame()

        # Flatten multi-level columns if present
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0].lower() for col in data.columns]
        else:
            data.columns = [c.lower().replace(" ", "_") for c in data.columns]

        data.index = pd.to_datetime(data.index).date
        data = data.dropna(subset=["close"])
        return data

    def fetch_multiple(
        self,
        symbols: list[str],
        start_date: str = "2010-01-01",
    ) -> dict[str, pd.DataFrame]:
        """Fetch OHLCV for multiple assets."""
        results = {}
        for symbol in symbols:
            ticker = ASSET_TICKERS.get(symbol, symbol)
            try:
                df = self.fetch_ohlcv(ticker, start_date=start_date)
                if not df.empty:
                    results[symbol] = self.add_technical_indicators(df)
                    logger.info(f"Fetched {symbol} ({ticker}): {len(df)} bars")
            except Exception as e:
                logger.error(f"Failed to fetch {symbol}: {e}")
        return results

    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add SMA, EMA, RSI, ATR to a price DataFrame."""
        close = df["close"].copy()

        # Simple Moving Averages
        df["sma_20"] = close.rolling(20).mean()
        df["sma_50"] = close.rolling(50).mean()
        df["sma_200"] = close.rolling(200).mean()

        # EMA
        df["ema_20"] = close.ewm(span=20, adjust=False).mean()

        # RSI
        df["rsi_14"] = self._compute_rsi(close, 14)

        # ATR
        if all(c in df.columns for c in ["high", "low", "close"]):
            df["atr_14"] = self._compute_atr(df, 14)

        return df

    @staticmethod
    def _compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high = df["high"]
        low = df["low"]
        close = df["close"]
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        return tr.ewm(com=period - 1, min_periods=period).mean()

    def compute_returns(self, df: pd.DataFrame, periods: list[int] = [1, 5, 21, 63, 126, 252]) -> pd.DataFrame:
        """Add return columns for multiple horizons."""
        close = df["close"]
        for p in periods:
            df[f"return_{p}d"] = close.pct_change(p) * 100
        return df

    def get_trend_direction(self, df: pd.DataFrame) -> str:
        """
        Simple multi-timeframe trend detection.
        Returns: 'uptrend', 'downtrend', or 'sideways'
        """
        if df.empty or len(df) < 200:
            return "sideways"
        close = df["close"].iloc[-1]
        sma50 = df["sma_50"].iloc[-1] if "sma_50" in df.columns else None
        sma200 = df["sma_200"].iloc[-1] if "sma_200" in df.columns else None

        if sma50 and sma200:
            if close > sma50 > sma200:
                return "uptrend"
            if close < sma50 < sma200:
                return "downtrend"
        return "sideways"

    def compute_correlation_matrix(
        self,
        price_data: dict[str, pd.DataFrame],
        lookback_days: int = 63,
    ) -> pd.DataFrame:
        """Compute correlation matrix across assets."""
        returns = {}
        for symbol, df in price_data.items():
            if not df.empty and "close" in df.columns:
                r = df["close"].pct_change().tail(lookback_days)
                returns[symbol] = r

        if not returns:
            return pd.DataFrame()

        return pd.DataFrame(returns).corr()

    def compute_relative_strength(
        self,
        price_data: dict[str, pd.DataFrame],
        benchmark: str = "SPX",
        period: int = 63,
    ) -> dict[str, float]:
        """Compute relative strength vs benchmark over given period."""
        if benchmark not in price_data:
            return {}

        bench_df = price_data[benchmark]
        bench_return = (
            bench_df["close"].iloc[-1] / bench_df["close"].iloc[-min(period, len(bench_df))] - 1
        ) * 100

        result = {}
        for symbol, df in price_data.items():
            if df.empty or "close" not in df.columns:
                continue
            asset_return = (
                df["close"].iloc[-1] / df["close"].iloc[-min(period, len(df))] - 1
            ) * 100
            result[symbol] = round(asset_return - bench_return, 2)

        return result


price_fetcher = PriceFetcher()
