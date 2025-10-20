from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.db.models import Alert, Device
from app.schemas.alert import AlertCreate, AlertOut

router = APIRouter()

@router.get("/", response_model=list[AlertOut])
def list_alerts(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
    device_id: int | None = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    estado: str | None = Query(None, pattern="^(Aviso|Alerta Menor|Alerta Severa|Alerta Crítica)$")
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Falta token")
    token = authorization.split(" ", 1)[1]
    user = get_current_user(token, db)

    q = db.query(Alert).join(Device, Alert.equipo_id == Device.id).filter(Device.usuario_id == user.id)
    if device_id:
        q = q.filter(Alert.equipo_id == device_id)
    if estado:
        q = q.filter(Alert.estado == estado)
    q = q.order_by(Alert.fecha.desc()).limit(limit).offset(offset)
    items = q.all()
    return [AlertOut.model_validate(i) for i in items]

@router.post("/", response_model=AlertOut)
def create_alert(payload: AlertCreate, authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Falta token")
    token = authorization.split(" ", 1)[1]
    user = get_current_user(token, db)
    dev = db.query(Device).filter(Device.id == payload.equipo_id, Device.usuario_id == user.id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Equipo no pertenece al usuario")
    a = Alert(
        equipo_id=payload.equipo_id,
        estado=payload.estado,
        titulo=payload.titulo,
        descripcion=payload.descripcion
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a
