from pydantic import BaseModel, Field
from datetime import datetime

ESTADOS = ("Aviso","Alerta Menor","Alerta Severa","Alerta Crítica")

class AlertCreate(BaseModel):
    equipo_id: int
    estado: str = Field(..., pattern="^(Aviso|Alerta Menor|Alerta Severa|Alerta Crítica)$")
    titulo: str
    descripcion: str | None = None

class AlertOut(BaseModel):
    id: int
    equipo_id: int
    estado: str
    titulo: str
    descripcion: str | None
    fecha: datetime
    class Config:
        from_attributes = True
