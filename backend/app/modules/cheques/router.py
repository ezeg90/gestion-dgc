from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
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
)

router = APIRouter(prefix="/api/v1/cheques-emitidos", tags=["Cheques Emitidos"])


def _enrich(cheque: ChequeEmitido) -> dict:
    """Agrega días_para_vencer al dict del cheque."""
    data = {c.name: getattr(cheque, c.name) for c in cheque.__table__.columns}
    data["monto"] = float(data["monto"])
    estados_activos = {EstadoChequeEmitido.emitido, EstadoChequeEmitido.en_transito}
    if cheque.estado in estados_activos:
        data["dias_para_vencer"] = (cheque.fecha_vencimiento - date.today()).days
    else:
        data["dias_para_vencer"] = None
    return data


@router.get("/", response_model=List[ChequeEmitidoResponse])
def listar_cheques(
    estado: Optional[EstadoChequeEmitido] = None,
    beneficiario: Optional[str] = None,
    proximos_dias: Optional[int] = Query(None, description="Cheques que vencen en N días"),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    q = db.query(ChequeEmitido)

    if estado:
        q = q.filter(ChequeEmitido.estado == estado)

    if beneficiario:
        q = q.filter(ChequeEmitido.beneficiario.ilike(f"%{beneficiario}%"))

    if proximos_dias is not None:
        limite = date.today() + timedelta(days=proximos_dias)
        estados_activos = [EstadoChequeEmitido.emitido, EstadoChequeEmitido.en_transito]
        q = q.filter(
            ChequeEmitido.estado.in_(estados_activos),
            ChequeEmitido.fecha_vencimiento <= limite,
            ChequeEmitido.fecha_vencimiento >= date.today(),
        )

    cheques = q.order_by(ChequeEmitido.fecha_vencimiento.asc()).all()
    return [ChequeEmitidoResponse(**_enrich(c)) for c in cheques]


@router.post("/", response_model=ChequeEmitidoResponse, status_code=201)
def crear_cheque(
    data: ChequeEmitidoCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    if data.fecha_vencimiento < data.fecha_emision:
        raise HTTPException(400, "La fecha de vencimiento no puede ser anterior a la de emisión")

    cheque = ChequeEmitido(**data.model_dump())
    db.add(cheque)
    db.commit()
    db.refresh(cheque)
    return ChequeEmitidoResponse(**_enrich(cheque))


@router.get("/proximos-vencer", response_model=List[ChequeEmitidoResponse])
def proximos_a_vencer(
    dias: int = Query(7, description="Umbral de días"),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    limite = date.today() + timedelta(days=dias)
    estados_activos = [EstadoChequeEmitido.emitido, EstadoChequeEmitido.en_transito]
    cheques = (
        db.query(ChequeEmitido)
        .filter(
            ChequeEmitido.estado.in_(estados_activos),
            ChequeEmitido.fecha_vencimiento <= limite,
            ChequeEmitido.fecha_vencimiento >= date.today(),
        )
        .order_by(ChequeEmitido.fecha_vencimiento.asc())
        .all()
    )
    return [ChequeEmitidoResponse(**_enrich(c)) for c in cheques]


@router.get("/{cheque_id}", response_model=ChequeEmitidoResponse)
def obtener_cheque(
    cheque_id: UUID,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    cheque = db.query(ChequeEmitido).filter(ChequeEmitido.id == cheque_id).first()
    if not cheque:
        raise HTTPException(404, "Cheque no encontrado")
    return ChequeEmitidoResponse(**_enrich(cheque))


@router.put("/{cheque_id}", response_model=ChequeEmitidoResponse)
def actualizar_cheque(
    cheque_id: UUID,
    data: ChequeEmitidoUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    cheque = db.query(ChequeEmitido).filter(ChequeEmitido.id == cheque_id).first()
    if not cheque:
        raise HTTPException(404, "Cheque no encontrado")

    if cheque.estado == EstadoChequeEmitido.anulado:
        raise HTTPException(400, "No se puede modificar un cheque anulado")

    cambios = data.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(cheque, campo, valor)

    # Revalidar fechas si se cambiaron
    if cheque.fecha_vencimiento < cheque.fecha_emision:
        raise HTTPException(400, "La fecha de vencimiento no puede ser anterior a la de emisión")

    db.commit()
    db.refresh(cheque)
    return ChequeEmitidoResponse(**_enrich(cheque))


@router.patch("/{cheque_id}/estado", response_model=ChequeEmitidoResponse)
def cambiar_estado(
    cheque_id: UUID,
    data: CambioEstadoCheque,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    cheque = db.query(ChequeEmitido).filter(ChequeEmitido.id == cheque_id).first()
    if not cheque:
        raise HTTPException(404, "Cheque no encontrado")

    # Máquina de estados: transiciones válidas
    transiciones = {
        EstadoChequeEmitido.emitido: {
            EstadoChequeEmitido.en_transito,
            EstadoChequeEmitido.anulado,
        },
        EstadoChequeEmitido.en_transito: {
            EstadoChequeEmitido.debitado,
            EstadoChequeEmitido.rechazado,
            EstadoChequeEmitido.anulado,
        },
        EstadoChequeEmitido.debitado: set(),
        EstadoChequeEmitido.rechazado: {EstadoChequeEmitido.en_transito},  # re-presentación
        EstadoChequeEmitido.anulado: set(),
    }

    if data.estado not in transiciones[cheque.estado]:
        raise HTTPException(
            400,
            f"Transición inválida: {cheque.estado.value} → {data.estado.value}",
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
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    cheque = db.query(ChequeEmitido).filter(ChequeEmitido.id == cheque_id).first()
    if not cheque:
        raise HTTPException(404, "Cheque no encontrado")

    estados_bloqueados = {EstadoChequeEmitido.debitado, EstadoChequeEmitido.en_transito}
    if cheque.estado in estados_bloqueados:
        raise HTTPException(400, f"No se puede eliminar un cheque en estado '{cheque.estado.value}'")

    db.delete(cheque)
    db.commit()