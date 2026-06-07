import uuid
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CuentaCorriente(Base):
    __tablename__ = "cuentas_corrientes"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id      = Column(UUID(as_uuid=True), ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False, unique=True)
    saldo_actual    = Column(Numeric(12, 2), nullable=False, default=0)
    limite_credito  = Column(Numeric(12, 2), nullable=False, default=0)
    estado          = Column(String(30), nullable=False, default="activa")
    # activa | suspendida | bloqueada
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    cliente         = relationship("Cliente", back_populates="cuenta_corriente")
    movimientos     = relationship("MovimientoCuentaCorriente", back_populates="cuenta", cascade="all, delete-orphan")


class MovimientoCuentaCorriente(Base):
    __tablename__ = "movimientos_cta_cte"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cuenta_corriente_id = Column(UUID(as_uuid=True), ForeignKey("cuentas_corrientes.id", ondelete="RESTRICT"), nullable=False)
    tipo                = Column(String(10), nullable=False)
    # debito = cliente debe más | credito = cliente paga
    monto               = Column(Numeric(12, 2), nullable=False)
    referencia_tipo     = Column(String(50), nullable=True)
    # remito | cobro | ajuste_manual
    referencia_id       = Column(UUID(as_uuid=True), nullable=True)
    descripcion         = Column(Text, nullable=True)
    fecha               = Column(DateTime(timezone=True), server_default=func.now())
    usuario_id          = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)

    cuenta   = relationship("CuentaCorriente", back_populates="movimientos")
    usuario  = relationship("Usuario")
