import uuid
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Producto(Base):
    __tablename__ = "productos"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre        = Column(String(200), nullable=False)
    descripcion   = Column(String, nullable=True)
    unidad_medida = Column(String(30), nullable=False, default="unidad")
    categoria     = Column(String(100), nullable=True)   # ej: carnicos, repuestos, servicios
    subcategoria  = Column(String(100), nullable=True)   # ej: cortes_vaca, embutidos, fiambres
    activo        = Column(Boolean, nullable=False, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    precios = relationship("ListaPreciosItem", back_populates="producto")
