from uuid import UUID
from typing import Optional, List, Literal
from pydantic import BaseModel
from datetime import datetime

TipoCategoria = Literal["producto", "servicio"]


class CategoriaBase(BaseModel):
    nombre:   str
    padre_id: Optional[UUID] = None
    tipo:     Optional[TipoCategoria] = None


class CategoriaCreate(CategoriaBase):
    pass


class CategoriaUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo:   Optional[TipoCategoria] = None
    activo: Optional[bool] = None


class CategoriaOut(CategoriaBase):
    id:         UUID
    activo:     bool
    created_at: datetime

    class Config:
        from_attributes = True


class CategoriaArbolOut(CategoriaOut):
    """Categoría de nivel 1 con sus subcategorías anidadas (para selects en cascada)"""
    hijas: List[CategoriaOut] = []

    class Config:
        from_attributes = True