import uuid
from sqlalchemy import Column, String, DateTime, Date, Integer, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Ruta(Base):
    __tablename__ = "rutas"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre     = Column(String(150), nullable=False)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    fecha      = Column(Date, nullable=False)
    estado     = Column(String(30), nullable=False, default="planificada")
    # estados: planificada | en_curso | completada | cancelada
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    usuario = relationship("Usuario")
    pedidos = relationship("Pedido", back_populates="ruta")
    paradas = relationship("RutaParada", back_populates="ruta", cascade="all, delete-orphan")


class RutaParada(Base):
    __tablename__ = "ruta_paradas"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ruta_id     = Column(UUID(as_uuid=True), ForeignKey("rutas.id", ondelete="CASCADE"), nullable=False)
    cliente_id  = Column(UUID(as_uuid=True), ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False)
    pedido_id   = Column(UUID(as_uuid=True), ForeignKey("pedidos.id", ondelete="SET NULL"), nullable=True)
    orden       = Column(Integer, nullable=False)
    estado      = Column(String(30), nullable=False, default="pendiente")
    # estados: pendiente | visitado | no_visitado
    llegada     = Column(DateTime(timezone=True), nullable=True)
    observacion = Column(Text, nullable=True)

    ruta    = relationship("Ruta", back_populates="paradas")
    cliente = relationship("Cliente")
    pedido  = relationship("Pedido")

    __table_args__ = (
        UniqueConstraint("ruta_id", "orden", name="uq_ruta_orden"),
    )