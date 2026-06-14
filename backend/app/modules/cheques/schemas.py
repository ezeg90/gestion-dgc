from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date
from uuid import UUID
from app.modules.cheques.model import EstadoChequeEmitido


class ChequeEmitidoCreate(BaseModel):
    numero:            str
    banco:             str
    sucursal:          Optional[str] = None
    beneficiario:      str
    monto:             float
    fecha_emision:     date
    fecha_vencimiento: date
    concepto:          Optional[str] = None
    observaciones:     Optional[str] = None
    # fecha_limite_deposito se calcula automáticamente en el model

    @field_validator("monto")
    @classmethod
    def monto_positivo(cls, v):
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return round(v, 2)


class ChequeEmitidoUpdate(BaseModel):
    numero:            Optional[str]   = None
    banco:             Optional[str]   = None
    sucursal:          Optional[str]   = None
    beneficiario:      Optional[str]   = None
    monto:             Optional[float] = None
    fecha_emision:     Optional[date]  = None
    fecha_vencimiento: Optional[date]  = None
    concepto:          Optional[str]   = None
    estado:            Optional[EstadoChequeEmitido] = None
    observaciones:     Optional[str]   = None


class ChequeEmitidoResponse(BaseModel):
    id:                    UUID
    numero:                str
    banco:                 str
    sucursal:              Optional[str]
    beneficiario:          str
    monto:                 float
    fecha_emision:         date
    fecha_vencimiento:     date
    fecha_limite_deposito: date
    concepto:              Optional[str]
    estado:                EstadoChequeEmitido
    observaciones:         Optional[str]
    dias_para_vencer:      Optional[int] = None   # días hasta fecha_vencimiento (estados previos)
    dias_en_ventana:       Optional[int] = None   # días transcurridos desde fecha_vencimiento
    dias_restantes_cobro:  Optional[int] = None   # días hasta fecha_limite_deposito
    porcentaje_ventana:    Optional[float] = None # 0-100, % de los 30d consumidos

    model_config = {"from_attributes": True}


class CambioEstadoCheque(BaseModel):
    estado:        EstadoChequeEmitido
    observaciones: Optional[str] = None


class ResumenCirculacion(BaseModel):
    """Respuesta del endpoint /circulacion"""
    total_en_ventana:         int
    monto_en_ventana:         float
    total_proximos_ventana:   int      # en_transito con vencimiento <= 7 días
    monto_proximos_ventana:   float
    dias_promedio_en_ventana: Optional[float]
    cheques_criticos:         int      # en_ventana con <= 5 días para vencer instrumento
    monto_critico:            float
