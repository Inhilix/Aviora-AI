import hashlib
import mimetypes
import os
from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import Document
from app.schemas.schemas import DocumentResponse
from app.security.jwt import get_current_student_id
from app.security.rate_limit import limiter
from app.config import settings
from app.services.document_blur import (
    create_blurred_preview,
    has_blurred_preview,
    is_image_filename,
    is_sensitive_doc_type,
    blurred_preview_path,
)

router = APIRouter()

ALLOWED_DOC_TYPES = {"transcript", "ielts", "passport", "sop", "lor", "financial", "other"}
MAX_FILE_SIZE_MB = 10


def _enrich(doc: Document) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        doc_type=doc.doc_type,
        file_name=doc.file_name,
        file_size_bytes=doc.file_size_bytes,
        uploaded_at=doc.uploaded_at,
        expires_at=doc.expires_at,
        is_sensitive=is_sensitive_doc_type(doc.doc_type),
        has_blurred_preview=has_blurred_preview(doc.file_path),
        is_image=is_image_filename(doc.file_name),
    )


async def _owned_document(
    doc_id: UUID,
    student_id: str,
    db: AsyncSession,
) -> Document:
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.student_id == student_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


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

    # Sensitive image uploads get a blurred sibling used for default previews.
    if is_sensitive_doc_type(doc_type) and is_image_filename(file.filename):
        create_blurred_preview(content, dest_path)

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
    return _enrich(doc)


@router.get("/", response_model=List[DocumentResponse])
@limiter.limit("60/minute")
async def list_documents(
    request: Request,
    student_id: str = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.student_id == student_id))
    return [_enrich(doc) for doc in result.scalars().all()]


@router.get("/{doc_id}/preview")
@limiter.limit("60/minute")
async def preview_document(
    request: Request,
    doc_id: UUID,
    reveal: bool = Query(False, description="If true, return the clear original (owner only)"),
    student_id: str = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Serve a document preview. Sensitive image docs default to the blurred copy
    so screen-share / shoulder-surfing does not expose passport or bank details.
    Pass reveal=true to fetch the clear original.
    """
    doc = await _owned_document(doc_id, student_id, db)

    if not os.path.isfile(doc.file_path):
        raise HTTPException(status_code=404, detail="File missing on storage")

    if not is_image_filename(doc.file_name):
        raise HTTPException(
            status_code=415,
            detail="Preview only available for image documents (jpg, png, webp, …)",
        )

    use_blur = is_sensitive_doc_type(doc.doc_type) and not reveal
    if use_blur:
        blur_path = blurred_preview_path(doc.file_path)
        if not os.path.isfile(blur_path):
            # Regenerate if missing (e.g. older uploads before blur support).
            with open(doc.file_path, "rb") as f:
                content = f.read()
            created = create_blurred_preview(content, doc.file_path)
            if not created:
                raise HTTPException(status_code=422, detail="Could not create blurred preview")
            blur_path = created
        return FileResponse(blur_path, media_type="image/jpeg", filename=f"blurred_{doc.file_name}")

    media_type = mimetypes.guess_type(doc.file_name)[0] or "application/octet-stream"
    return FileResponse(doc.file_path, media_type=media_type, filename=doc.file_name)


@router.get("/{doc_id}/download")
@limiter.limit("30/minute")
async def download_document(
    request: Request,
    doc_id: UUID,
    student_id: str = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
):
    """Download the original (unblurred) file — authenticated owner only."""
    doc = await _owned_document(doc_id, student_id, db)
    if not os.path.isfile(doc.file_path):
        raise HTTPException(status_code=404, detail="File missing on storage")
    media_type = mimetypes.guess_type(doc.file_name)[0] or "application/octet-stream"
    return FileResponse(doc.file_path, media_type=media_type, filename=doc.file_name)
