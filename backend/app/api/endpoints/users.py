from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.schemas.user import UserOut

router = APIRouter()

@router.get("/me", response_model=UserOut)
def me(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Falta token")
    token = authorization.split(" ", 1)[1]
    user = get_current_user(token, db)
    return UserOut.model_validate(user)
