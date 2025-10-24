from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import func
from app.db.session import get_db
from app.core.security import vault, get_current_user
from app.schemas.device import DeviceCreate, DeviceUpdate, DeviceOut
from app.db.models import Device, User, Plan

router = APIRouter()

def check_plan_limit(db: Session, user_id: int):
    """Verifica límite de dispositivos según el plan del usuario"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.plan_id:
        raise HTTPException(status_code=400, detail="Usuario sin plan asignado")
    
    plan = db.query(Plan).filter(Plan.id == user.plan_id).first()
    if not plan:
        raise HTTPException(status_code=400, detail="Plan no encontrado")
        
    if plan.max_equipos > 0:  # 0 = ilimitado
        current_count = db.query(Device).filter(
            Device.usuario_id == user_id
        ).count()
        if current_count >= plan.max_equipos:
            raise HTTPException(
                status_code=403, 
                detail=f"Límite de {plan.max_equipos} dispositivos alcanzado"
            )

@router.get("/", response_model=List[DeviceOut])
async def list_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Device).filter(Device.usuario_id == current_user.id).all()

@router.post("/", response_model=DeviceOut)
async def create_device(
    device: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_plan_limit(db, current_user.id)
    
    db_device = Device(
        usuario_id=current_user.id,
        nombre=device.nombre,
        ip=str(device.ip),
        puerto=device.puerto,
        usuario_mk_enc=vault.encrypt(device.usuario_mk),
        password_mk_enc=vault.encrypt(device.password_mk)
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

@router.get("/{device_id}", response_model=DeviceOut)
async def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.usuario_id == current_user.id
    ).first()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    return device

@router.delete("/{device_id}")
async def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.usuario_id == current_user.id
    ).first()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    db.delete(device)
    db.commit()
    return {"ok": True}
