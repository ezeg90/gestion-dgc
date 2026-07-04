from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date, datetime
from uuid import UUID
from app.modules.gastos.model import (
    TipoComprobanteGasto, CategoriaGasto, FormaPagoGasto, EstadoGasto
)


class GastoCreate(BaseModel):
    fecha:              date
    proveedor_id:       Optional[UUID] = None
    tipo_comprobante:   TipoComprobanteGasto = TipoComprobanteGasto.factura_a
    numero_comprobante: Optional[str] = None
    concepto:           str
    categoria:          CategoriaGasto = CategoriaGasto.otros
    monto:              float
    forma_pago:         FormaPagoGasto = FormaPagoGasto.transferencia
    cheque_id:          Optional[UUID] = None
    observaciones:      Optional[str] = None

    @field_validator("monto")
    @classmethod
    def monto_positivo(cls, v):
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return round(v, 2)

    @field_validator("cheque_id")
    @classmethod
    def cheque_requerido_si_pago_cheque(cls, v, info):
        if info.data.get("forma_pago") == FormaPagoGasto.cheque and not v:
            raise ValueError("cheque_id es obligatorio cuando forma_pago es 'cheque'")
        return v

    @field_validator("proveedor_id")
    @classmethod
    def proveedor_requerido_si_cc(cls, v, info):
        if info.data.get("forma_pago") == FormaPagoGasto.cuenta_corriente_proveedor and not v:
            raise ValueError("proveedor_id es obligatorio cuando forma_pago es 'cuenta_corriente_proveedor'")
        return v


class GastoUpdate(BaseModel):
    fecha:              Optional[date] = None
    proveedor_id:       Optional[UUID] = None
    tipo_comprobante:   Optional[TipoComprobanteGasto] = None
    numero_comprobante: Optional[str] = None
    concepto:           Optional[str] = None
    categoria:          Optional[CategoriaGasto] = None
    monto:              Optional[float] = None
    forma_pago:         Optional[FormaPagoGasto] = None
    cheque_id:          Optional[UUID] = None
    estado:             Optional[EstadoGasto] = None
    observaciones:      Optional[str] = None


class GastoResponse(BaseModel):
    id:                 UUID
    fecha:              date
    proveedor_id:       Optional[UUID]
    proveedor_nombre:   Optional[str] = None   # join
    tipo_comprobante:   TipoComprobanteGasto
    numero_comprobante: Optional[str]
    concepto:           str
    categoria:          CategoriaGasto
    monto:              float
    forma_pago:         FormaPagoGasto
    cheque_id:          Optional[UUID]
    cheque_numero:      Optional[str] = None   # join
    estado:             EstadoGasto
    observaciones:      Optional[str]
    created_at:         datetime

    model_config = {"from_attributes": True}


class ResumenGastos(BaseModel):
    total_mes:          float
    total_año:          float
    por_categoria:      dict
    por_forma_pago:     dict
    cantidad_pendientes: int
    monto_pendientes:   float
