from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.cheques.model import ChequeEmitido, EstadoChequeEmitido
from app.modules.cheques.schemas import (
    ChequeEmitidoCreate,
    ChequeEmitidoUpdate,
    ChequeEmitidoResponse,
    CambioEstadoCheque,
    ResumenCirculacion,
)

router = APIRouter(prefix="/cheques-emitidos", tags=["Cheques Emitidos"])

# ── Máquina de estados ────────────────────────────────────────
TRANSICIONES = {
    EstadoChequeEmitido.emitido:               {EstadoChequeEmitido.en_transito,           EstadoChequeEmitido.anulado},
    EstadoChequeEmitido.en_transito:           {EstadoChequeEmitido.en_ventana,            EstadoChequeEmitido.rechazado, EstadoChequeEmitido.anulado},
    EstadoChequeEmitido.en_ventana:            {EstadoChequeEmitido.debitado,              EstadoChequeEmitido.vencido_sin_depositar, EstadoChequeEmitido.rechazado},
    EstadoChequeEmitido.rechazado:             {EstadoChequeEmitido.en_transito},
    EstadoChequeEmitido.debitado:              set(),
    EstadoChequeEmitido.vencido_sin_depositar: set(),
    EstadoChequeEmitido.anulado:               set(),
}

ESTADOS_VIVOS = [
    EstadoChequeEmitido.emitido,
    EstadoChequeEmitido.en_transito,
    EstadoChequeEmitido.en_ventana,
]


def _enrich(cheque: ChequeEmitido) -> dict:
    """Calcula campos derivados de fechas según el estado actual."""
    data = {c.name: getattr(cheque, c.name) for c in cheque.__table__.columns}
    data["monto"] = float(data["monto"])
    hoy = date.today()

    data["dias_para_vencer"]     = None
    data["dias_en_ventana"]      = None
    data["dias_restantes_cobro"] = None
    data["porcentaje_ventana"]   = None

    if cheque.estado in (EstadoChequeEmitido.emitido, EstadoChequeEmitido.en_transito):
        data["dias_para_vencer"] = (cheque.fecha_vencimiento - hoy).days

    elif cheque.estado == EstadoChequeEmitido.en_ventana:
        data["dias_en_ventana"]      = (hoy - cheque.fecha_vencimiento).days
        data["dias_restantes_cobro"] = (cheque.fecha_limite_deposito - hoy).days
        consumidos = (hoy - cheque.fecha_vencimiento).days
        data["porcentaje_ventana"]   = round(min(100.0, max(0.0, consumidos / 30 * 100)), 1)

    return data


# ── CRUD ──────────────────────────────────────────────────────

@router.get("/", response_model=List[ChequeEmitidoResponse])
def listar_cheques(
    estado:        Optional[EstadoChequeEmitido] = None,
    beneficiario:  Optional[str] = None,
    proximos_dias: Optional[int] = Query(None, description="Cheques que vencen en N días"),
    db:            Session = Depends(get_db),
    _:             dict = Depends(get_current_user),
):
    q = db.query(ChequeEmitido)
    if estado:
        q = q.filter(ChequeEmitido.estado == estado)
    if beneficiario:
        q = q.filter(ChequeEmitido.beneficiario.ilike(f"%{beneficiario}%"))
    if proximos_dias is not None:
        limite = date.today() + timedelta(days=proximos_dias)
        q = q.filter(
            ChequeEmitido.estado.in_([EstadoChequeEmitido.emitido, EstadoChequeEmitido.en_transito]),
            ChequeEmitido.fecha_vencimiento <= limite,
            ChequeEmitido.fecha_vencimiento >= date.today(),
        )
    cheques = q.order_by(ChequeEmitido.fecha_vencimiento.asc()).all()
    return [ChequeEmitidoResponse(**_enrich(c)) for c in cheques]


@router.post("/", response_model=ChequeEmitidoResponse, status_code=201)
def crear_cheque(
    data: ChequeEmitidoCreate,
    db:   Session = Depends(get_db),
    _:    dict = Depends(get_current_user),
):
    if data.fecha_vencimiento < data.fecha_emision:
        raise HTTPException(400, "La fecha de vencimiento no puede ser anterior a la de emisión")
    cheque = ChequeEmitido(**data.model_dump())
    # fecha_limite_deposito se setea via @validates en el model
    db.add(cheque)
    db.commit()
    db.refresh(cheque)
    return ChequeEmitidoResponse(**_enrich(cheque))


@router.get("/proximos-vencer", response_model=List[ChequeEmitidoResponse])
def proximos_a_vencer(
    dias: int = Query(7),
    db:   Session = Depends(get_db),
    _:    dict = Depends(get_current_user),
):
    limite = date.today() + timedelta(days=dias)
    cheques = (
        db.query(ChequeEmitido)
        .filter(
            ChequeEmitido.estado.in_([EstadoChequeEmitido.emitido, EstadoChequeEmitido.en_transito]),
            ChequeEmitido.fecha_vencimiento <= limite,
            ChequeEmitido.fecha_vencimiento >= date.today(),
        )
        .order_by(ChequeEmitido.fecha_vencimiento.asc())
        .all()
    )
    return [ChequeEmitidoResponse(**_enrich(c)) for c in cheques]


@router.get("/circulacion", response_model=dict)
def reporte_circulacion(
    db: Session = Depends(get_db),
    _:  dict = Depends(get_current_user),
):
    """
    Reporte completo de circulación:
    - en_ventana: cheques dentro de la ventana de 30 días post-vencimiento
    - proximos_ventana: en_transito cuya fecha_vencimiento <= hoy + 7 días
    - resumen: totales y métricas
    """
    hoy = date.today()
    en_7 = hoy + timedelta(days=7)

    # Cheques en ventana activa
    en_ventana = (
        db.query(ChequeEmitido)
        .filter(ChequeEmitido.estado == EstadoChequeEmitido.en_ventana)
        .order_by(ChequeEmitido.fecha_limite_deposito.asc())
        .all()
    )

    # Próximos a entrar en ventana (en_transito, vencen en <=7 días o ya vencieron hoy)
    proximos = (
        db.query(ChequeEmitido)
        .filter(
            ChequeEmitido.estado == EstadoChequeEmitido.en_transito,
            ChequeEmitido.fecha_vencimiento <= en_7,
        )
        .order_by(ChequeEmitido.fecha_vencimiento.asc())
        .all()
    )

    # Críticos: en_ventana con <= 5 días para vencer instrumento
    criticos = [c for c in en_ventana if (c.fecha_limite_deposito - hoy).days <= 5]

    en_ventana_enriched = [_enrich(c) for c in en_ventana]
    proximos_enriched   = [_enrich(c) for c in proximos]

    monto_ventana   = sum(float(c.monto) for c in en_ventana)
    monto_proximos  = sum(float(c.monto) for c in proximos)
    monto_critico   = sum(float(c.monto) for c in criticos)

    dias_prom = None
    if en_ventana:
        dias_prom = round(
            sum((hoy - c.fecha_vencimiento).days for c in en_ventana) / len(en_ventana), 1
        )

    return {
        "resumen": {
            "total_en_ventana":         len(en_ventana),
            "monto_en_ventana":         monto_ventana,
            "total_proximos_ventana":   len(proximos),
            "monto_proximos_ventana":   monto_proximos,
            "dias_promedio_en_ventana": dias_prom,
            "cheques_criticos":         len(criticos),
            "monto_critico":            monto_critico,
        },
        "en_ventana": en_ventana_enriched,
        "proximos_a_entrar": proximos_enriched,
    }


@router.get("/{cheque_id}", response_model=ChequeEmitidoResponse)
def obtener_cheque(
    cheque_id: UUID,
    db:        Session = Depends(get_db),
    _:         dict = Depends(get_current_user),
):
    cheque = db.query(ChequeEmitido).filter(ChequeEmitido.id == cheque_id).first()
    if not cheque:
        raise HTTPException(404, "Cheque no encontrado")
    return ChequeEmitidoResponse(**_enrich(cheque))


@router.put("/{cheque_id}", response_model=ChequeEmitidoResponse)
def actualizar_cheque(
    cheque_id: UUID,
    data:      ChequeEmitidoUpdate,
    db:        Session = Depends(get_db),
    _:         dict = Depends(get_current_user),
):
    cheque = db.query(ChequeEmitido).filter(ChequeEmitido.id == cheque_id).first()
    if not cheque:
        raise HTTPException(404, "Cheque no encontrado")
    if cheque.estado == EstadoChequeEmitido.anulado:
        raise HTTPException(400, "No se puede modificar un cheque anulado")

    cambios = data.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(cheque, campo, valor)

    if cheque.fecha_vencimiento < cheque.fecha_emision:
        raise HTTPException(400, "La fecha de vencimiento no puede ser anterior a la de emisión")

    db.commit()
    db.refresh(cheque)
    return ChequeEmitidoResponse(**_enrich(cheque))


@router.patch("/{cheque_id}/estado", response_model=ChequeEmitidoResponse)
def cambiar_estado(
    cheque_id: UUID,
    data:      CambioEstadoCheque,
    db:        Session = Depends(get_db),
    _:         dict = Depends(get_current_user),
):
    cheque = db.query(ChequeEmitido).filter(ChequeEmitido.id == cheque_id).first()
    if not cheque:
        raise HTTPException(404, "Cheque no encontrado")

    if data.estado not in TRANSICIONES[cheque.estado]:
        raise HTTPException(
            400,
            f"Transición inválida: {cheque.estado.value} → {data.estado.value}. "
            f"Permitidas: {[e.value for e in TRANSICIONES[cheque.estado]]}"
        )

    cheque.estado = data.estado
    if data.observaciones:
        cheque.observaciones = data.observaciones

    db.commit()
    db.refresh(cheque)
    return ChequeEmitidoResponse(**_enrich(cheque))


@router.delete("/{cheque_id}", status_code=204)
def eliminar_cheque(
    cheque_id: UUID,
    db:        Session = Depends(get_db),
    _:         dict = Depends(get_current_user),
):
    cheque = db.query(ChequeEmitido).filter(ChequeEmitido.id == cheque_id).first()
    if not cheque:
        raise HTTPException(404, "Cheque no encontrado")

    bloqueados = {EstadoChequeEmitido.debitado, EstadoChequeEmitido.en_ventana, EstadoChequeEmitido.en_transito}
    if cheque.estado in bloqueados:
        raise HTTPException(400, f"No se puede eliminar un cheque en estado '{cheque.estado.value}'")

    db.delete(cheque)
    db.commit()
