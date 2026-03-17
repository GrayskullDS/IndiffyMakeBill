"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- macro_indicators ---
    op.create_table(
        'macro_indicators',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(64), nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.Enum(
            'growth','inflation','labor','monetary','sentiment',
            'positioning','price','volatility', name='indicatorcategory'), nullable=False),
        sa.Column('frequency', sa.Enum(
            'daily','weekly','monthly','quarterly','annual', name='datafrequency'), nullable=False),
        sa.Column('unit', sa.String(64), nullable=True),
        sa.Column('source', sa.String(64), nullable=True),
        sa.Column('source_series_id', sa.String(128), nullable=True),
        sa.Column('country', sa.String(8), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('ix_macro_indicators_code', 'macro_indicators', ['code'])

    # --- macro_readings ---
    op.create_table(
        'macro_readings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('indicator_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('prior_value', sa.Float(), nullable=True),
        sa.Column('revision_flag', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['indicator_id'], ['macro_indicators.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('indicator_id', 'date', name='uq_indicator_date'),
    )
    op.create_index('ix_macro_readings_indicator_date', 'macro_readings', ['indicator_id', 'date'])

    # --- macro_z_scores ---
    op.create_table(
        'macro_z_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('indicator_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('window_months', sa.Integer(), nullable=False),
        sa.Column('z_score', sa.Float(), nullable=False),
        sa.Column('percentile', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['indicator_id'], ['macro_indicators.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('indicator_id', 'date', 'window_months', name='uq_zscore_indicator_date_window'),
    )

    # --- macro_regimes ---
    op.create_table(
        'macro_regimes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('regime_type', sa.Enum(
            'risk_on_expansion','risk_off_fear','inflationary_boom','deflationary_slowdown',
            'policy_tightening','policy_easing','liquidity_expansion','liquidity_contraction',
            'stagflation','recovery', name='regimetype'), nullable=False),
        sa.Column('regime_label', sa.String(128), nullable=False),
        sa.Column('regime_confidence', sa.Float(), nullable=False),
        sa.Column('regime_duration_days', sa.Integer(), nullable=True),
        sa.Column('growth_score', sa.Float(), nullable=True),
        sa.Column('inflation_score', sa.Float(), nullable=True),
        sa.Column('labor_score', sa.Float(), nullable=True),
        sa.Column('monetary_score', sa.Float(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('liquidity_score', sa.Float(), nullable=True),
        sa.Column('growth_phase', sa.Enum('expansion','peak','contraction','trough', name='growthphase'), nullable=True),
        sa.Column('inflation_phase', sa.Enum('rising','high_stable','falling','low_stable', name='inflationphase'), nullable=True),
        sa.Column('macro_composite_score', sa.Float(), nullable=True),
        sa.Column('recession_probability', sa.Float(), nullable=True),
        sa.Column('regime_summary', sa.Text(), nullable=True),
        sa.Column('key_drivers', sa.JSON(), nullable=True),
        sa.Column('favorable_assets', sa.JSON(), nullable=True),
        sa.Column('unfavorable_assets', sa.JSON(), nullable=True),
        sa.Column('is_regime_change', sa.Boolean(), nullable=True),
        sa.Column('previous_regime', sa.Enum(
            'risk_on_expansion','risk_off_fear','inflationary_boom','deflationary_slowdown',
            'policy_tightening','policy_easing','liquidity_expansion','liquidity_contraction',
            'stagflation','recovery', name='regimetype_prev'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date'),
    )
    op.create_index('ix_macro_regimes_date', 'macro_regimes', ['date'])

    # --- assets ---
    op.create_table(
        'assets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(32), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('asset_class', sa.Enum(
            'forex','equity_index','commodity','bond','crypto', name='assetclass'), nullable=False),
        sa.Column('yfinance_ticker', sa.String(32), nullable=True),
        sa.Column('base_currency', sa.String(8), nullable=True),
        sa.Column('quote_currency', sa.String(8), nullable=True),
        sa.Column('country', sa.String(8), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol'),
    )
    op.create_index('ix_assets_symbol', 'assets', ['symbol'])

    # --- asset_prices ---
    op.create_table(
        'asset_prices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('open', sa.Float(), nullable=True),
        sa.Column('high', sa.Float(), nullable=True),
        sa.Column('low', sa.Float(), nullable=True),
        sa.Column('close', sa.Float(), nullable=False),
        sa.Column('volume', sa.Float(), nullable=True),
        sa.Column('adj_close', sa.Float(), nullable=True),
        sa.Column('sma_20', sa.Float(), nullable=True),
        sa.Column('sma_50', sa.Float(), nullable=True),
        sa.Column('sma_200', sa.Float(), nullable=True),
        sa.Column('ema_20', sa.Float(), nullable=True),
        sa.Column('rsi_14', sa.Float(), nullable=True),
        sa.Column('atr_14', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_id', 'date', name='uq_asset_price_date'),
    )
    op.create_index('ix_asset_prices_asset_date', 'asset_prices', ['asset_id', 'date'])

    # --- bias_signals ---
    op.create_table(
        'bias_signals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('direction', sa.Enum(
            'strong_bullish','bullish','neutral_bullish','neutral',
            'neutral_bearish','bearish','strong_bearish', name='biasdirection'), nullable=False),
        sa.Column('strength_score', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('macro_alignment_score', sa.Float(), nullable=True),
        sa.Column('rate_differential_score', sa.Float(), nullable=True),
        sa.Column('growth_inflation_score', sa.Float(), nullable=True),
        sa.Column('risk_sentiment_score', sa.Float(), nullable=True),
        sa.Column('cot_positioning_score', sa.Float(), nullable=True),
        sa.Column('seasonality_score', sa.Float(), nullable=True),
        sa.Column('technical_score', sa.Float(), nullable=True),
        sa.Column('relative_strength_score', sa.Float(), nullable=True),
        sa.Column('timing_label', sa.String(64), nullable=True),
        sa.Column('volatility_regime', sa.String(32), nullable=True),
        sa.Column('is_favorable_environment', sa.Boolean(), nullable=True),
        sa.Column('macro_drivers', sa.JSON(), nullable=True),
        sa.Column('key_risks', sa.JSON(), nullable=True),
        sa.Column('summary_text', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_id', 'date', name='uq_bias_asset_date'),
    )
    op.create_index('ix_bias_signals_asset_date', 'bias_signals', ['asset_id', 'date'])

    # --- cot_readings ---
    op.create_table(
        'cot_readings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('report_date', sa.Date(), nullable=False),
        sa.Column('release_date', sa.Date(), nullable=True),
        sa.Column('commercial_long', sa.Float(), nullable=True),
        sa.Column('commercial_short', sa.Float(), nullable=True),
        sa.Column('commercial_net', sa.Float(), nullable=True),
        sa.Column('noncommercial_long', sa.Float(), nullable=True),
        sa.Column('noncommercial_short', sa.Float(), nullable=True),
        sa.Column('noncommercial_net', sa.Float(), nullable=True),
        sa.Column('nonreportable_long', sa.Float(), nullable=True),
        sa.Column('nonreportable_short', sa.Float(), nullable=True),
        sa.Column('nonreportable_net', sa.Float(), nullable=True),
        sa.Column('open_interest', sa.Float(), nullable=True),
        sa.Column('net_position_index', sa.Float(), nullable=True),
        sa.Column('positioning_extreme', sa.Boolean(), nullable=True),
        sa.Column('percentile_52w', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_id', 'report_date', name='uq_cot_asset_date'),
    )

    # --- seasonality_data ---
    op.create_table(
        'seasonality_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('lookback_years', sa.Integer(), nullable=False),
        sa.Column('avg_return', sa.Float(), nullable=True),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('median_return', sa.Float(), nullable=True),
        sa.Column('std_dev', sa.Float(), nullable=True),
        sa.Column('best_return', sa.Float(), nullable=True),
        sa.Column('worst_return', sa.Float(), nullable=True),
        sa.Column('sample_size', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_id', 'month', 'lookback_years', name='uq_seasonality'),
    )

    # --- alerts ---
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_type', sa.Enum(
            'regime_change','positioning_extreme','macro_divergence',
            'recession_warning','volatility_spike','bias_change','seasonal_setup',
            name='alerttype'), nullable=False),
        sa.Column('severity', sa.Enum('info','medium','high','critical', name='alertseverity'), nullable=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('title', sa.String(256), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('asset_symbol', sa.String(32), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_alerts_date', 'alerts', ['date'])


def downgrade() -> None:
    op.drop_table('alerts')
    op.drop_table('seasonality_data')
    op.drop_table('cot_readings')
    op.drop_table('bias_signals')
    op.drop_table('asset_prices')
    op.drop_table('assets')
    op.drop_table('macro_regimes')
    op.drop_table('macro_z_scores')
    op.drop_table('macro_readings')
    op.drop_table('macro_indicators')
