"""
CFTC Commitment of Traders (COT) data fetcher.
Downloads and parses weekly COT reports for positioning analysis.
"""
import logging
from datetime import date
from typing import Optional
import pandas as pd
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# COT market name -> asset symbol mapping
COT_MARKET_MAP = {
    # Forex
    "EURO FX": "EURUSD",
    "BRITISH POUND STERLING": "GBPUSD",
    "JAPANESE YEN": "USDJPY",
    "SWISS FRANC": "USDCHF",
    "AUSTRALIAN DOLLAR": "AUDUSD",
    "NEW ZEALAND DOLLAR": "NZDUSD",
    "CANADIAN DOLLAR": "USDCAD",
    # Commodities
    "GOLD - COMMODITY EXCHANGE INC.": "GOLD",
    "CRUDE OIL, LIGHT SWEET": "CRUDE_OIL",
    "SILVER - COMMODITY EXCHANGE INC.": "SILVER",
    "NATURAL GAS - NEW YORK MERCANTILE": "NATURAL_GAS",
    "COPPER- #1": "COPPER",
    # Indices
    "S&P 500 STOCK INDEX": "SPX",
    "NASDAQ-100 STOCK INDEX (MINI)": "NDX",
    "DOW JONES INDUS. AVG. (DJIA) X $5": "DJI",
    # Bonds
    "10-YEAR U.S. TREASURY NOTES": "US10Y",
    "2-YEAR U.S. TREASURY NOTES (CBT)": "US2Y",
    "30-YEAR U.S. TREASURY BONDS (CBT)": "US30Y",
    "CBOE VOLATILITY INDEX (VIX)": "VIX",
}

# Columns to extract from COT legacy futures report
COT_COLUMNS = {
    "Market_and_Exchange_Names": "market_name",
    "As_of_Date_In_Form_YYMMDD": "report_date",
    "Open_Interest_All": "open_interest",
    "NonComm_Positions_Long_All": "noncommercial_long",
    "NonComm_Positions_Short_All": "noncommercial_short",
    "Comm_Positions_Long_All": "commercial_long",
    "Comm_Positions_Short_All": "commercial_short",
    "NonRept_Positions_Long_All": "nonreportable_long",
    "NonRept_Positions_Short_All": "nonreportable_short",
}


class COTFetcher:
    """Downloads and processes CFTC COT data."""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
    def fetch_cot_year(self, year: int) -> pd.DataFrame:
        """Fetch legacy futures COT data for a single year."""
        try:
            import cot_reports as cot
            df = cot.cot_year(year=year, cot_report_type="legacy_fut")
            return df
        except Exception as e:
            logger.error(f"Failed to fetch COT year {year}: {e}")
            raise

    def fetch_historical_cot(
        self,
        start_year: int = 2010,
        end_year: Optional[int] = None,
    ) -> pd.DataFrame:
        """Fetch COT data for a range of years."""
        end_year = end_year or date.today().year
        frames = []
        for year in range(start_year, end_year + 1):
            try:
                df = self.fetch_cot_year(year)
                frames.append(df)
                logger.info(f"Fetched COT {year}: {len(df)} records")
            except Exception as e:
                logger.warning(f"Skipping COT year {year}: {e}")
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

    def process_cot_data(self, raw_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
        """
        Process raw COT data into per-asset DataFrames with derived metrics.
        Returns dict of {asset_symbol: processed_df}.
        """
        # Rename columns
        available_cols = {k: v for k, v in COT_COLUMNS.items() if k in raw_df.columns}
        df = raw_df[list(available_cols.keys())].rename(columns=available_cols).copy()

        # Parse date
        df["report_date"] = pd.to_datetime(
            df["report_date"].astype(str), format="%y%m%d", errors="coerce"
        )
        df = df.dropna(subset=["report_date"])
        df["report_date"] = df["report_date"].dt.date

        results = {}
        for market_name, asset_symbol in COT_MARKET_MAP.items():
            mask = df["market_name"].str.upper().str.contains(
                market_name[:20].upper(), na=False
            )
            asset_df = df[mask].copy().sort_values("report_date").reset_index(drop=True)

            if asset_df.empty:
                continue

            # Compute net positions
            asset_df["noncommercial_net"] = (
                asset_df["noncommercial_long"] - asset_df["noncommercial_short"]
            )
            asset_df["commercial_net"] = (
                asset_df["commercial_long"] - asset_df["commercial_short"]
            )
            asset_df["nonreportable_net"] = (
                asset_df["nonreportable_long"] - asset_df["nonreportable_short"]
            )

            # Normalize net positions to -100 / +100 index using 3-year rolling window
            asset_df = self._compute_positioning_index(asset_df)

            results[asset_symbol] = asset_df

        return results

    def _compute_positioning_index(
        self, df: pd.DataFrame, window: int = 156
    ) -> pd.DataFrame:
        """
        Compute normalized positioning index for non-commercial net.
        Index: -100 (max short extreme) to +100 (max long extreme).
        Also flags 90th/10th percentile extremes.
        """
        net = df["noncommercial_net"]
        rolling_min = net.rolling(window, min_periods=52).min()
        rolling_max = net.rolling(window, min_periods=52).max()

        rng = rolling_max - rolling_min
        rng = rng.replace(0, np.nan)

        df["net_position_index"] = ((net - rolling_min) / rng * 200 - 100).round(2)

        # 52-week percentile for extremes flag
        rolling_52w_min = net.rolling(52, min_periods=26).min()
        rolling_52w_max = net.rolling(52, min_periods=26).max()
        rng_52 = rolling_52w_max - rolling_52w_min
        rng_52 = rng_52.replace(0, np.nan)
        df["percentile_52w"] = ((net - rolling_52w_min) / rng_52 * 100).round(2)
        df["positioning_extreme"] = (df["percentile_52w"] >= 90) | (df["percentile_52w"] <= 10)

        return df

    def get_latest_cot(self) -> dict[str, dict]:
        """
        Get the most recent COT reading for each tracked asset.
        Returns dict of {asset_symbol: {field: value}}.
        """
        current_year = date.today().year
        frames = []
        for year in [current_year - 1, current_year]:
            try:
                df = self.fetch_cot_year(year)
                frames.append(df)
            except Exception:
                pass

        if not frames:
            return {}

        combined = pd.concat(frames, ignore_index=True)
        processed = self.process_cot_data(combined)

        latest = {}
        for symbol, df in processed.items():
            if df.empty:
                continue
            row = df.iloc[-1].to_dict()
            latest[symbol] = {
                "report_date": row.get("report_date"),
                "noncommercial_net": row.get("noncommercial_net"),
                "net_position_index": row.get("net_position_index"),
                "percentile_52w": row.get("percentile_52w"),
                "positioning_extreme": bool(row.get("positioning_extreme", False)),
                "open_interest": row.get("open_interest"),
            }

        return latest

    def get_cot_signal(self, symbol: str, df: pd.DataFrame) -> float:
        """
        Convert COT positioning to a 0-10 bias score.
        High non-commercial long → 10 (bullish smart money)
        High non-commercial short → 0 (bearish smart money)
        """
        if df.empty or "net_position_index" not in df.columns:
            return 5.0  # Neutral default

        idx = df["net_position_index"].iloc[-1]
        # net_position_index is -100 to +100, normalize to 0-10
        score = (idx + 100) / 200 * 10
        return round(max(0, min(10, score)), 2)


cot_fetcher = COTFetcher()
