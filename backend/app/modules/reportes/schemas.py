from datetime import date
from decimal import Decimal
from typing import Dict
from pydantic import BaseModel


class PeriodoOut(BaseModel):
    desde: date
    hasta: date


class ConfigAplicadaOut(BaseModel):
    aplica_iva: bool
    tasa_iva:   Decimal


class DevengadoOut(BaseModel):
    """Estado de Resultados contable: lo que se vendió (remitos emitidos)
    en el período, sin importar si ya se cobró."""
    ingresos_brutos:          Decimal  # precio final, con IVA incluido
    iva_debito_fiscal:        Decimal  # se descuenta, es de AFIP no de la empresa
    ingresos_netos:           Decimal
    costo_ventas:             Decimal  # foto del costo al momento de cada venta
    resultado_bruto:          Decimal  # ingresos_netos - costo_ventas
    gastos_operativos:        Dict[str, Decimal]  # por categoría
    gastos_operativos_total:  Decimal
    resultado_neto:           Decimal  # resultado_bruto - gastos_operativos_total


class PercibidoOut(BaseModel):
    """Lo que efectivamente entró/salió de la cuenta en el período —
    un vistazo de caja para comparar contra el devengado, no reemplaza
    el Flujo de Caja Proyectado (que mira hacia adelante)."""
    cobros_clientes:    Decimal
    pagos_proveedores:  Decimal
    gastos_pagados:     Decimal
    resultado_neto:     Decimal  # cobros - pagos_proveedores - gastos_pagados


class EstadoResultadosOut(BaseModel):
    periodo:   PeriodoOut
    config:    ConfigAplicadaOut
    devengado: DevengadoOut
    percibido: PercibidoOut
