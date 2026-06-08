"""AI intelligence monitoring features

Revision ID: 0003_ai_intelligence
Revises: 0002_phase3_features
Create Date: 2026-06-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003_ai_intelligence'
down_revision: Union[str, None] = '0002_phase3_features'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Intelligence Sources table
    op.create_table(
        'intelligence_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('source_type', sa.String(20), nullable=False),
        sa.Column('url', sa.String(500), nullable=True),
        sa.Column('api_key', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('check_interval_minutes', sa.Integer(), nullable=False, default=15),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='active'),
        sa.Column('reliability_score', sa.Float(), nullable=False, default=0.7),
        sa.Column('default_region', sa.String(100), nullable=True),
        sa.Column('default_theme', sa.String(100), nullable=True),
        sa.Column('priority_keywords', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('analysts.id'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_intelligence_sources_id', 'intelligence_sources', ['id'])

    # Raw Intel Items table
    op.create_table(
        'raw_intel_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), sa.ForeignKey('intelligence_sources.id'), nullable=False),
        sa.Column('external_id', sa.String(500), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('url', sa.String(500), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_processed', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_relevant', sa.Boolean(), nullable=True),
        sa.Column('is_duplicate', sa.Boolean(), nullable=False, default=False),
        sa.Column('ai_summary', sa.Text(), nullable=True),
        sa.Column('ai_region', sa.String(100), nullable=True),
        sa.Column('ai_country', sa.String(100), nullable=True),
        sa.Column('ai_theme', sa.String(100), nullable=True),
        sa.Column('ai_sector', sa.String(100), nullable=True),
        sa.Column('ai_severity', sa.Integer(), nullable=True),
        sa.Column('ai_confidence', sa.Float(), nullable=True),
        sa.Column('ai_tags', sa.Text(), nullable=True),
        sa.Column('ai_reasoning', sa.Text(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.id'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_raw_intel_items_id', 'raw_intel_items', ['id'])
    op.create_index('ix_raw_intel_items_external_id', 'raw_intel_items', ['external_id'])
    op.create_index('ix_raw_intel_items_is_processed', 'raw_intel_items', ['is_processed'])

    # Signals table
    op.create_table(
        'signals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('signal_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('region', sa.String(100), nullable=False),
        sa.Column('countries', sa.Text(), nullable=True),
        sa.Column('themes', sa.Text(), nullable=False),
        sa.Column('supporting_event_ids', sa.Text(), nullable=False),
        sa.Column('evidence_summary', sa.Text(), nullable=False),
        sa.Column('key_indicators', sa.Text(), nullable=False),
        sa.Column('watch_for', sa.Text(), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_acknowledged', sa.Boolean(), nullable=False, default=False),
        sa.Column('acknowledged_by_id', sa.Integer(), sa.ForeignKey('analysts.id'), nullable=True),
        sa.Column('analyst_notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_signals_id', 'signals', ['id'])
    op.create_index('ix_signals_region', 'signals', ['region'])
    op.create_index('ix_signals_is_active', 'signals', ['is_active'])

    # Market Indicators table
    op.create_table(
        'market_indicators',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('current_value', sa.Float(), nullable=True),
        sa.Column('previous_value', sa.Float(), nullable=True),
        sa.Column('change_percent', sa.Float(), nullable=True),
        sa.Column('relevant_regions', sa.Text(), nullable=True),
        sa.Column('relevant_themes', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('data_source', sa.String(200), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_market_indicators_id', 'market_indicators', ['id'])
    op.create_index('ix_market_indicators_symbol', 'market_indicators', ['symbol'])
    op.create_index('ix_market_indicators_category', 'market_indicators', ['category'])

    # Prediction Markets table
    op.create_table(
        'prediction_markets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('question', sa.String(500), nullable=False),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('external_url', sa.String(500), nullable=True),
        sa.Column('probability_yes', sa.Float(), nullable=False),
        sa.Column('probability_change_24h', sa.Float(), nullable=True),
        sa.Column('volume', sa.Float(), nullable=True),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('theme', sa.String(100), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_prediction_markets_id', 'prediction_markets', ['id'])
    op.create_index('ix_prediction_markets_region', 'prediction_markets', ['region'])
    op.create_index('ix_prediction_markets_theme', 'prediction_markets', ['theme'])

    # Priority Areas table
    op.create_table(
        'priority_areas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('regions', sa.Text(), nullable=False),
        sa.Column('countries', sa.Text(), nullable=True),
        sa.Column('themes', sa.Text(), nullable=False),
        sa.Column('keywords', sa.Text(), nullable=False),
        sa.Column('severity_threshold', sa.Integer(), nullable=False, default=3),
        sa.Column('alert_on_new_events', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('analysts.id'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_priority_areas_id', 'priority_areas', ['id'])

    # Add new columns to existing tables
    # Events table - AI tracking
    op.add_column('events', sa.Column('is_ai_generated', sa.Boolean(), nullable=True, default=False))
    op.add_column('events', sa.Column('ai_source_id', sa.Integer(), sa.ForeignKey('intelligence_sources.id'), nullable=True))

    # EventTimelineEntry - entry type
    op.add_column('event_timeline_entries', sa.Column('entry_type', sa.String(50), nullable=True, default='manual'))

    # Tags - category
    op.add_column('tags', sa.Column('category', sa.String(50), nullable=True))

    # Outlook - scope and AI analysis
    op.add_column('outlooks', sa.Column('region', sa.String(100), nullable=True))
    op.add_column('outlooks', sa.Column('theme', sa.String(100), nullable=True))
    op.add_column('outlooks', sa.Column('executive_summary', sa.Text(), nullable=True))
    op.add_column('outlooks', sa.Column('sentiment', sa.String(20), nullable=True))
    op.add_column('outlooks', sa.Column('risk_direction', sa.String(20), nullable=True))
    op.add_column('outlooks', sa.Column('source_event_ids', sa.Text(), nullable=True))

    # Scenario - extended fields
    op.add_column('scenarios', sa.Column('region', sa.String(100), nullable=True))
    op.add_column('scenarios', sa.Column('theme', sa.String(100), nullable=True))
    op.add_column('scenarios', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('scenarios', sa.Column('warning_indicators', sa.Text(), nullable=True))
    op.add_column('scenarios', sa.Column('operational_impacts', sa.Text(), nullable=True))
    op.add_column('scenarios', sa.Column('market_impacts', sa.Text(), nullable=True))

    # AskAnythingQuery - extended fields
    op.add_column('ask_anything_queries', sa.Column('sentiment', sa.String(20), nullable=True))
    op.add_column('ask_anything_queries', sa.Column('risk_assessment', sa.Text(), nullable=True))

    # Create indexes for new columns
    op.create_index('ix_outlooks_region', 'outlooks', ['region'])
    op.create_index('ix_outlooks_theme', 'outlooks', ['theme'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_outlooks_theme', 'outlooks')
    op.drop_index('ix_outlooks_region', 'outlooks')

    # Remove added columns
    op.drop_column('ask_anything_queries', 'risk_assessment')
    op.drop_column('ask_anything_queries', 'sentiment')

    op.drop_column('scenarios', 'market_impacts')
    op.drop_column('scenarios', 'operational_impacts')
    op.drop_column('scenarios', 'warning_indicators')
    op.drop_column('scenarios', 'description')
    op.drop_column('scenarios', 'theme')
    op.drop_column('scenarios', 'region')

    op.drop_column('outlooks', 'source_event_ids')
    op.drop_column('outlooks', 'risk_direction')
    op.drop_column('outlooks', 'sentiment')
    op.drop_column('outlooks', 'executive_summary')
    op.drop_column('outlooks', 'theme')
    op.drop_column('outlooks', 'region')

    op.drop_column('tags', 'category')
    op.drop_column('event_timeline_entries', 'entry_type')
    op.drop_column('events', 'ai_source_id')
    op.drop_column('events', 'is_ai_generated')

    # Drop new tables
    op.drop_table('priority_areas')
    op.drop_table('prediction_markets')
    op.drop_table('market_indicators')
    op.drop_table('signals')
    op.drop_table('raw_intel_items')
    op.drop_table('intelligence_sources')

