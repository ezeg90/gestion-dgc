import uuid
from datetime import date, timedelta
from sqlalchemy import Column, String, Numeric, Date, Text, Enum as SAEnum, event
from sqlalchemy.orm import validates
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
import enum


class EstadoChequeEmitido(str, enum.Enum):
    emitido              = "emitido"
    en_transito          = "en_transito"
    en_ventana           = "en_ventana"           # vencimiento pasado, aún no debitado
    debitado             = "debitado"
    rechazado            = "rechazado"
    vencido_sin_depositar = "vencido_sin_depositar"  # venció la ventana de 30d
    anulado              = "anulado"


class ChequeEmitido(Base):
    __tablename__ = "cheques_emitidos"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero                = Column(String(50),  nullable=False)
    banco                 = Column(String(100), nullable=False)
    sucursal              = Column(String(100), nullable=True)
    beneficiario          = Column(String(200), nullable=False)
    monto                 = Column(Numeric(12, 2), nullable=False)
    fecha_emision         = Column(Date, nullable=False)
    fecha_vencimiento     = Column(Date, nullable=False)
    fecha_limite_deposito = Column(Date, nullable=False)   # fecha_vencimiento + 30d
    concepto              = Column(Text, nullable=True)
    estado                = Column(
        SAEnum(EstadoChequeEmitido, name="estado_cheque_emitido"),
        nullable=False,
        default=EstadoChequeEmitido.emitido,
    )
    observaciones         = Column(Text, nullable=True)

    @validates("fecha_vencimiento")
    def set_fecha_limite(self, key, value):
        """Auto-calcula fecha_limite_deposito cuando se setea fecha_vencimiento."""
        if value:
            if isinstance(value, str):
                from datetime import date as dt
                value = dt.fromisoformat(value)
            self.fecha_limite_deposito = value + timedelta(days=30)
        return value
