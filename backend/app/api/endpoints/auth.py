from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import User, Plan
from app.schemas.user import UserCreate, UserLogin, UserOut
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.config import settings

router = APIRouter()

@router.post("/register", response_model=UserOut)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email ya registrado")
    u = User(
        email=payload.email,
        password=hash_password(payload.password),
        nombre=payload.nombre,
        plan_id=payload.plan_id,
        activo=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u

@router.post("/login")
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email, User.activo == True).first()
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    return {
        "access_token": create_access_token(user.email),
        "refresh_token": create_refresh_token(user.email),
        "token_type": "bearer",
        "user": UserOut.model_validate(user)
    }

@router.post("/refresh")
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    # (por simplicidad) reusa decode en dependencies si deseas
    from app.core.security import decode_token
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError()
        email = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")
    return {"access_token": create_access_token(email), "token_type": "bearer"}
