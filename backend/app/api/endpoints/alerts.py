from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.core.security import get_current_user
from app.schemas.alert import AlertCreate, AlertOut
from app.db.models import Alert, Device, User

router = APIRouter()

@router.get("/", response_model=List[AlertOut])
async def list_alerts(
    status: str | None = Query(None, regex="^(Aviso|Alerta Menor|Alerta Severa|Alerta Crítica)$"),
    limit: int = Query(10, ge=1, le=20),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Alert).join(Device).filter(Device.usuario_id == current_user.id)
    
    if status:
        query = query.filter(Alert.estado == status)
    
    return query.order_by(Alert.fecha.desc()).offset(offset).limit(limit).all()

@router.post("/", response_model=AlertOut)
async def create_alert(
    alert: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar que el dispositivo pertenece al usuario
    device = db.query(Device).filter(
        Device.id == alert.equipo_id,
        Device.usuario_id == current_user.id
    ).first()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    db_alert = Alert(**alert.model_dump())
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert
