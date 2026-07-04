from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.modules.proveedores.model import (
    CondicionIvaProveedor, EstadoProveedor, EstadoCCProveedor, TipoMovimientoProveedor
)


# ── Proveedor ─────────────────────────────────────────────────

class ProveedorCreate(BaseModel):
    nombre:        str
    cuit:          Optional[str] = None
    telefono:      Optional[str] = None
    email:         Optional[str] = None
    direccion:     Optional[str] = None
    localidad:     Optional[str] = None
    condicion_iva: CondicionIvaProveedor = CondicionIvaProveedor.responsable_inscripto
    rubro:         Optional[str] = None
    cbu:           Optional[str] = None
    alias:         Optional[str] = None
    banco:         Optional[str] = None
    contacto:      Optional[str] = None
    observaciones: Optional[str] = None


class ProveedorUpdate(BaseModel):
    nombre:        Optional[str] = None
    cuit:          Optional[str] = None
    telefono:      Optional[str] = None
    email:         Optional[str] = None
    direccion:     Optional[str] = None
    localidad:     Optional[str] = None
    condicion_iva: Optional[CondicionIvaProveedor] = None
    rubro:         Optional[str] = None
    cbu:           Optional[str] = None
    alias:         Optional[str] = None
    banco:         Optional[str] = None
    contacto:      Optional[str] = None
    estado:        Optional[EstadoProveedor] = None
    observaciones: Optional[str] = None


class ProveedorResponse(BaseModel):
    id:            UUID
    nombre:        str
    cuit:          Optional[str]
    telefono:      Optional[str]
    email:         Optional[str]
    direccion:     Optional[str]
    localidad:     Optional[str]
    condicion_iva: CondicionIvaProveedor
    rubro:         Optional[str]
    cbu:           Optional[str]
    alias:         Optional[str]
    banco:         Optional[str]
    contacto:      Optional[str]
    estado:        EstadoProveedor
    observaciones: Optional[str]
    saldo_cc:      Optional[float] = None   # viene join con CC

    model_config = {"from_attributes": True}


# ── Cuenta Corriente Proveedor ────────────────────────────────

class CCProveedorResponse(BaseModel):
    id:             UUID
    proveedor_id:   UUID
    proveedor_nombre: Optional[str] = None
    saldo_actual:   float
    limite_credito: float
    estado:         EstadoCCProveedor
    updated_at:     datetime

    model_config = {"from_attributes": True}


# ── Movimientos CC Proveedor ──────────────────────────────────

class MovimientoCCProveedorResponse(BaseModel):
    id:                  UUID
    cuenta_id:           UUID
    tipo:                TipoMovimientoProveedor
    monto:               float
    descripcion:         Optional[str]
    referencia_gasto_id: Optional[UUID]
    fecha:               datetime

    model_config = {"from_attributes": True}


class PagoProveedorRequest(BaseModel):
    monto:       float
    descripcion: Optional[str] = None

    @field_validator("monto")
    @classmethod
    def monto_positivo(cls, v):
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return round(v, 2)


class AjusteManualCCProveedor(BaseModel):
    tipo:        TipoMovimientoProveedor
    monto:       float
    descripcion: str

    @field_validator("monto")
    @classmethod
    def monto_positivo(cls, v):
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return round(v, 2)
