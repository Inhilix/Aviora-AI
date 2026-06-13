import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Integer, Numeric, Date,
    ARRAY, TIMESTAMP, Text, BigInteger, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Student(Base):
    __tablename__ = "students"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email                = Column(String(255), unique=True, nullable=False)
    password_hash        = Column(String(255), nullable=False)
    full_name            = Column(String(255), nullable=False)
    phone                = Column(String(50))
    created_at           = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    last_active_at       = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    deletion_scheduled_at = Column(TIMESTAMP(timezone=True))
    deletion_notified_at  = Column(TIMESTAMP(timezone=True))
    is_active            = Column(Boolean, default=True)
    is_admin             = Column(Boolean, default=False)
    encryption_key_id    = Column(String(64))

    profile      = relationship("Profile",      back_populates="student", uselist=False)
    applications = relationship("Application",  back_populates="student")
    documents    = relationship("Document",     back_populates="student")
    sop_drafts   = relationship("SopDraft",     back_populates="student")


class Profile(Base):
    __tablename__ = "profiles"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id            = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"))
    gpa                   = Column(Numeric(3, 2))
    gpa_scale             = Column(Numeric(3, 1), default=4.0)
    ielts_overall         = Column(Numeric(3, 1))
    ielts_writing         = Column(Numeric(3, 1))
    gap_years             = Column(Integer, default=0)
    work_experience_months = Column(Integer, default=0)
    financial_proof_usd   = Column(Integer)
    target_countries      = Column(ARRAY(String))
    target_degree         = Column(String(50))
    target_subject        = Column(String(255))
    budget_usd_per_year   = Column(Integer)
    profile_score         = Column(Integer)
    score_breakdown       = Column(JSONB)
    updated_at            = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    student = relationship("Student", back_populates="profile")


class University(Base):
    __tablename__ = "universities"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name                  = Column(String(255), nullable=False)
    country               = Column(String(100), nullable=False)
    city                  = Column(String(100))
    qs_ranking            = Column(Integer)
    course_name           = Column(String(255))
    degree_level          = Column(String(50))
    min_gpa               = Column(Numeric(3, 2))
    min_ielts             = Column(Numeric(3, 1))
    annual_tuition_usd    = Column(Integer)
    application_deadline  = Column(Date)
    intake_months         = Column(ARRAY(Integer))
    visa_approval_rate_pct = Column(Integer)
    accepts_gap_years     = Column(Boolean, default=True)
    notes                 = Column(Text)


class Application(Base):
    __tablename__ = "applications"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id        = Column(UUID(as_uuid=True), ForeignKey("students.id"))
    university_id     = Column(UUID(as_uuid=True), ForeignKey("universities.id"))
    status            = Column(String(50), default="draft")
    applied_at        = Column(TIMESTAMP(timezone=True))
    deadline          = Column(Date)
    offer_received_at = Column(TIMESTAMP(timezone=True))
    notes             = Column(Text)
    created_at        = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    student    = relationship("Student",    back_populates="applications")
    university = relationship("University")


class Document(Base):
    __tablename__ = "documents"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id       = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"))
    doc_type         = Column(String(100))
    file_path        = Column(String(512))
    file_name        = Column(String(255))
    file_size_bytes  = Column(Integer)
    checksum_sha256  = Column(String(64))
    uploaded_at      = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    expires_at       = Column(TIMESTAMP(timezone=True))

    student = relationship("Student", back_populates="documents")


class SopDraft(Base):
    __tablename__ = "sop_drafts"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id    = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"))
    university_id = Column(UUID(as_uuid=True), ForeignKey("universities.id"))
    version       = Column(Integer, default=1)
    content       = Column(Text)
    prompt_used   = Column(Text)
    model_version = Column(String(100))
    critique      = Column(Text)
    created_at    = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    student    = relationship("Student",    back_populates="sop_drafts")
    university = relationship("University")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id          = Column(BigInteger, primary_key=True, autoincrement=True)
    student_id  = Column(UUID(as_uuid=True))
    admin_id    = Column(UUID(as_uuid=True))
    action      = Column(String(100), nullable=False)
    entity_type = Column(String(100))
    entity_id   = Column(UUID(as_uuid=True))
    ip_address  = Column(INET)
    user_agent  = Column(Text)
    details     = Column(JSONB)
    created_at  = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic     = Column(String(100))
    country   = Column(String(100))
    content   = Column(Text)
    embedding = Column(Vector(768))
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ApiUsage(Base):
    __tablename__ = "api_usage"

    id            = Column(BigInteger, primary_key=True, autoincrement=True)
    student_id    = Column(UUID(as_uuid=True), ForeignKey("students.id"))
    endpoint      = Column(String(100))
    model         = Column(String(100), default="claude-haiku-4-5")
    input_tokens  = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    cost_usd      = Column(Numeric(10, 6))
    duration_ms   = Column(Integer)
    created_at    = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, index=True)


class UserTokenBudget(Base):
    __tablename__ = "user_token_budgets"

    student_id   = Column(UUID(as_uuid=True), ForeignKey("students.id"), primary_key=True)
    budget_date  = Column(Date, nullable=False, primary_key=True)
    tokens_used  = Column(Integer, default=0)
    daily_limit  = Column(Integer, default=50_000)
    is_suspended = Column(Boolean, default=False)


class GuardrailViolation(Base):
    __tablename__ = "guardrail_violations"

    id             = Column(BigInteger, primary_key=True, autoincrement=True)
    student_id     = Column(UUID(as_uuid=True), ForeignKey("students.id"))
    violation_type = Column(String(50))
    raw_input      = Column(String(500))
    ip_address     = Column(INET)
    created_at     = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("ix_guardrail_violations_student_created", "student_id", "created_at"),
    )
