import uuid
from sqlalchemy import Column, String, Numeric, Date, Text, Enum as SAEnum, TIMESTAMP, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class TipoComprobanteGasto(str, enum.Enum):
    factura_a = "factura_a"
    factura_b = "factura_b"
    factura_c = "factura_c"
    ticket    = "ticket"
    remito    = "remito"
    otro      = "otro"


class CategoriaGasto(str, enum.Enum):
    materias_primas = "materias_primas"
    servicios       = "servicios"
    fletes          = "fletes"
    impuestos       = "impuestos"
    mantenimiento   = "mantenimiento"
    otros           = "otros"


class FormaPagoGasto(str, enum.Enum):
    efectivo                    = "efectivo"
    transferencia               = "transferencia"
    cheque                      = "cheque"
    cuenta_corriente_proveedor  = "cuenta_corriente_proveedor"


class EstadoGasto(str, enum.Enum):
    pendiente = "pendiente"
    pagado    = "pagado"
    anulado   = "anulado"


class Gasto(Base):
    __tablename__ = "gastos"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fecha              = Column(Date, nullable=False)
    proveedor_id       = Column(UUID(as_uuid=True), ForeignKey("proveedores.id", ondelete="SET NULL"), nullable=True)
    tipo_comprobante   = Column(SAEnum(TipoComprobanteGasto, name="tipo_comprobante_gasto"),
                                nullable=False, default=TipoComprobanteGasto.factura_a)
    numero_comprobante = Column(String(50), nullable=True)
    concepto           = Column(Text, nullable=False)
    categoria          = Column(SAEnum(CategoriaGasto, name="categoria_gasto"),
                                nullable=False, default=CategoriaGasto.otros)
    monto              = Column(Numeric(14, 2), nullable=False)
    forma_pago         = Column(SAEnum(FormaPagoGasto, name="forma_pago_gasto"),
                                nullable=False, default=FormaPagoGasto.transferencia)
    cheque_id          = Column(UUID(as_uuid=True), ForeignKey("cheques_emitidos.id", ondelete="SET NULL"), nullable=True)
    estado             = Column(SAEnum(EstadoGasto, name="estado_gasto"),
                                nullable=False, default=EstadoGasto.pendiente)
    observaciones      = Column(Text, nullable=True)
    created_at         = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at         = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    proveedor = relationship("Proveedor", back_populates="gastos")
