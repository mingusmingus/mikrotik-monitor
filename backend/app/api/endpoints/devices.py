from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.db.models import Device, User, Plan
from app.schemas.device import DeviceCreate, DeviceOut
from app.core.security import encrypt_secret, decrypt_secret

router = APIRouter()

def _check_plan_limit(db: Session, user: User):
    plan = db.get(Plan, user.plan_id) if user.plan_id else None
    if not plan:
        return
    if plan.max_equipos == 0:
        return
    count = db.query(func.count(Device.id)).filter(Device.usuario_id == user.id).scalar()
    if count >= plan.max_equipos:
        raise HTTPException(status_code=403, detail="Límite de equipos alcanzado para tu plan")

@router.post("/", response_model=DeviceOut)
def create_device(payload: DeviceCreate, authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Falta token")
    token = authorization.split(" ", 1)[1]
    user = get_current_user(token, db)

    _check_plan_limit(db, user)

    dev = Device(
        usuario_id=user.id,
        nombre=payload.nombre,
        ip=str(payload.ip),
        puerto=payload.puerto,
        usuario_mk_enc=encrypt_secret(payload.usuario_mk),
        password_mk_enc=encrypt_secret(payload.password_mk),
        activo=True
    )
    db.add(dev)
    db.commit()
    db.refresh(dev)
    return dev

@router.get("/", response_model=list[DeviceOut])
def list_devices(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Falta token")
    token = authorization.split(" ", 1)[1]
    user = get_current_user(token, db)
    items = db.query(Device).filter(Device.usuario_id == user.id).order_by(Device.id.desc()).all()
    return [DeviceOut.model_validate(i) for i in items]

@router.delete("/{device_id}")
def delete_device(device_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Falta token")
    token = authorization.split(" ", 1)[1]
    user = get_current_user(token, db)
    dev = db.query(Device).filter(Device.id == device_id, Device.usuario_id == user.id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    db.delete(dev)
    db.commit()
    return {"ok": True}
