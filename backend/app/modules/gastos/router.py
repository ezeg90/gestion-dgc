from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from typing import List, Optional
from datetime import date
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.gastos.model import Gasto, FormaPagoGasto, EstadoGasto, CategoriaGasto
from app.modules.gastos.schemas import (
    GastoCreate, GastoUpdate, GastoResponse, ResumenGastos
)
from app.modules.proveedores.model import (
    Proveedor, CuentaCorrienteProveedor, MovimientoCCProveedor, TipoMovimientoProveedor
)
from app.modules.cheques.model import ChequeEmitido

router = APIRouter(prefix="/gastos", tags=["Gastos"])


def _enrich_gasto(g: Gasto, db: Session) -> dict:
    data = {c.name: getattr(g, c.name) for c in g.__table__.columns}
    data["monto"] = float(data["monto"])
    data["proveedor_nombre"] = None
    data["cheque_numero"]    = None

    if g.proveedor_id:
        p = db.query(Proveedor).filter(Proveedor.id == g.proveedor_id).first()
        if p:
            data["proveedor_nombre"] = p.nombre

    if g.cheque_id:
        ch = db.query(ChequeEmitido).filter(ChequeEmitido.id == g.cheque_id).first()
        if ch:
            data["cheque_numero"] = ch.numero

    return data


def _impactar_cc_proveedor(db: Session, gasto: Gasto):
    """Genera débito en CC del proveedor cuando la forma de pago es cuenta_corriente_proveedor."""
    cc = db.query(CuentaCorrienteProveedor).filter(
        CuentaCorrienteProveedor.proveedor_id == gasto.proveedor_id
    ).first()
    if not cc:
        raise HTTPException(400, "El proveedor no tiene cuenta corriente configurada")

    mov = MovimientoCCProveedor(
        cuenta_id=cc.id,
        tipo=TipoMovimientoProveedor.debito,
        monto=float(gasto.monto),
        descripcion=f"Compra: {gasto.concepto} — Comprobante {gasto.numero_comprobante or 'S/N'}",
        referencia_gasto_id=gasto.id,
    )
    cc.saldo_actual = float(cc.saldo_actual) + float(gasto.monto)
    db.add(mov)


# ── CRUD ──────────────────────────────────────────────────────

@router.get("/", response_model=List[GastoResponse])
def listar_gastos(
    estado:       Optional[EstadoGasto]    = None,
    categoria:    Optional[CategoriaGasto] = None,
    proveedor_id: Optional[UUID]           = None,
    fecha_desde:  Optional[date]           = None,
    fecha_hasta:  Optional[date]           = None,
    db:           Session = Depends(get_db),
    _:            dict = Depends(get_current_user),
):
    q = db.query(Gasto)
    if estado:
        q = q.filter(Gasto.estado == estado)
    if categoria:
        q = q.filter(Gasto.categoria == categoria)
    if proveedor_id:
        q = q.filter(Gasto.proveedor_id == proveedor_id)
    if fecha_desde:
        q = q.filter(Gasto.fecha >= fecha_desde)
    if fecha_hasta:
        q = q.filter(Gasto.fecha <= fecha_hasta)
    gastos = q.order_by(Gasto.fecha.desc()).all()
    return [GastoResponse(**_enrich_gasto(g, db)) for g in gastos]


@router.post("/", response_model=GastoResponse, status_code=201)
def crear_gasto(
    data: GastoCreate,
    db:   Session = Depends(get_db),
    _:    dict = Depends(get_current_user),
):
    # Validar cheque existe si forma_pago = cheque
    if data.forma_pago == FormaPagoGasto.cheque and data.cheque_id:
        ch = db.query(ChequeEmitido).filter(ChequeEmitido.id == data.cheque_id).first()
        if not ch:
            raise HTTPException(404, "Cheque no encontrado")

    # Validar proveedor existe si se referencia
    if data.proveedor_id:
        prov = db.query(Proveedor).filter(Proveedor.id == data.proveedor_id).first()
        if not prov:
            raise HTTPException(404, "Proveedor no encontrado")

    gasto = Gasto(**data.model_dump())
    db.add(gasto)
    db.flush()  # genera UUID antes de impactar CC

    # Impacto automático en CC si forma_pago = cuenta_corriente_proveedor
    if data.forma_pago == FormaPagoGasto.cuenta_corriente_proveedor:
        _impactar_cc_proveedor(db, gasto)
        gasto.estado = EstadoGasto.pagado  # queda registrado como pagado vía CC

    db.commit()
    db.refresh(gasto)
    return GastoResponse(**_enrich_gasto(gasto, db))


@router.get("/resumen", response_model=ResumenGastos)
def resumen_gastos(
    año: Optional[int] = None,
    mes: Optional[int] = None,
    db:  Session = Depends(get_db),
    _:   dict = Depends(get_current_user),
):
    from datetime import datetime
    hoy = date.today()
    año_actual = año or hoy.year
    mes_actual = mes or hoy.month

    q_base = db.query(Gasto).filter(Gasto.estado != EstadoGasto.anulado)

    # Total mes actual
    q_mes = q_base.filter(
        extract("year", Gasto.fecha) == año_actual,
        extract("month", Gasto.fecha) == mes_actual,
    )
    total_mes = sum(float(g.monto) for g in q_mes.all())

    # Total año
    q_año = q_base.filter(extract("year", Gasto.fecha) == año_actual)
    gastos_año = q_año.all()
    total_año = sum(float(g.monto) for g in gastos_año)

    # Por categoría (año)
    por_cat = {}
    for g in gastos_año:
        k = g.categoria.value
        por_cat[k] = round(por_cat.get(k, 0) + float(g.monto), 2)

    # Por forma de pago (año)
    por_pago = {}
    for g in gastos_año:
        k = g.forma_pago.value
        por_pago[k] = round(por_pago.get(k, 0) + float(g.monto), 2)

    # Pendientes
    pendientes = db.query(Gasto).filter(Gasto.estado == EstadoGasto.pendiente).all()

    return ResumenGastos(
        total_mes=round(total_mes, 2),
        total_año=round(total_año, 2),
        por_categoria=por_cat,
        por_forma_pago=por_pago,
        cantidad_pendientes=len(pendientes),
        monto_pendientes=round(sum(float(g.monto) for g in pendientes), 2),
    )


@router.get("/{gasto_id}", response_model=GastoResponse)
def obtener_gasto(
    gasto_id: UUID,
    db:       Session = Depends(get_db),
    _:        dict = Depends(get_current_user),
):
    g = db.query(Gasto).filter(Gasto.id == gasto_id).first()
    if not g:
        raise HTTPException(404, "Gasto no encontrado")
    return GastoResponse(**_enrich_gasto(g, db))


@router.patch("/{gasto_id}", response_model=GastoResponse)
def actualizar_gasto(
    gasto_id: UUID,
    data:     GastoUpdate,
    db:       Session = Depends(get_db),
    _:        dict = Depends(get_current_user),
):
    g = db.query(Gasto).filter(Gasto.id == gasto_id).first()
    if not g:
        raise HTTPException(404, "Gasto no encontrado")
    if g.estado == EstadoGasto.anulado:
        raise HTTPException(400, "No se puede modificar un gasto anulado")

    cambios = data.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(g, campo, valor)

    db.commit()
    db.refresh(g)
    return GastoResponse(**_enrich_gasto(g, db))


@router.patch("/{gasto_id}/pagar", response_model=GastoResponse)
def marcar_pagado(
    gasto_id: UUID,
    db:       Session = Depends(get_db),
    _:        dict = Depends(get_current_user),
):
    """Marca un gasto pendiente como pagado (efectivo / transferencia)."""
    g = db.query(Gasto).filter(Gasto.id == gasto_id).first()
    if not g:
        raise HTTPException(404, "Gasto no encontrado")
    if g.estado != EstadoGasto.pendiente:
        raise HTTPException(400, f"El gasto está en estado '{g.estado.value}', no se puede marcar como pagado")
    g.estado = EstadoGasto.pagado
    db.commit()
    db.refresh(g)
    return GastoResponse(**_enrich_gasto(g, db))


@router.patch("/{gasto_id}/anular", response_model=GastoResponse)
def anular_gasto(
    gasto_id: UUID,
    db:       Session = Depends(get_db),
    _:        dict = Depends(get_current_user),
):
    g = db.query(Gasto).filter(Gasto.id == gasto_id).first()
    if not g:
        raise HTTPException(404, "Gasto no encontrado")
    if g.estado == EstadoGasto.anulado:
        raise HTTPException(400, "El gasto ya está anulado")
    g.estado = EstadoGasto.anulado
    db.commit()
    db.refresh(g)
    return GastoResponse(**_enrich_gasto(g, db))


@router.delete("/{gasto_id}", status_code=204)
def eliminar_gasto(
    gasto_id: UUID,
    db:       Session = Depends(get_db),
    _:        dict = Depends(get_current_user),
):
    g = db.query(Gasto).filter(Gasto.id == gasto_id).first()
    if not g:
        raise HTTPException(404, "Gasto no encontrado")
    if g.estado == EstadoGasto.pagado:
        raise HTTPException(400, "No se puede eliminar un gasto pagado. Use anular.")
    db.delete(g)
    db.commit()
