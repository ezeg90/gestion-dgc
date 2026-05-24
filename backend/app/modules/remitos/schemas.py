from uuid import UUID
from typing import Optional, List, Literal
from pydantic import BaseModel
from decimal import Decimal
from datetime import date, datetime

EstadoRemito = Literal["borrador", "emitido", "anulado"]


class RemitoCreate(BaseModel):
    pedido_ids:    List[UUID]   # uno o más pedidos del mismo cliente
    observaciones: Optional[str] = None
    fecha:         Optional[date] = None


class RemitoUpdate(BaseModel):
    estado:        Optional[EstadoRemito] = None
    observaciones: Optional[str] = None


# ── Schemas para el PDF / vista detallada ────────────────────

class RemitoItemOut(BaseModel):
    """Un item consolidado de todos los pedidos del remito"""
    producto_nombre:  str
    producto_unidad:  str
    cantidad:         Decimal
    precio_unitario:  Decimal
    subtotal:         Decimal


class RemitoOut(BaseModel):
    id:            UUID
    numero:        str
    cliente_id:    UUID
    usuario_id:    Optional[UUID]
    fecha:         date
    estado:        EstadoRemito
    observaciones: Optional[str]
    created_at:    datetime
    pedido_ids:    List[UUID] = []

    class Config:
        from_attributes = True


class RemitoDetalleOut(BaseModel):
    """Respuesta completa con todos los datos para generar el PDF"""
    id:              UUID
    numero:          str
    fecha:           date
    estado:          EstadoRemito
    observaciones:   Optional[str]

    # Datos del cliente
    cliente_nombre:      str
    cliente_direccion:   Optional[str]
    cliente_localidad:   Optional[str]
    cliente_cuit:        Optional[str]
    cliente_condicion_iva: str

    # Datos del emisor (constantes del negocio)
    emisor_nombre:     str = "Don Gimenez - Fábrica de Chacinados"
    emisor_direccion:  str = "Independencia Norte 3644"
    emisor_localidad:  str = "San Francisco, Córdoba"
    emisor_cuit:       str = "27-26309348-3"
    emisor_telefono:   str = "3564-508470"

    # Items consolidados
    items:           List[RemitoItemOut]
    total:           Decimal
    forma_pago:      str

    # Referencias
    pedido_ids:      List[UUID]

    class Config:
        from_attributes = True
