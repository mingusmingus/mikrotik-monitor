from pydantic import BaseModel

class PlanBase(BaseModel):
    nombre: str
    max_equipos: int
    precio: float
    descripcion: str | None = None

class PlanOut(PlanBase):
    id: int
    class Config:
        from_attributes = True
