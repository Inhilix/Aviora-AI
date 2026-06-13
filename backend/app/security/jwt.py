from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException, Request
from app.config import settings

ALGORITHM = "RS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(student_id: str) -> str:
    payload = {
        "sub": student_id,
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.utcnow(),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_private_key, algorithm=ALGORITHM)


def create_refresh_token(student_id: str) -> str:
    payload = {
        "sub": student_id,
        "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.utcnow(),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_private_key, algorithm=ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_public_key, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_student_id(request: Request) -> str:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = verify_token(token, "access")
    student_id = payload.get("sub")
    if not student_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return student_id
