"""add bero integration tables

Revision ID: d1e2f3a4b5c6
Revises: c1d110990bbf
Create Date: 2026-02-17
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1e2f3a4b5c6'
down_revision = 'c1d110990bbf'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('products', sa.Column('origin', sa.String(), nullable=False, server_default='LOCAL'))
    op.create_index('ix_products_origin', 'products', ['origin'], unique=False)

    op.create_table(
        'store_bero_connections',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('store_id', sa.Integer(), sa.ForeignKey('stores.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('company_identifier', sa.String(), nullable=False),
        sa.Column('company_token_encrypted', sa.Text(), nullable=False),
        sa.Column('bero_tenant_id', sa.String(), nullable=True),
        sa.Column('company_name', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='PENDING_VERIFY'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_successful_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_store_bero_connections_store_id', 'store_bero_connections', ['store_id'], unique=True)
    op.create_index('ix_store_bero_connections_status', 'store_bero_connections', ['status'], unique=False)

    op.create_table(
        'product_external_mappings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('store_id', sa.Integer(), sa.ForeignKey('stores.id', ondelete='CASCADE'), nullable=False),
        sa.Column('shop_product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('external_system', sa.String(), nullable=False, server_default='BERO'),
        sa.Column('bero_product_id', sa.String(), nullable=False),
        sa.Column('barcode', sa.String(), nullable=True),
        sa.Column('sku', sa.String(), nullable=True),
        sa.Column('sync_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('store_id', 'external_system', 'bero_product_id', name='uq_store_external_bero_product'),
        sa.UniqueConstraint('store_id', 'shop_product_id', 'external_system', name='uq_store_shop_product_external'),
    )
    op.create_index('ix_product_external_mappings_store_id', 'product_external_mappings', ['store_id'], unique=False)
    op.create_index('ix_product_external_mappings_shop_product_id', 'product_external_mappings', ['shop_product_id'], unique=False)
    op.create_index('ix_product_external_mappings_bero_product_id', 'product_external_mappings', ['bero_product_id'], unique=False)
    op.create_index('ix_product_external_mappings_barcode', 'product_external_mappings', ['barcode'], unique=False)
    op.create_index('ix_product_external_mappings_sku', 'product_external_mappings', ['sku'], unique=False)

    op.create_table(
        'bero_sync_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('store_id', sa.Integer(), sa.ForeignKey('stores.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='PENDING'),
        sa.Column('cursor', sa.String(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_bero_sync_jobs_store_id', 'bero_sync_jobs', ['store_id'], unique=False)
    op.create_index('ix_bero_sync_jobs_status', 'bero_sync_jobs', ['status'], unique=False)

    op.create_table(
        'bero_outbox_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('store_id', sa.Integer(), sa.ForeignKey('stores.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False, server_default='ORDER_ACCEPTED'),
        sa.Column('payload_json', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='PENDING'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('bero_sales_invoice_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_bero_outbox_events_store_id', 'bero_outbox_events', ['store_id'], unique=False)
    op.create_index('ix_bero_outbox_events_order_id', 'bero_outbox_events', ['order_id'], unique=False)
    op.create_index('ix_bero_outbox_events_status', 'bero_outbox_events', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_bero_outbox_events_status', table_name='bero_outbox_events')
    op.drop_index('ix_bero_outbox_events_order_id', table_name='bero_outbox_events')
    op.drop_index('ix_bero_outbox_events_store_id', table_name='bero_outbox_events')
    op.drop_table('bero_outbox_events')

    op.drop_index('ix_bero_sync_jobs_status', table_name='bero_sync_jobs')
    op.drop_index('ix_bero_sync_jobs_store_id', table_name='bero_sync_jobs')
    op.drop_table('bero_sync_jobs')

    op.drop_index('ix_product_external_mappings_sku', table_name='product_external_mappings')
    op.drop_index('ix_product_external_mappings_barcode', table_name='product_external_mappings')
    op.drop_index('ix_product_external_mappings_bero_product_id', table_name='product_external_mappings')
    op.drop_index('ix_product_external_mappings_shop_product_id', table_name='product_external_mappings')
    op.drop_index('ix_product_external_mappings_store_id', table_name='product_external_mappings')
    op.drop_table('product_external_mappings')

    op.drop_index('ix_store_bero_connections_status', table_name='store_bero_connections')
    op.drop_index('ix_store_bero_connections_store_id', table_name='store_bero_connections')
    op.drop_table('store_bero_connections')

    op.drop_index('ix_products_origin', table_name='products')
    op.drop_column('products', 'origin')
