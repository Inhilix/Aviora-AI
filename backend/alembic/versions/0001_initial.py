"""Initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
import sqlalchemy.dialects.postgresql as pg

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "students",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("last_active_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("deletion_scheduled_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("deletion_notified_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("is_active", sa.Boolean, server_default="TRUE"),
        sa.Column("is_admin", sa.Boolean, server_default="FALSE"),
        sa.Column("encryption_key_id", sa.String(64)),
    )

    op.create_table(
        "profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("student_id", UUID(as_uuid=True), sa.ForeignKey("students.id", ondelete="CASCADE")),
        sa.Column("gpa", sa.Numeric(3, 2)),
        sa.Column("gpa_scale", sa.Numeric(3, 1), server_default="4.0"),
        sa.Column("ielts_overall", sa.Numeric(3, 1)),
        sa.Column("ielts_writing", sa.Numeric(3, 1)),
        sa.Column("gap_years", sa.Integer, server_default="0"),
        sa.Column("work_experience_months", sa.Integer, server_default="0"),
        sa.Column("financial_proof_usd", sa.Integer),
        sa.Column("target_countries", pg.ARRAY(sa.String)),
        sa.Column("target_degree", sa.String(50)),
        sa.Column("target_subject", sa.String(255)),
        sa.Column("budget_usd_per_year", sa.Integer),
        sa.Column("profile_score", sa.Integer),
        sa.Column("score_breakdown", JSONB),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "universities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("city", sa.String(100)),
        sa.Column("qs_ranking", sa.Integer),
        sa.Column("course_name", sa.String(255)),
        sa.Column("degree_level", sa.String(50)),
        sa.Column("min_gpa", sa.Numeric(3, 2)),
        sa.Column("min_ielts", sa.Numeric(3, 1)),
        sa.Column("annual_tuition_usd", sa.Integer),
        sa.Column("application_deadline", sa.Date),
        sa.Column("intake_months", pg.ARRAY(sa.Integer)),
        sa.Column("visa_approval_rate_pct", sa.Integer),
        sa.Column("accepts_gap_years", sa.Boolean, server_default="TRUE"),
        sa.Column("notes", sa.Text),
    )

    op.create_table(
        "applications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("student_id", UUID(as_uuid=True), sa.ForeignKey("students.id")),
        sa.Column("university_id", UUID(as_uuid=True), sa.ForeignKey("universities.id")),
        sa.Column("status", sa.String(50), server_default="'draft'"),
        sa.Column("applied_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("deadline", sa.Date),
        sa.Column("offer_received_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("student_id", UUID(as_uuid=True), sa.ForeignKey("students.id", ondelete="CASCADE")),
        sa.Column("doc_type", sa.String(100)),
        sa.Column("file_path", sa.String(512)),
        sa.Column("file_name", sa.String(255)),
        sa.Column("file_size_bytes", sa.Integer),
        sa.Column("checksum_sha256", sa.String(64)),
        sa.Column("uploaded_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True)),
    )

    op.create_table(
        "sop_drafts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("student_id", UUID(as_uuid=True), sa.ForeignKey("students.id", ondelete="CASCADE")),
        sa.Column("university_id", UUID(as_uuid=True), sa.ForeignKey("universities.id")),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("content", sa.Text),
        sa.Column("prompt_used", sa.Text),
        sa.Column("model_version", sa.String(100)),
        sa.Column("critique", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("student_id", UUID(as_uuid=True)),
        sa.Column("admin_id", UUID(as_uuid=True)),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100)),
        sa.Column("entity_id", UUID(as_uuid=True)),
        sa.Column("ip_address", INET),
        sa.Column("user_agent", sa.Text),
        sa.Column("details", JSONB),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # Append-only audit log trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION deny_audit_mutations()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only. UPDATE and DELETE are not permitted.';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER audit_logs_append_only
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION deny_audit_mutations();
    """)

    op.create_table(
        "knowledge_base",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("topic", sa.String(100)),
        sa.Column("country", sa.String(100)),
        sa.Column("content", sa.Text),
        # vector column added via raw SQL — SQLAlchemy type not needed in migration
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.execute("ALTER TABLE knowledge_base ADD COLUMN embedding vector(768)")
    op.execute("CREATE INDEX ON knowledge_base USING ivfflat (embedding vector_cosine_ops)")

    op.create_table(
        "api_usage",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("student_id", UUID(as_uuid=True), sa.ForeignKey("students.id")),
        sa.Column("endpoint", sa.String(100)),
        sa.Column("model", sa.String(100), server_default="'claude-haiku-4-5'"),
        sa.Column("input_tokens", sa.Integer, nullable=False),
        sa.Column("output_tokens", sa.Integer, nullable=False),
        sa.Column("cost_usd", sa.Numeric(10, 6)),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_api_usage_created_at", "api_usage", ["created_at"])

    op.create_table(
        "user_token_budgets",
        sa.Column("student_id", UUID(as_uuid=True), sa.ForeignKey("students.id"), primary_key=True),
        sa.Column("budget_date", sa.Date, nullable=False, primary_key=True),
        sa.Column("tokens_used", sa.Integer, server_default="0"),
        sa.Column("daily_limit", sa.Integer, server_default="50000"),
        sa.Column("is_suspended", sa.Boolean, server_default="FALSE"),
    )

    op.create_table(
        "guardrail_violations",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("student_id", UUID(as_uuid=True), sa.ForeignKey("students.id")),
        sa.Column("violation_type", sa.String(50)),
        sa.Column("raw_input", sa.String(500)),
        sa.Column("ip_address", INET),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_guardrail_student_created", "guardrail_violations", ["student_id", "created_at"])


def downgrade():
    for table in [
        "guardrail_violations", "user_token_budgets", "api_usage",
        "knowledge_base", "audit_logs", "sop_drafts", "documents",
        "applications", "universities", "profiles", "students",
    ]:
        op.drop_table(table)
