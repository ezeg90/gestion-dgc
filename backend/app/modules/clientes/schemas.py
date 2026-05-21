from uuid import UUID
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr
from datetime import datetime


CondicionIVA = Literal["responsable_inscripto", "monotributo", "consumidor_final", "exento"]
EstadoCliente = Literal["activo", "inactivo", "bloqueado"]


class ClienteBase(BaseModel):
    razon_social:     str
    cuit:             Optional[str] = None
    condicion_iva:    CondicionIVA = "consumidor_final"
    telefono:         Optional[str] = None
    email:            Optional[EmailStr] = None
    direccion:        Optional[str] = None
    localidad:        Optional[str] = None
    latitud:          Optional[float] = None
    longitud:         Optional[float] = None
    lista_precios_id: Optional[UUID] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    razon_social:     Optional[str] = None
    cuit:             Optional[str] = None
    condicion_iva:    Optional[CondicionIVA] = None
    telefono:         Optional[str] = None
    email:            Optional[EmailStr] = None
    direccion:        Optional[str] = None
    localidad:        Optional[str] = None
    latitud:          Optional[float] = None
    longitud:         Optional[float] = None
    estado:           Optional[EstadoCliente] = None
    lista_precios_id: Optional[UUID] = None


class ClienteOut(ClienteBase):
    id:         UUID
    estado:     EstadoCliente
    created_at: datetime

    class Config:
        from_attributes = True


class ClienteListOut(BaseModel):
    """Versión reducida para listados"""
    id:           UUID
    razon_social: str
    telefono:     Optional[str]
    localidad:    Optional[str]
    estado:       EstadoCliente

    class Config:
        from_attributes = True
