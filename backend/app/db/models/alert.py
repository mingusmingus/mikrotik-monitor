from sqlalchemy import Integer, String, Text, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

# Estados: 'Aviso','Alerta Menor','Alerta Severa','Alerta Crítica'
class Alert(Base):
    __tablename__ = "alertas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equipo_id: Mapped[int] = mapped_column(ForeignKey("equipos.id", ondelete="CASCADE"), index=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    titulo: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha: Mapped[str] = mapped_column(TIMESTAMP, server_default=func.now())

    equipo = relationship("Device", back_populates="alertas")
