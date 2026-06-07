from uuid import UUID
from typing import Optional, List, Literal
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime

EstadoCuenta = Literal["activa", "suspendida", "bloqueada"]
TipoMovimiento = Literal["debito", "credito"]
ReferenciaTipo = Literal["remito", "cobro", "ajuste_manual"]


class MovimientoOut(BaseModel):
    id:               UUID
    tipo:             TipoMovimiento
    monto:            Decimal
    referencia_tipo:  Optional[str]
    referencia_id:    Optional[UUID]
    descripcion:      Optional[str]
    fecha:            datetime

    class Config:
        from_attributes = True


class CuentaCorrienteOut(BaseModel):
    id:             UUID
    cliente_id:     UUID
    saldo_actual:   Decimal
    limite_credito: Decimal
    estado:         EstadoCuenta
    updated_at:     Optional[datetime]

    class Config:
        from_attributes = True


class CuentaResumenOut(BaseModel):
    """Vista enriquecida con datos del cliente"""
    id:                  UUID
    cliente_id:          UUID
    cliente_nombre:      str
    cliente_telefono:    Optional[str]
    cliente_localidad:   Optional[str]
    saldo_actual:        Decimal
    limite_credito:      Decimal
    estado:              EstadoCuenta
    ultimo_movimiento:   Optional[datetime]

    class Config:
        from_attributes = True


class RegistrarCobroRequest(BaseModel):
    monto:       Decimal
    descripcion: Optional[str] = None
    # referencia_id puede ser un cheque, transferencia, etc. — se expande en v2


class AjusteManualRequest(BaseModel):
    tipo:        TipoMovimiento
    monto:       Decimal
    descripcion: str


class ActualizarCuentaRequest(BaseModel):
    estado:          Optional[EstadoCuenta] = None
    limite_credito:  Optional[Decimal] = None
