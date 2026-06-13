from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=255)
    phone: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    message: str = "Logged in"


# ── Profile ───────────────────────────────────────────────────────────────────

class ProfileCreate(BaseModel):
    gpa: float = Field(ge=0, le=10)
    gpa_scale: float = Field(default=4.0, ge=1.0, le=10.0)
    ielts_overall: Optional[float] = Field(None, ge=0, le=9)
    ielts_writing: Optional[float] = Field(None, ge=0, le=9)
    gap_years: int = Field(default=0, ge=0)
    work_experience_months: int = Field(default=0, ge=0)
    financial_proof_usd: Optional[int] = Field(None, ge=0)
    target_countries: List[str] = []
    target_degree: Optional[str] = None
    target_subject: Optional[str] = None
    budget_usd_per_year: Optional[int] = None


class ProfileResponse(ProfileCreate):
    id: UUID
    student_id: UUID
    profile_score: Optional[int]
    score_breakdown: Optional[dict]
    updated_at: datetime

    class Config:
        from_attributes = True


# ── University ────────────────────────────────────────────────────────────────

class UniversityResponse(BaseModel):
    id: UUID
    name: str
    country: str
    city: Optional[str]
    qs_ranking: Optional[int]
    course_name: Optional[str]
    degree_level: Optional[str]
    min_gpa: Optional[float]
    min_ielts: Optional[float]
    annual_tuition_usd: Optional[int]
    application_deadline: Optional[date]
    visa_approval_rate_pct: Optional[int]
    accepts_gap_years: bool
    match_score: Optional[int] = None

    class Config:
        from_attributes = True


# ── Applications ──────────────────────────────────────────────────────────────

class ApplicationCreate(BaseModel):
    university_id: UUID
    deadline: Optional[date] = None
    notes: Optional[str] = None


class ApplicationResponse(ApplicationCreate):
    id: UUID
    student_id: UUID
    status: str
    applied_at: Optional[datetime]
    offer_received_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Documents ─────────────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: UUID
    doc_type: str
    file_name: str
    file_size_bytes: int
    uploaded_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── SOP ───────────────────────────────────────────────────────────────────────

class SopGenerateRequest(BaseModel):
    university_id: UUID
    additional_context: Optional[str] = Field(None, max_length=1000)


class SopDraftResponse(BaseModel):
    id: UUID
    university_id: UUID
    version: int
    content: Optional[str]
    critique: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Interview ─────────────────────────────────────────────────────────────────

class InterviewMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: Optional[str] = None


class InterviewMessageResponse(BaseModel):
    session_id: str
    response: str
    task_id: Optional[str] = None


# ── Task status ───────────────────────────────────────────────────────────────

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str   # queued | in_progress | complete | failed
    result: Optional[dict] = None
    error: Optional[str] = None


# ── Admin ─────────────────────────────────────────────────────────────────────

class AdminStudentResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    last_active_at: datetime

    class Config:
        from_attributes = True
