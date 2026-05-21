from uuid import UUID
from typing import Optional, List, Literal
from pydantic import BaseModel
from decimal import Decimal
from datetime import date, datetime

TipoLista = Literal["minorista", "mayorista", "especial"]


class ListaPreciosBase(BaseModel):
    nombre:         str
    tipo:           TipoLista = "minorista"
    vigencia_desde: Optional[date] = None
    vigencia_hasta: Optional[date] = None


class ListaPreciosCreate(ListaPreciosBase):
    pass


class ListaPreciosUpdate(BaseModel):
    nombre:         Optional[str] = None
    tipo:           Optional[TipoLista] = None
    activo:         Optional[bool] = None
    vigencia_desde: Optional[date] = None
    vigencia_hasta: Optional[date] = None


class ItemPrecioOut(BaseModel):
    id:          UUID
    producto_id: UUID
    precio:      Decimal
    updated_at:  datetime

    class Config:
        from_attributes = True


class ListaPreciosOut(ListaPreciosBase):
    id:         UUID
    activo:     bool
    created_at: datetime
    items:      List[ItemPrecioOut] = []

    class Config:
        from_attributes = True


class ListaPreciosSimpleOut(BaseModel):
    id:     UUID
    nombre: str
    tipo:   TipoLista
    activo: bool

    class Config:
        from_attributes = True


class SetPrecioRequest(BaseModel):
    """Establece o actualiza el precio de un producto en una lista"""
    producto_id: UUID
    precio:      Decimal
