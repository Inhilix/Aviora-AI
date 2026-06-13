import hashlib
import os
from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models import Document
from app.schemas.schemas import DocumentResponse
from app.security.jwt import get_current_student_id
from app.security.rate_limit import limiter
from app.config import settings

router = APIRouter()

ALLOWED_DOC_TYPES = {"transcript", "ielts", "passport", "sop", "lor", "financial", "other"}
MAX_FILE_SIZE_MB = 10


@router.get("/checklist")
@limiter.limit("60/minute")
async def get_checklist(
    request: Request,
    country: str = "UK",
    degree: str = "MSc",
    student_id: str = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
):
    """Config-driven document checklist per country + degree."""
    base = ["transcript", "passport", "financial"]
    if country in ("UK", "Australia", "Canada", "USA", "Germany"):
        base += ["ielts"]
    if degree in ("MSc", "MBA", "PhD"):
        base += ["sop", "lor"]

    # Check which docs the student has uploaded
    result = await db.execute(select(Document).where(Document.student_id == student_id))
    uploaded = {doc.doc_type for doc in result.scalars().all()}

    return {
        "required": base,
        "uploaded": list(uploaded),
        "missing": [d for d in base if d not in uploaded],
    }


@router.post("/upload", response_model=DocumentResponse, status_code=201)
@limiter.limit("20/minute")
async def upload_document(
    request: Request,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    student_id: str = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
):
    if doc_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid doc_type. Allowed: {ALLOWED_DOC_TYPES}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_FILE_SIZE_MB}MB limit")

    checksum = hashlib.sha256(content).hexdigest()
    dest_dir = os.path.join(settings.nas_mount_path, "documents", student_id)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, f"{doc_type}_{checksum[:8]}_{file.filename}")

    with open(dest_path, "wb") as f:
        f.write(content)

    doc = Document(
        student_id=student_id,
        doc_type=doc_type,
        file_path=dest_path,
        file_name=file.filename,
        file_size_bytes=len(content),
        checksum_sha256=checksum,
    )
    db.add(doc)
    await db.flush()
    return doc


@router.get("/", response_model=List[DocumentResponse])
@limiter.limit("60/minute")
async def list_documents(
    request: Request,
    student_id: str = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.student_id == student_id))
    return result.scalars().all()
