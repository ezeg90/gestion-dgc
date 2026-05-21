import uuid
from sqlalchemy import Column, String, DateTime, Date, Numeric, ForeignKey, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Pedido(Base):
    __tablename__ = "pedidos"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id    = Column(UUID(as_uuid=True), ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False)
    usuario_id    = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    ruta_id       = Column(UUID(as_uuid=True), ForeignKey("rutas.id", ondelete="SET NULL"), nullable=True)
    estado        = Column(String(30), nullable=False, default="pendiente")
    # estados: pendiente | en_ruta | entregado | cancelado | no_entregado
    fecha_pedido  = Column(Date, nullable=False, server_default=func.current_date())
    fecha_entrega = Column(Date, nullable=True)
    observaciones = Column(Text, nullable=True)
    total         = Column(Numeric(12, 2), nullable=False, default=0)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    cliente = relationship("Cliente", back_populates="pedidos")
    usuario = relationship("Usuario")
    ruta    = relationship("Ruta", back_populates="pedidos")
    items   = relationship("PedidoItem", back_populates="pedido", cascade="all, delete-orphan")


class PedidoItem(Base):
    __tablename__ = "pedido_items"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pedido_id       = Column(UUID(as_uuid=True), ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False)
    producto_id     = Column(UUID(as_uuid=True), ForeignKey("productos.id", ondelete="RESTRICT"), nullable=False)
    cantidad        = Column(Numeric(10, 3), nullable=False)
    precio_unitario = Column(Numeric(12, 2), nullable=False)
    # precio grabado al momento del pedido — no se recalcula aunque cambie la lista
    subtotal        = Column(Numeric(12, 2), nullable=False, default=0)
    observacion     = Column(Text, nullable=True)

    pedido   = relationship("Pedido", back_populates="items")
    producto = relationship("Producto")

    __table_args__ = (
        CheckConstraint("cantidad > 0", name="chk_cantidad_positiva"),
        CheckConstraint("precio_unitario >= 0", name="chk_precio_positivo"),
    )
