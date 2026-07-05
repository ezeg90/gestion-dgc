import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Producto(Base):
    __tablename__ = "productos"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre        = Column(String(200), nullable=False)
    descripcion   = Column(String, nullable=True)
    tipo          = Column(String(20), nullable=False, default="producto")  # producto | servicio
    unidad_medida = Column(String(30), nullable=False, default="unidad")
    categoria_id  = Column(UUID(as_uuid=True), ForeignKey("categorias.id", ondelete="SET NULL"), nullable=True)
    # categoria / subcategoria (texto libre) quedan en la tabla como respaldo histórico,
    # ya no se leen ni se escriben desde acá — reemplazadas por categoria_id
    activo        = Column(Boolean, nullable=False, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    precios       = relationship("ListaPreciosItem", back_populates="producto")
    categoria_rel = relationship("Categoria")

    __table_args__ = (
        CheckConstraint("tipo IN ('producto', 'servicio')", name="chk_productos_tipo"),
    )