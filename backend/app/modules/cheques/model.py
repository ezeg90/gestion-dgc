import uuid
from datetime import date
from sqlalchemy import Column, String, Numeric, Date, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
import enum


class EstadoChequeEmitido(str, enum.Enum):
    emitido = "emitido"
    en_transito = "en_transito"
    debitado = "debitado"
    rechazado = "rechazado"
    anulado = "anulado"


class ChequeEmitido(Base):
    __tablename__ = "cheques_emitidos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero = Column(String(50), nullable=False)
    banco = Column(String(100), nullable=False)
    sucursal = Column(String(100), nullable=True)
    beneficiario = Column(String(200), nullable=False)
    monto = Column(Numeric(12, 2), nullable=False)
    fecha_emision = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    concepto = Column(Text, nullable=True)
    estado = Column(
        SAEnum(EstadoChequeEmitido, name="estado_cheque_emitido"),
        nullable=False,
        default=EstadoChequeEmitido.emitido,
    )
    observaciones = Column(Text, nullable=True)