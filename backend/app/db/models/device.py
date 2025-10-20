from sqlalchemy import Integer, String, Boolean, SmallInteger, ForeignKey
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Device(Base):
    __tablename__ = "equipos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    ip: Mapped[str] = mapped_column(INET, nullable=False)
    puerto: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=8728)
    usuario_mk_enc: Mapped[str] = mapped_column(String(255), nullable=False)   # encrypted
    password_mk_enc: Mapped[str] = mapped_column(String(255), nullable=False)  # encrypted
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    usuario = relationship("User", back_populates="equipos")
    alertas = relationship("Alert", back_populates="equipo", cascade="all,delete")

    __table_args__ = (
        # Evita duplicados por usuario/ip/puerto
        # Nota: en Alembic crearemos el índice único.
    )
