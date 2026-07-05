from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.usuarios.model import Usuario
from app.modules.remitos.model import Remito, RemitoPedido
from app.modules.pedidos.model import Pedido, PedidoItem
from app.modules.gastos.model import Gasto, EstadoGasto
from app.modules.cuentas_corrientes.model import MovimientoCuentaCorriente
from app.modules.proveedores.model import MovimientoCCProveedor, TipoMovimientoProveedor
from app.modules.config_negocio.model import ConfigNegocio
from app.modules.reportes.schemas import EstadoResultadosOut

router = APIRouter(prefix="/reportes", tags=["Reportes"])

CENTAVOS = Decimal("0.01")


def _rango_fechas(desde: Optional[date], hasta: Optional[date]):
    """Default: mes calendario actual si no se especifica rango."""
    hoy = date.today()
    if not hasta:
        hasta = hoy
    if not desde:
        desde = hasta.replace(day=1)
    return desde, hasta


@router.get("/estado-resultados", response_model=EstadoResultadosOut)
def estado_resultados(
    desde: Optional[date] = Query(None, description="Default: primer día del mes actual"),
    hasta: Optional[date] = Query(None, description="Default: hoy"),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    desde, hasta = _rango_fechas(desde, hasta)
    hasta_exclusivo = hasta + timedelta(days=1)  # límite superior para columnas datetime

    config = db.query(ConfigNegocio).filter(ConfigNegocio.id == 1).first()
    aplica_iva = config.aplica_iva if config else True
    tasa_iva = Decimal(config.tasa_iva) if config else Decimal("21.00")

    # ── DEVENGADO: lo vendido (remitos emitidos) en el período ──────────
    fila = (
        db.query(
            func.coalesce(func.sum(PedidoItem.subtotal), 0).label("ingresos_brutos"),
            func.coalesce(func.sum(PedidoItem.subtotal_costo), 0).label("costo_ventas"),
        )
        .select_from(Remito)
        .join(RemitoPedido, RemitoPedido.remito_id == Remito.id)
        .join(Pedido, Pedido.id == RemitoPedido.pedido_id)
        .join(PedidoItem, PedidoItem.pedido_id == Pedido.id)
        .filter(Remito.estado == "emitido")
        .filter(Remito.fecha >= desde, Remito.fecha <= hasta)
        .first()
    )
    ingresos_brutos = Decimal(fila.ingresos_brutos or 0)
    costo_ventas    = Decimal(fila.costo_ventas or 0)

    if aplica_iva and ingresos_brutos:
        ingresos_netos = (ingresos_brutos / (1 + tasa_iva / 100)).quantize(CENTAVOS, rounding=ROUND_HALF_UP)
    else:
        ingresos_netos = ingresos_brutos
    iva_debito_fiscal = (ingresos_brutos - ingresos_netos).quantize(CENTAVOS, rounding=ROUND_HALF_UP)

    resultado_bruto = ingresos_netos - costo_ventas

    gastos_por_categoria = (
        db.query(Gasto.categoria, func.coalesce(func.sum(Gasto.monto), 0))
        .filter(Gasto.estado != EstadoGasto.anulado)
        .filter(Gasto.fecha >= desde, Gasto.fecha <= hasta)
        .group_by(Gasto.categoria)
        .all()
    )
    gastos_dict = {cat.value: Decimal(monto) for cat, monto in gastos_por_categoria}
    gastos_operativos_total = sum(gastos_dict.values(), Decimal("0"))

    resultado_neto_devengado = resultado_bruto - gastos_operativos_total

    # ── PERCIBIDO: lo que efectivamente entró/salió de la cuenta ────────
    cobros_clientes = Decimal(
        db.query(func.coalesce(func.sum(MovimientoCuentaCorriente.monto), 0))
        .filter(
            MovimientoCuentaCorriente.tipo == "credito",
            MovimientoCuentaCorriente.referencia_tipo == "cobro",
            MovimientoCuentaCorriente.fecha >= desde,
            MovimientoCuentaCorriente.fecha < hasta_exclusivo,
        )
        .scalar() or 0
    )

    pagos_proveedores = Decimal(
        db.query(func.coalesce(func.sum(MovimientoCCProveedor.monto), 0))
        .filter(
            MovimientoCCProveedor.tipo == TipoMovimientoProveedor.credito,
            MovimientoCCProveedor.fecha >= desde,
            MovimientoCCProveedor.fecha < hasta_exclusivo,
        )
        .scalar() or 0
    )

    gastos_pagados = Decimal(
        db.query(func.coalesce(func.sum(Gasto.monto), 0))
        .filter(
            Gasto.estado == EstadoGasto.pagado,
            Gasto.fecha >= desde, Gasto.fecha <= hasta,
        )
        .scalar() or 0
    )

    resultado_neto_percibido = cobros_clientes - pagos_proveedores - gastos_pagados

    return {
        "periodo": {"desde": desde, "hasta": hasta},
        "config": {"aplica_iva": aplica_iva, "tasa_iva": tasa_iva},
        "devengado": {
            "ingresos_brutos": ingresos_brutos,
            "iva_debito_fiscal": iva_debito_fiscal,
            "ingresos_netos": ingresos_netos,
            "costo_ventas": costo_ventas,
            "resultado_bruto": resultado_bruto,
            "gastos_operativos": gastos_dict,
            "gastos_operativos_total": gastos_operativos_total,
            "resultado_neto": resultado_neto_devengado,
        },
        "percibido": {
            "cobros_clientes": cobros_clientes,
            "pagos_proveedores": pagos_proveedores,
            "gastos_pagados": gastos_pagados,
            "resultado_neto": resultado_neto_percibido,
        },
    }
