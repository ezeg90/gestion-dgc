from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from decimal import Decimal

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.cuentas_corrientes.model import CuentaCorriente, MovimientoCuentaCorriente
from app.modules.cuentas_corrientes.schemas import (
    CuentaCorrienteOut, CuentaResumenOut, MovimientoOut,
    RegistrarCobroRequest, AjusteManualRequest, ActualizarCuentaRequest
)
from app.modules.clientes.model import Cliente
from app.modules.usuarios.model import Usuario

router = APIRouter(prefix="/cuentas-corrientes", tags=["Cuentas corrientes"])


def recalcular_saldo(cuenta: CuentaCorriente, db: Session):
    """Recalcula y persiste el saldo desde los movimientos"""
    movs = db.query(MovimientoCuentaCorriente).filter(
        MovimientoCuentaCorriente.cuenta_corriente_id == cuenta.id
    ).all()
    saldo = sum(
        Decimal(str(m.monto)) if m.tipo == "debito" else -Decimal(str(m.monto))
        for m in movs
    )
    cuenta.saldo_actual = saldo
    db.add(cuenta)


@router.get("/", response_model=List[CuentaResumenOut])
def listar_cuentas(
    estado: Optional[str] = Query(None),
    con_saldo: Optional[bool] = Query(None, description="True = solo clientes con deuda"),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    query = db.query(CuentaCorriente)
    if estado:
        query = query.filter(CuentaCorriente.estado == estado)
    if con_saldo:
        query = query.filter(CuentaCorriente.saldo_actual > 0)

    cuentas = query.all()
    result = []
    for cc in cuentas:
        cliente = db.query(Cliente).filter(Cliente.id == cc.cliente_id).first()
        ultimo = db.query(MovimientoCuentaCorriente).filter(
            MovimientoCuentaCorriente.cuenta_corriente_id == cc.id
        ).order_by(desc(MovimientoCuentaCorriente.fecha)).first()

        result.append(CuentaResumenOut(
            id=cc.id,
            cliente_id=cc.cliente_id,
            cliente_nombre=cliente.razon_social if cliente else "—",
            cliente_telefono=cliente.telefono if cliente else None,
            cliente_localidad=cliente.localidad if cliente else None,
            saldo_actual=cc.saldo_actual,
            limite_credito=cc.limite_credito,
            estado=cc.estado,
            ultimo_movimiento=ultimo.fecha if ultimo else None,
        ))
    return sorted(result, key=lambda x: x.saldo_actual, reverse=True)


@router.get("/{cuenta_id}", response_model=CuentaCorrienteOut)
def obtener_cuenta(
    cuenta_id: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    cc = db.query(CuentaCorriente).filter(CuentaCorriente.id == cuenta_id).first()
    if not cc:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return cc


@router.get("/cliente/{cliente_id}", response_model=CuentaCorrienteOut)
def obtener_cuenta_por_cliente(
    cliente_id: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    cc = db.query(CuentaCorriente).filter(
        CuentaCorriente.cliente_id == cliente_id
    ).first()
    if not cc:
        raise HTTPException(status_code=404, detail="Este cliente no tiene cuenta corriente")
    return cc


@router.get("/{cuenta_id}/movimientos", response_model=List[MovimientoOut])
def listar_movimientos(
    cuenta_id: str,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    cc = db.query(CuentaCorriente).filter(CuentaCorriente.id == cuenta_id).first()
    if not cc:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    movs = db.query(MovimientoCuentaCorriente).filter(
        MovimientoCuentaCorriente.cuenta_corriente_id == cuenta_id
    ).order_by(desc(MovimientoCuentaCorriente.fecha)).limit(limit).all()
    return movs


@router.post("/{cuenta_id}/cobrar", response_model=CuentaCorrienteOut)
def registrar_cobro(
    cuenta_id: str,
    data: RegistrarCobroRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cc = db.query(CuentaCorriente).filter(CuentaCorriente.id == cuenta_id).first()
    if not cc:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    if data.monto <= 0:
        raise HTTPException(status_code=422, detail="El monto debe ser mayor a cero")

    mov = MovimientoCuentaCorriente(
        cuenta_corriente_id=str(cc.id),
        tipo="credito",
        monto=data.monto,
        referencia_tipo="cobro",
        descripcion=data.descripcion or f"Cobro de ${data.monto:,.2f}",
        usuario_id=str(current_user.id),
    )
    db.add(mov)
    db.flush()
    recalcular_saldo(cc, db)
    db.commit()
    db.refresh(cc)
    return cc


@router.post("/{cuenta_id}/ajuste", response_model=CuentaCorrienteOut)
def ajuste_manual(
    cuenta_id: str,
    data: AjusteManualRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cc = db.query(CuentaCorriente).filter(CuentaCorriente.id == cuenta_id).first()
    if not cc:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    if data.monto <= 0:
        raise HTTPException(status_code=422, detail="El monto debe ser mayor a cero")

    mov = MovimientoCuentaCorriente(
        cuenta_corriente_id=str(cc.id),
        tipo=data.tipo,
        monto=data.monto,
        referencia_tipo="ajuste_manual",
        descripcion=data.descripcion,
        usuario_id=str(current_user.id),
    )
    db.add(mov)
    db.flush()
    recalcular_saldo(cc, db)
    db.commit()
    db.refresh(cc)
    return cc


@router.patch("/{cuenta_id}", response_model=CuentaCorrienteOut)
def actualizar_cuenta(
    cuenta_id: str,
    data: ActualizarCuentaRequest,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    cc = db.query(CuentaCorriente).filter(CuentaCorriente.id == cuenta_id).first()
    if not cc:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cc, field, value)
    db.commit()
    db.refresh(cc)
    return cc
