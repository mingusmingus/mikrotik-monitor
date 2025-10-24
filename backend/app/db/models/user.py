from sqlalchemy import Integer, String, Boolean, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class User(Base):
    __tablename__ = "usuarios"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False) 
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("planes.id"))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[str] = mapped_column(TIMESTAMP, server_default=func.now())
    
    plan = relationship("Plan")
    equipos = relationship("Device", back_populates="usuario", cascade="all,delete")
