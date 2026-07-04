from uuid import UUID
from typing import Optional, Literal
from pydantic import BaseModel
from datetime import datetime

UnidadMedida = Literal["unidad", "kg", "litro", "docena", "caja", "hora", "trabajo"]
TipoArticulo = Literal["producto", "servicio"]


class ProductoBase(BaseModel):
    nombre:        str
    descripcion:   Optional[str] = None
    tipo:          TipoArticulo = "producto"
    unidad_medida: UnidadMedida = "unidad"
    categoria:     Optional[str] = None
    subcategoria:  Optional[str] = None


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(BaseModel):
    nombre:        Optional[str] = None
    descripcion:   Optional[str] = None
    tipo:          Optional[TipoArticulo] = None
    unidad_medida: Optional[UnidadMedida] = None
    categoria:     Optional[str] = None
    subcategoria:  Optional[str] = None
    activo:        Optional[bool] = None


class ProductoOut(ProductoBase):
    id:         UUID
    activo:     bool
    created_at: datetime

    class Config:
        from_attributes = True

