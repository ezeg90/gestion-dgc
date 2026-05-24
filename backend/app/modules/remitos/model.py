import uuid
from sqlalchemy import Column, String, DateTime, Date, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Remito(Base):
    __tablename__ = "remitos"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero        = Column(String(30), nullable=False, unique=True)
    cliente_id    = Column(UUID(as_uuid=True), ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False)
    usuario_id    = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    fecha         = Column(Date, nullable=False, server_default=func.current_date())
    estado        = Column(String(30), nullable=False, default="emitido")
    # estados: borrador | emitido | anulado
    observaciones = Column(Text, nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    cliente        = relationship("Cliente")
    usuario        = relationship("Usuario")
    remito_pedidos = relationship("RemitoPedido", back_populates="remito", cascade="all, delete-orphan")


class RemitoPedido(Base):
    __tablename__ = "remito_pedidos"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    remito_id = Column(UUID(as_uuid=True), ForeignKey("remitos.id", ondelete="CASCADE"), nullable=False)
    pedido_id = Column(UUID(as_uuid=True), ForeignKey("pedidos.id", ondelete="RESTRICT"), nullable=False)

    remito = relationship("Remito", back_populates="remito_pedidos")
    pedido = relationship("Pedido")

    __table_args__ = (
        UniqueConstraint("remito_id", "pedido_id", name="uq_remito_pedido"),
    )
