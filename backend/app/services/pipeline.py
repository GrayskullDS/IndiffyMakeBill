"""
Main data pipeline orchestrator.
Coordinates data fetching, processing, and storage for all data types.
"""
import logging
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.macro import MacroIndicator, MacroReading
from app.models.asset import Asset, AssetPrice, COTReading, BiasSignal, SeasonalityData
from app.models.regime import MacroRegime
from app.models.alert import Alert, AlertType, AlertSeverity
from app.services.data_fetchers.fred_fetcher import fred_fetcher, FRED_SERIES
from app.services.data_fetchers.price_fetcher import price_fetcher, ASSET_TICKERS
from app.services.data_fetchers.cot_fetcher import cot_fetcher
from app.services.analytics.regime_classifier import regime_classifier
from app.services.analytics.bias_engine import bias_engine
from app.services.analytics.score_builder import ScoreBuilder
from app.services.analytics.seasonality import seasonality_calc

logger = logging.getLogger(__name__)
score_builder = ScoreBuilder()


class MacroPipeline:
    """
    Orchestrates the full data pipeline:
    1. Fetch raw data (FRED, yfinance, CFTC)
    2. Clean and normalize
    3. Store to database
    4. Run analytics (regime, bias)
    5. Store results and generate alerts
    """

    async def run_full_pipeline(self, db: AsyncSession, backfill: bool = False) -> dict:
        """Run all pipeline stages."""
        start_date = "2010-01-01" if backfill else "2023-01-01"
        results = {}

        logger.info("Starting macro pipeline run...")

        # Stage 1: Macro indicators
        results["macro"] = await self.ingest_macro_indicators(db, start_date)

        # Stage 2: Prices
        results["prices"] = await self.ingest_prices(db, start_date)

        # Stage 3: COT
        results["cot"] = await self.ingest_cot(db)

        # Stage 4: Compute regime
        results["regime"] = await self.compute_and_store_regime(db)

        # Stage 5: Compute bias signals
        results["bias"] = await self.compute_and_store_bias(db)

        # Stage 6: Generate alerts
        results["alerts"] = await self.generate_alerts(db, results["regime"])

        logger.info(f"Pipeline complete: {results}")
        return results

    async def ingest_macro_indicators(self, db: AsyncSession, start_date: str = "2020-01-01") -> dict:
        """Fetch and store all FRED macro indicator series."""
        logger.info("Ingesting macro indicators from FRED...")
        stored = 0
        errors = 0

        for code, meta in FRED_SERIES.items():
            try:
                # Ensure indicator exists
                result = await db.execute(
                    select(MacroIndicator).where(MacroIndicator.code == code)
                )
                indicator = result.scalar_one_or_none()

                if not indicator:
                    indicator = MacroIndicator(
                        code=code,
                        name=meta["name"],
                        category=meta["category"],
                        frequency=meta["frequency"],
                        unit=meta.get("unit"),
                        source="FRED",
                        source_series_id=meta["series_id"],
                        country="US",
                    )
                    db.add(indicator)
                    await db.flush()

                # Fetch series data
                series = fred_fetcher.fetch_series(meta["series_id"], start_date=start_date)

                # Upsert readings
                for obs_date, value in series.items():
                    if value is None or (hasattr(value, '__class__') and
                                         value.__class__.__name__ == 'float' and
                                         value != value):  # NaN check
                        continue

                    stmt = pg_insert(MacroReading).values(
                        indicator_id=indicator.id,
                        date=obs_date,
                        value=float(value),
                    ).on_conflict_do_update(
                        constraint="uq_indicator_date",
                        set_={"value": float(value)}
                    )
                    await db.execute(stmt)
                    stored += 1

                await db.commit()
                logger.debug(f"Stored {len(series)} readings for {code}")

            except Exception as e:
                errors += 1
                logger.error(f"Failed to ingest {code}: {e}")
                await db.rollback()

        return {"stored": stored, "errors": errors}

    async def ingest_prices(self, db: AsyncSession, start_date: str = "2020-01-01") -> dict:
        """Fetch and store OHLCV price data for all tracked assets."""
        logger.info("Ingesting prices from yfinance...")
        stored = 0

        # Get or create asset records
        asset_map = {}
        for symbol, ticker in ASSET_TICKERS.items():
            result = await db.execute(select(Asset).where(Asset.symbol == symbol))
            asset = result.scalar_one_or_none()
            if not asset:
                asset = Asset(
                    symbol=symbol,
                    name=symbol,
                    asset_class=self._infer_asset_class(symbol),
                    yfinance_ticker=ticker,
                )
                db.add(asset)
                await db.flush()
            asset_map[symbol] = asset

        await db.commit()

        # Fetch price data
        price_data = price_fetcher.fetch_multiple(
            list(ASSET_TICKERS.keys()),
            start_date=start_date,
        )

        for symbol, df in price_data.items():
            if df.empty or symbol not in asset_map:
                continue
            asset = asset_map[symbol]

            for row_date, row in df.iterrows():
                try:
                    stmt = pg_insert(AssetPrice).values(
                        asset_id=asset.id,
                        date=row_date,
                        open=self._safe_float(row.get("open")),
                        high=self._safe_float(row.get("high")),
                        low=self._safe_float(row.get("low")),
                        close=self._safe_float(row.get("close")),
                        volume=self._safe_float(row.get("volume")),
                        adj_close=self._safe_float(row.get("adj close")),
                        sma_20=self._safe_float(row.get("sma_20")),
                        sma_50=self._safe_float(row.get("sma_50")),
                        sma_200=self._safe_float(row.get("sma_200")),
                        ema_20=self._safe_float(row.get("ema_20")),
                        rsi_14=self._safe_float(row.get("rsi_14")),
                        atr_14=self._safe_float(row.get("atr_14")),
                    ).on_conflict_do_update(
                        constraint="uq_asset_price_date",
                        set_={"close": self._safe_float(row.get("close"))}
                    )
                    await db.execute(stmt)
                    stored += 1
                except Exception as e:
                    logger.warning(f"Failed to store price for {symbol} {row_date}: {e}")

            await db.commit()

        return {"stored": stored}

    async def ingest_cot(self, db: AsyncSession) -> dict:
        """Fetch and store COT data."""
        logger.info("Ingesting COT data...")
        stored = 0

        try:
            latest_cot = cot_fetcher.get_latest_cot()
        except Exception as e:
            logger.error(f"COT fetch failed: {e}")
            return {"stored": 0, "error": str(e)}

        for symbol, data in latest_cot.items():
            result = await db.execute(select(Asset).where(Asset.symbol == symbol))
            asset = result.scalar_one_or_none()
            if not asset:
                continue

            stmt = pg_insert(COTReading).values(
                asset_id=asset.id,
                report_date=data["report_date"],
                noncommercial_net=data.get("noncommercial_net"),
                open_interest=data.get("open_interest"),
                net_position_index=data.get("net_position_index"),
                positioning_extreme=data.get("positioning_extreme", False),
                percentile_52w=data.get("percentile_52w"),
            ).on_conflict_do_update(
                constraint="uq_cot_asset_date",
                set_={"noncommercial_net": data.get("noncommercial_net")}
            )
            await db.execute(stmt)
            stored += 1

        await db.commit()
        return {"stored": stored}

    async def compute_and_store_regime(self, db: AsyncSession) -> dict:
        """Compute current macro regime and store to database."""
        logger.info("Computing macro regime...")

        # Pull latest indicator values
        macro_values = await self._get_latest_macro_values(db)

        # Build component scores
        growth_score = score_builder.build_growth_score(
            gdp_growth=macro_values.get("GDP_REAL_QOQ"),
            pmi_manufacturing=macro_values.get("PMI_MANUFACTURING"),
            industrial_production_yoy=None,
            retail_sales_yoy=None,
            leading_index_trend=None,
        )
        inflation_score = score_builder.build_inflation_score(
            cpi_yoy=macro_values.get("CPI_YOY"),
            core_cpi_yoy=macro_values.get("CORE_CPI_YOY"),
            ppi_yoy=macro_values.get("PPI"),
            breakeven_5y=macro_values.get("INFLATION_EXPECTATIONS_5Y"),
        )
        labor_score = score_builder.build_labor_score(
            unemployment_rate=macro_values.get("UNEMPLOYMENT_RATE"),
            nonfarm_payrolls_mom=macro_values.get("NONFARM_PAYROLLS"),
            wage_growth_yoy=macro_values.get("WAGE_GROWTH"),
            jobless_claims=macro_values.get("INITIAL_JOBLESS_CLAIMS"),
        )
        monetary_score = score_builder.build_monetary_score(
            fed_funds_rate=macro_values.get("FED_FUNDS_RATE"),
            yield_curve_10y2y=macro_values.get("YIELD_CURVE_10Y2Y"),
            real_rate_10y=macro_values.get("REAL_RATE_10Y"),
            fed_bs_change_yoy=None,
        )
        risk_score = score_builder.build_risk_score(
            vix=macro_values.get("VIX"),
            hy_credit_spread=macro_values.get("CREDIT_SPREAD_HY"),
            financial_conditions_index=macro_values.get("FINANCIAL_CONDITIONS"),
            equity_trend="uptrend",  # TODO: pull from price data
        )
        liquidity_score = score_builder.build_liquidity_score(
            fed_balance_sheet_yoy=None,
            m2_growth_yoy=None,
            repo_rate_vs_fed_funds=None,
        )

        # Classify regime
        result = regime_classifier.classify(
            growth_score=growth_score,
            inflation_score=inflation_score,
            labor_score=labor_score,
            monetary_score=monetary_score,
            risk_score=risk_score,
            liquidity_score=liquidity_score,
        )

        # Store to DB
        today = date.today()
        regime = MacroRegime(
            date=today,
            regime_type=result["regime_type"],
            regime_label=result["regime_label"],
            regime_confidence=result["regime_confidence"],
            growth_score=result["scores"]["growth"],
            inflation_score=result["scores"]["inflation"],
            labor_score=result["scores"]["labor"],
            monetary_score=result["scores"]["monetary"],
            risk_score=result["scores"]["risk"],
            liquidity_score=result["scores"]["liquidity"],
            macro_composite_score=result["macro_composite_score"],
            recession_probability=result["recession_probability"],
            growth_phase=result["growth_phase"],
            inflation_phase=result["inflation_phase"],
            favorable_assets=result["favorable_assets"],
            unfavorable_assets=result["unfavorable_assets"],
            regime_summary=regime_classifier.generate_regime_narrative(result),
            key_drivers=[],
        )

        stmt = pg_insert(MacroRegime.__table__).values(
            date=today,
            regime_type=result["regime_type"],
            regime_label=result["regime_label"],
            regime_confidence=result["regime_confidence"],
            growth_score=result["scores"]["growth"],
            inflation_score=result["scores"]["inflation"],
            labor_score=result["scores"]["labor"],
            monetary_score=result["scores"]["monetary"],
            risk_score=result["scores"]["risk"],
            liquidity_score=result["scores"]["liquidity"],
            macro_composite_score=result["macro_composite_score"],
            recession_probability=result["recession_probability"],
            favorable_assets=result["favorable_assets"],
            unfavorable_assets=result["unfavorable_assets"],
            regime_summary=regime_classifier.generate_regime_narrative(result),
        ).on_conflict_do_update(
            constraint="macro_regimes_date_key",
            set_={"regime_type": result["regime_type"], "regime_confidence": result["regime_confidence"]}
        )
        await db.execute(stmt)
        await db.commit()

        return result

    async def compute_and_store_bias(self, db: AsyncSession) -> dict:
        """Compute directional bias for all assets and store."""
        logger.info("Computing asset bias signals...")

        # Get latest regime
        result = await db.execute(
            select(MacroRegime).order_by(MacroRegime.date.desc()).limit(1)
        )
        regime_row = result.scalar_one_or_none()
        if not regime_row:
            return {"error": "No regime data found"}

        regime_data = {
            "regime_type": regime_row.regime_type.value if regime_row.regime_type else "risk_on_expansion",
            "regime_label": regime_row.regime_label,
            "macro_composite_score": regime_row.macro_composite_score or 0,
            "favorable_assets": regime_row.favorable_assets or [],
            "unfavorable_assets": regime_row.unfavorable_assets or [],
            "scores": {
                "growth": regime_row.growth_score or 5,
                "inflation": regime_row.inflation_score or 5,
                "labor": regime_row.labor_score or 5,
                "monetary": regime_row.monetary_score or 5,
                "risk": regime_row.risk_score or 5,
                "liquidity": regime_row.liquidity_score or 5,
            },
        }

        # Get all active assets
        result = await db.execute(select(Asset).where(Asset.is_active == True))
        assets = result.scalars().all()

        vix = 20.0  # TODO: pull from price data
        stored = 0

        for asset in assets:
            try:
                bias = bias_engine.calculate_bias(
                    symbol=asset.symbol,
                    asset_class=asset.asset_class.value if asset.asset_class else "equity_index",
                    regime_data=regime_data,
                    vix_level=vix,
                )

                stmt = pg_insert(BiasSignal.__table__).values(
                    asset_id=asset.id,
                    date=date.today(),
                    direction=bias["direction"],
                    strength_score=bias["strength_score"],
                    confidence=bias["confidence"],
                    macro_alignment_score=bias["components"]["macro_alignment"],
                    rate_differential_score=bias["components"]["rate_differential"],
                    growth_inflation_score=bias["components"]["growth_inflation"],
                    risk_sentiment_score=bias["components"]["risk_sentiment"],
                    cot_positioning_score=bias["components"]["cot_positioning"],
                    seasonality_score=bias["components"]["seasonality"],
                    technical_score=bias["components"]["technical"],
                    timing_label=bias["timing_label"],
                    volatility_regime=bias["volatility_regime"],
                    is_favorable_environment=bias["is_favorable_environment"],
                    macro_drivers=bias["macro_drivers"],
                    summary_text=bias["summary_text"],
                ).on_conflict_do_update(
                    constraint="uq_bias_asset_date",
                    set_={"strength_score": bias["strength_score"], "direction": bias["direction"]}
                )
                await db.execute(stmt)
                stored += 1
            except Exception as e:
                logger.error(f"Failed to compute bias for {asset.symbol}: {e}")

        await db.commit()
        return {"stored": stored}

    async def generate_alerts(self, db: AsyncSession, regime_result: dict) -> dict:
        """Generate alerts for regime changes, extremes, etc."""
        alerts_created = 0
        today = date.today()

        # Check for extreme recession probability
        if regime_result and regime_result.get("recession_probability", 0) > 0.6:
            alert = Alert(
                alert_type=AlertType.RECESSION_WARNING,
                severity=AlertSeverity.HIGH,
                date=today,
                title="Elevated Recession Risk Detected",
                message=(
                    f"Recession probability has risen to "
                    f"{int(regime_result['recession_probability']*100)}%. "
                    f"Current regime: {regime_result.get('regime_label', 'Unknown')}."
                ),
            )
            db.add(alert)
            alerts_created += 1

        # Check for VIX extreme (handled in price pipeline)
        await db.commit()
        return {"created": alerts_created}

    async def _get_latest_macro_values(self, db: AsyncSession) -> dict:
        """Pull the most recent value for each macro indicator from DB."""
        from sqlalchemy import text

        query = text("""
            SELECT i.code, r.value
            FROM macro_indicators i
            INNER JOIN LATERAL (
                SELECT value FROM macro_readings
                WHERE indicator_id = i.id
                ORDER BY date DESC
                LIMIT 1
            ) r ON true
            WHERE i.is_active = true
        """)
        result = await db.execute(query)
        return {row.code: row.value for row in result.fetchall()}

    def _infer_asset_class(self, symbol: str) -> str:
        forex = {"EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD", "XAUUSD"}
        indices = {"SPX", "NDX", "DJI", "DAX", "FTSE", "NIKKEI", "HSI"}
        bonds = {"US10Y", "US2Y", "US30Y"}
        if symbol in forex:
            return "forex"
        if symbol in indices:
            return "equity_index"
        if symbol in bonds:
            return "bond"
        return "commodity"

    @staticmethod
    def _safe_float(val) -> Optional[float]:
        try:
            if val is None:
                return None
            f = float(val)
            return None if f != f else f  # NaN check
        except (TypeError, ValueError):
            return None


pipeline = MacroPipeline()
