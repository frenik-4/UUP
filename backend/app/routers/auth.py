from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from jose import jwt
import bcrypt as _bcrypt

from app.database import get_db
from app.config import settings
from app.models.core import Anvandare
from app.schemas.core import LoginIn, TokenOut, AnvandareOut

router = APIRouter(prefix="/auth", tags=["auth"])


def hash_pw(pw: str) -> str:
    return _bcrypt.hashpw(pw.encode(), _bcrypt.gensalt()).decode()


def verify_pw(pw: str, hashed: str) -> bool:
    return _bcrypt.checkpw(pw.encode(), hashed.encode())


def create_token(user_id: int) -> str:
    payload = {"sub": str(user_id), "exp": datetime.utcnow() + timedelta(days=7)}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def get_current_user(token: str, db: Session) -> Anvandare:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Ogiltig token")
    user = db.get(Anvandare, user_id)
    if not user or not user.aktiv:
        raise HTTPException(status_code=401, detail="Användaren finns inte")
    return user


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(Anvandare).filter(Anvandare.epost == body.epost).first()
    if not user or not verify_pw(body.losenord, user.losenord_hash):
        raise HTTPException(status_code=401, detail="Fel e-post eller lösenord")
    return TokenOut(
        access_token=create_token(user.id),
        anvandare=AnvandareOut.model_validate(user)
    )


@router.get("/me", response_model=AnvandareOut)
def me(token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    return AnvandareOut.model_validate(user)
