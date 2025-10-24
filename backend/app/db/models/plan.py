from sqlalchemy import Integer, String, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base_class import Base

class Plan(Base):
    __tablename__ = "planes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    max_equipos: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 = ilimitado
    precio: Mapped[float] = mapped_column(Numeric(10,2), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(200))
