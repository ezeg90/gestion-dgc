import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Categoria(Base):
    __tablename__ = "categorias"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre     = Column(String(100), nullable=False)
    padre_id   = Column(UUID(as_uuid=True), ForeignKey("categorias.id", ondelete="CASCADE"), nullable=True)
    tipo       = Column(String(20), nullable=True)  # producto | servicio | NULL (aplica a ambos)
    activo     = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    padre = relationship("Categoria", remote_side=[id], back_populates="hijas")
    hijas = relationship(
        "Categoria",
        back_populates="padre",
        cascade="all, delete-orphan",
        order_by="Categoria.nombre",
    )

    __table_args__ = (
        UniqueConstraint("nombre", "padre_id", name="uq_categoria_nombre_padre"),
        CheckConstraint("tipo IS NULL OR tipo IN ('producto', 'servicio')", name="chk_categorias_tipo"),
    )