from pydantic import BaseModel, Field, IPvAnyAddress, field_validator

class DeviceCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    ip: IPvAnyAddress
    puerto: int = Field(8728, ge=1, le=65535)
    usuario_mk: str = Field(..., min_length=1, max_length=50)
    password_mk: str = Field(..., min_length=1, max_length=255)

class DeviceOut(BaseModel):
    id: int
    nombre: str
    ip: str
    puerto: int
    activo: bool
    class Config:
        from_attributes = True
