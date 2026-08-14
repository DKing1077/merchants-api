"""feature expansion

Revision ID: 4b9a66e4f7a1
Revises: 2f837bbf0498
Create Date: 2026-08-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "4b9a66e4f7a1"
down_revision: Union[str, Sequence[str], None] = "2f837bbf0498"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


JSONType = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    with op.batch_alter_table("payment_intents") as batch_op:
        batch_op.add_column(sa.Column("merchant_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("captured_amount", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("is_flagged", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("review_status", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("review_reason", sa.Text(), nullable=True))
        batch_op.create_index("ix_payment_intents_merchant_id", ["merchant_id"], unique=False)
    op.execute("UPDATE payment_intents SET merchant_id = 'unknown_merchant' WHERE merchant_id IS NULL")
    with op.batch_alter_table("payment_intents") as batch_op:
        batch_op.alter_column("merchant_id", existing_type=sa.String(), nullable=False)

    with op.batch_alter_table("refunds") as batch_op:
        batch_op.alter_column("amout", new_column_name="amount", existing_type=sa.Integer())
        batch_op.add_column(sa.Column("merchant_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("is_flagged", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("review_status", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("review_reason", sa.Text(), nullable=True))
        batch_op.create_index("ix_refunds_merchant_id", ["merchant_id"], unique=False)
    op.execute(
        "UPDATE refunds SET merchant_id = (SELECT merchant_id FROM payment_intents WHERE payment_intents.id = refunds.payment_intent_id) WHERE merchant_id IS NULL"
    )
    with op.batch_alter_table("refunds") as batch_op:
        batch_op.alter_column("merchant_id", existing_type=sa.String(), nullable=False)

    op.create_table(
        "events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("object_id", sa.String(), nullable=False),
        sa.Column("payload", JSONType, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_events_type"), "events", ["type"], unique=False)
    op.create_index(op.f("ix_events_object_id"), "events", ["object_id"], unique=False)

    op.create_table(
        "webhook_endpoints",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("merchant_id", sa.String(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("event_types", JSONType, nullable=False),
        sa.Column("secret", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_webhook_endpoints_merchant_id"), "webhook_endpoints", ["merchant_id"], unique=False)

    op.create_table(
        "webhook_dispatches",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("webhook_endpoint_id", sa.String(), nullable=False),
        sa.Column("payload", JSONType, nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["webhook_endpoint_id"], ["webhook_endpoints.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_webhook_dispatches_event_id"), "webhook_dispatches", ["event_id"], unique=False)
    op.create_index(op.f("ix_webhook_dispatches_webhook_endpoint_id"), "webhook_dispatches", ["webhook_endpoint_id"], unique=False)

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("webhook_dispatch_id", sa.String(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["webhook_dispatch_id"], ["webhook_dispatches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_webhook_deliveries_webhook_dispatch_id"), "webhook_deliveries", ["webhook_dispatch_id"], unique=False)

    op.create_table(
        "ledger_accounts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("merchant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("account_type", sa.String(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ledger_accounts_merchant_id"), "ledger_accounts", ["merchant_id"], unique=False)

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("entry_type", sa.String(), nullable=False),
        sa.Column("reference_id", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("entry_metadata", JSONType, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ledger_entries_reference_id"), "ledger_entries", ["reference_id"], unique=False)

    op.create_table(
        "ledger_postings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("entry_id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["ledger_accounts.id"]),
        sa.ForeignKeyConstraint(["entry_id"], ["ledger_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ledger_postings_account_id"), "ledger_postings", ["account_id"], unique=False)
    op.create_index(op.f("ix_ledger_postings_entry_id"), "ledger_postings", ["entry_id"], unique=False)

    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("key_hash", sa.String(), nullable=False),
        sa.Column("merchant_id", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_api_keys_key_hash"), "api_keys", ["key_hash"], unique=True)
    op.create_index(op.f("ix_api_keys_merchant_id"), "api_keys", ["merchant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_api_keys_merchant_id"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_key_hash"), table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_index(op.f("ix_ledger_postings_entry_id"), table_name="ledger_postings")
    op.drop_index(op.f("ix_ledger_postings_account_id"), table_name="ledger_postings")
    op.drop_table("ledger_postings")
    op.drop_index(op.f("ix_ledger_entries_reference_id"), table_name="ledger_entries")
    op.drop_table("ledger_entries")
    op.drop_index(op.f("ix_ledger_accounts_merchant_id"), table_name="ledger_accounts")
    op.drop_table("ledger_accounts")
    op.drop_index(op.f("ix_webhook_deliveries_webhook_dispatch_id"), table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")
    op.drop_index(op.f("ix_webhook_dispatches_webhook_endpoint_id"), table_name="webhook_dispatches")
    op.drop_index(op.f("ix_webhook_dispatches_event_id"), table_name="webhook_dispatches")
    op.drop_table("webhook_dispatches")
    op.drop_index(op.f("ix_webhook_endpoints_merchant_id"), table_name="webhook_endpoints")
    op.drop_table("webhook_endpoints")
    op.drop_index(op.f("ix_events_object_id"), table_name="events")
    op.drop_index(op.f("ix_events_type"), table_name="events")
    op.drop_table("events")

    with op.batch_alter_table("refunds") as batch_op:
        batch_op.drop_index("ix_refunds_merchant_id")
        batch_op.drop_column("review_reason")
        batch_op.drop_column("review_status")
        batch_op.drop_column("is_flagged")
        batch_op.drop_column("merchant_id")
        batch_op.alter_column("amount", new_column_name="amout", existing_type=sa.Integer())

    with op.batch_alter_table("payment_intents") as batch_op:
        batch_op.drop_index("ix_payment_intents_merchant_id")
        batch_op.drop_column("review_reason")
        batch_op.drop_column("review_status")
        batch_op.drop_column("is_flagged")
        batch_op.drop_column("risk_score")
        batch_op.drop_column("captured_amount")
        batch_op.drop_column("merchant_id")
