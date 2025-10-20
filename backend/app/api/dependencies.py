from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import JWTError
from app.db.session import get_db
from app.core.security import decode_token
from app.db.models import User

def get_db_dep():
    return next(get_db())

def get_current_user(token: str, db: Session) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("invalid token type")
        email = payload.get("sub")
        if not email:
            raise ValueError("missing sub")
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    user = db.query(User).filter(User.email == email, User.activo == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return user
