from uuid import UUID
from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime


class UsuarioBase(BaseModel):
    nombre: str
    email: EmailStr
    rol: str = "operador"


class UsuarioCreate(UsuarioBase):
    password: str


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None


class UsuarioOut(UsuarioBase):
    id: UUID
    activo: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut
