from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext

from app.database import get_db
from app.models import Student
from app.schemas.schemas import RegisterRequest, LoginRequest, TokenResponse
from app.security.jwt import (
    create_access_token, create_refresh_token, verify_token,
    ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.security.rate_limit import limiter

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

COOKIE_OPTS = dict(httponly=True, secure=True, samesite="strict")


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Student).where(Student.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    student = Student(
        email=body.email,
        password_hash=pwd_context.hash(body.password),
        full_name=body.full_name,
        phone=body.phone,
    )
    db.add(student)
    await db.flush()
    return {"id": str(student.id), "email": student.email}


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Student).where(Student.email == body.email))
    student = result.scalar_one_or_none()
    if not student or not pwd_context.verify(body.password, student.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not student.is_active:
        raise HTTPException(status_code=403, detail="Account inactive")

    access  = create_access_token(str(student.id))
    refresh = create_refresh_token(str(student.id))

    response = JSONResponse(content={"message": "Logged in"})
    response.set_cookie("access_token",  access,  max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60, **COOKIE_OPTS)
    response.set_cookie("refresh_token", refresh, max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400, **COOKIE_OPTS)
    return response


@router.post("/refresh")
async def refresh(request: Request):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    payload = verify_token(token, "refresh")
    access = create_access_token(payload["sub"])
    response = JSONResponse(content={"message": "Token refreshed"})
    response.set_cookie("access_token", access, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60, **COOKIE_OPTS)
    return response


@router.post("/logout")
async def logout(request: Request):
    response = JSONResponse(content={"message": "Logged out"})
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response
