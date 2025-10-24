from sqlalchemy import Integer, String, Text, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class Alert(Base):
    __tablename__ = "alertas"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equipo_id: Mapped[int] = mapped_column(ForeignKey("equipos.id", ondelete="CASCADE"))
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    titulo: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    fecha: Mapped[str] = mapped_column(TIMESTAMP, server_default=func.now())

    equipo = relationship("Device", back_populates="alertas")

class Device(Base):
    __tablename__ = "equipos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    ip: Mapped[str] = mapped_column(String(15), nullable=False)  # Usamos String en lugar de INET por compatibilidad
    puerto: Mapped[int] = mapped_column(SmallInteger, default=8728)
    usuario_mk_enc: Mapped[str] = mapped_column(String(255), nullable=False)
    password_mk_enc: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    usuario = relationship("User", back_populates="equipos")
    alertas = relationship("Alert", back_populates="equipo", cascade="all,delete")
