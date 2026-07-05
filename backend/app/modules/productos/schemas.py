from uuid import UUID
from typing import Optional, Literal
from decimal import Decimal
from pydantic import BaseModel
from datetime import datetime

UnidadMedida = Literal["unidad", "kg", "litro", "docena", "caja", "hora", "trabajo"]
TipoArticulo = Literal["producto", "servicio"]


class ProductoBase(BaseModel):
    nombre:         str
    descripcion:    Optional[str] = None
    tipo:           TipoArticulo = "producto"
    unidad_medida:  UnidadMedida = "unidad"
    categoria_id:   Optional[UUID] = None
    costo_unitario: Optional[Decimal] = None


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(BaseModel):
    nombre:         Optional[str] = None
    descripcion:    Optional[str] = None
    tipo:           Optional[TipoArticulo] = None
    unidad_medida:  Optional[UnidadMedida] = None
    categoria_id:   Optional[UUID] = None
    costo_unitario: Optional[Decimal] = None
    activo:         Optional[bool] = None


class ProductoOut(ProductoBase):
    id:                  UUID
    activo:              bool
    created_at:          datetime
    # Resueltos server-side a partir de categoria_id, para que el frontend
    # no tenga que pedir el árbol de categorías solo para mostrar el nombre
    categoria_nombre:    Optional[str] = None
    subcategoria_nombre: Optional[str] = None

    class Config:
        from_attributes = True

