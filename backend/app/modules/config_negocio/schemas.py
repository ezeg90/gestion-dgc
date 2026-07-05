from typing import Optional
from decimal import Decimal
from pydantic import BaseModel


class ConfigNegocioOut(BaseModel):
    nombre_fantasia: Optional[str] = None
    aplica_iva:      bool
    tasa_iva:        Decimal

    class Config:
        from_attributes = True


class ConfigNegocioUpdate(BaseModel):
    nombre_fantasia: Optional[str] = None
    aplica_iva:      Optional[bool] = None
    tasa_iva:        Optional[Decimal] = None