from uuid import UUID
from typing import Optional, List, Literal
from pydantic import BaseModel, model_validator
from decimal import Decimal
from datetime import date, datetime

EstadoPedido = Literal["pendiente", "en_ruta", "entregado", "cancelado", "no_entregado"]


# ── Items ────────────────────────────────────────────────────

class PedidoItemCreate(BaseModel):
    producto_id:     UUID
    cantidad:        Decimal
    precio_unitario: Optional[Decimal] = None
    # Si no se envía, se busca el precio de la lista del cliente


class PedidoItemOut(BaseModel):
    id:              UUID
    producto_id:     UUID
    cantidad:        Decimal
    precio_unitario: Decimal
    subtotal:        Decimal
    observacion:     Optional[str] = None

    class Config:
        from_attributes = True


# ── Pedido ───────────────────────────────────────────────────

class PedidoCreate(BaseModel):
    cliente_id:    UUID
    fecha_entrega: Optional[date] = None
    observaciones: Optional[str] = None
    items:         List[PedidoItemCreate]

    @model_validator(mode="after")
    def validar_items(self):
        if not self.items:
            raise ValueError("El pedido debe tener al menos un item")
        return self


class PedidoUpdate(BaseModel):
    estado:        Optional[EstadoPedido] = None
    fecha_entrega: Optional[date] = None
    observaciones: Optional[str] = None
    ruta_id:       Optional[UUID] = None


class PedidoOut(BaseModel):
    id:            UUID
    cliente_id:    UUID
    usuario_id:    Optional[UUID]
    ruta_id:       Optional[UUID]
    estado:        EstadoPedido
    fecha_pedido:  date
    fecha_entrega: Optional[date]
    observaciones: Optional[str]
    total:         Decimal
    items:         List[PedidoItemOut] = []
    created_at:    datetime

    class Config:
        from_attributes = True


class PedidoListOut(BaseModel):
    """Versión reducida para listados"""
    id:            UUID
    cliente_id:    UUID
    estado:        EstadoPedido
    fecha_pedido:  date
    fecha_entrega: Optional[date]
    total:         Decimal

    class Config:
        from_attributes = True
