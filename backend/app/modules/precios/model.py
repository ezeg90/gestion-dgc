import uuid
from sqlalchemy import Column, String, Boolean, Date, DateTime, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ListaPrecios(Base):
    __tablename__ = "listas_precios"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre         = Column(String(100), nullable=False)
    tipo           = Column(String(50), nullable=False, default="minorista")
    activo         = Column(Boolean, nullable=False, default=True)
    vigencia_desde = Column(Date, nullable=True)
    vigencia_hasta = Column(Date, nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    items    = relationship("ListaPreciosItem", back_populates="lista", cascade="all, delete-orphan")
    clientes = relationship("Cliente", back_populates="lista_precios")


class ListaPreciosItem(Base):
    __tablename__ = "lista_precios_items"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lista_precios_id = Column(UUID(as_uuid=True), ForeignKey("listas_precios.id", ondelete="CASCADE"), nullable=False)
    producto_id      = Column(UUID(as_uuid=True), ForeignKey("productos.id", ondelete="CASCADE"), nullable=False)
    precio           = Column(Numeric(12, 2), nullable=False)
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    lista    = relationship("ListaPrecios", back_populates="items")
    producto = relationship("Producto", back_populates="precios")

    __table_args__ = (
        UniqueConstraint("lista_precios_id", "producto_id", name="uq_lista_producto"),
    )
