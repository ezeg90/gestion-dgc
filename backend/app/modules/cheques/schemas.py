from pydantic import BaseModel, condecimal
from typing import Optional
from datetime import date
from uuid import UUID
from app.modules.cheques.model import EstadoChequeEmitido


class ChequeEmitidoCreate(BaseModel):
    numero: str
    banco: str
    sucursal: Optional[str] = None
    beneficiario: str
    monto: condecimal(max_digits=12, decimal_places=2)
    fecha_emision: date
    fecha_vencimiento: date
    concepto: Optional[str] = None
    observaciones: Optional[str] = None


class ChequeEmitidoUpdate(BaseModel):
    numero: Optional[str] = None
    banco: Optional[str] = None
    sucursal: Optional[str] = None
    beneficiario: Optional[str] = None
    monto: Optional[condecimal(max_digits=12, decimal_places=2)] = None
    fecha_emision: Optional[date] = None
    fecha_vencimiento: Optional[date] = None
    concepto: Optional[str] = None
    estado: Optional[EstadoChequeEmitido] = None
    observaciones: Optional[str] = None


class ChequeEmitidoResponse(BaseModel):
    id: UUID
    numero: str
    banco: str
    sucursal: Optional[str]
    beneficiario: str
    monto: float
    fecha_emision: date
    fecha_vencimiento: date
    concepto: Optional[str]
    estado: EstadoChequeEmitido
    observaciones: Optional[str]
    dias_para_vencer: Optional[int] = None  # calculado, no persistido

    model_config = {"from_attributes": True}


class CambioEstadoCheque(BaseModel):
    estado: EstadoChequeEmitido
    observaciones: Optional[str] = None