import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    razon_social     = Column(String(200), nullable=False)
    cuit             = Column(String(20))
    condicion_iva    = Column(String(50), nullable=False, default="consumidor_final")
    telefono         = Column(String(50))
    email            = Column(String(255))
    direccion        = Column(String(300))
    localidad        = Column(String(150))
    latitud          = Column(Numeric(10, 8))
    longitud         = Column(Numeric(11, 8))
    estado           = Column(String(30), nullable=False, default="activo")
    lista_precios_id = Column(UUID(as_uuid=True), ForeignKey("listas_precios.id"), nullable=True)
    created_by       = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    lista_precios    = relationship("ListaPrecios", back_populates="clientes")

