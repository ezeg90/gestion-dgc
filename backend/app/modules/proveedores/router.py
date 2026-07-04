from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.proveedores.model import (
    Proveedor, CuentaCorrienteProveedor, MovimientoCCProveedor,
    EstadoProveedor, TipoMovimientoProveedor
)
from app.modules.proveedores.schemas import (
    ProveedorCreate, ProveedorUpdate, ProveedorResponse,
    CCProveedorResponse, MovimientoCCProveedorResponse,
    PagoProveedorRequest, AjusteManualCCProveedor
)

router = APIRouter(prefix="/proveedores", tags=["Proveedores"])


def _crear_cc(db: Session, proveedor_id: UUID) -> CuentaCorrienteProveedor:
    """Crea la cuenta corriente al crear el proveedor."""
    cc = CuentaCorrienteProveedor(proveedor_id=proveedor_id)
    db.add(cc)
    return cc


def _enrich_proveedor(p: Proveedor) -> dict:
    data = {c.name: getattr(p, c.name) for c in p.__table__.columns}
    data["saldo_cc"] = float(p.cuenta_corriente.saldo_actual) if p.cuenta_corriente else None
    return data


# ── CRUD Proveedores ──────────────────────────────────────────

@router.get("/", response_model=List[ProveedorResponse])
def listar_proveedores(
    estado:    Optional[EstadoProveedor] = None,
    buscar:    Optional[str] = None,
    db:        Session = Depends(get_db),
    _:         dict = Depends(get_current_user),
):
    q = db.query(Proveedor)
    if estado:
        q = q.filter(Proveedor.estado == estado)
    if buscar:
        q = q.filter(Proveedor.nombre.ilike(f"%{buscar}%"))
    proveedores = q.order_by(Proveedor.nombre.asc()).all()
    return [ProveedorResponse(**_enrich_proveedor(p)) for p in proveedores]


@router.post("/", response_model=ProveedorResponse, status_code=201)
def crear_proveedor(
    data: ProveedorCreate,
    db:   Session = Depends(get_db),
    _:    dict = Depends(get_current_user),
):
    if data.cuit:
        existe = db.query(Proveedor).filter(Proveedor.cuit == data.cuit).first()
        if existe:
            raise HTTPException(400, f"Ya existe un proveedor con CUIT {data.cuit}")

    proveedor = Proveedor(**data.model_dump())
    db.add(proveedor)
    db.flush()  # genera el UUID antes del commit
    _crear_cc(db, proveedor.id)
    db.commit()
    db.refresh(proveedor)
    return ProveedorResponse(**_enrich_proveedor(proveedor))


@router.get("/{proveedor_id}", response_model=ProveedorResponse)
def obtener_proveedor(
    proveedor_id: UUID,
    db:           Session = Depends(get_db),
    _:            dict = Depends(get_current_user),
):
    p = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not p:
        raise HTTPException(404, "Proveedor no encontrado")
    return ProveedorResponse(**_enrich_proveedor(p))


@router.patch("/{proveedor_id}", response_model=ProveedorResponse)
def actualizar_proveedor(
    proveedor_id: UUID,
    data:         ProveedorUpdate,
    db:           Session = Depends(get_db),
    _:            dict = Depends(get_current_user),
):
    p = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not p:
        raise HTTPException(404, "Proveedor no encontrado")

    cambios = data.model_dump(exclude_unset=True)
    if "cuit" in cambios and cambios["cuit"]:
        existe = db.query(Proveedor).filter(
            Proveedor.cuit == cambios["cuit"], Proveedor.id != proveedor_id
        ).first()
        if existe:
            raise HTTPException(400, f"Ya existe un proveedor con CUIT {cambios['cuit']}")

    for campo, valor in cambios.items():
        setattr(p, campo, valor)

    db.commit()
    db.refresh(p)
    return ProveedorResponse(**_enrich_proveedor(p))


# ── Cuenta corriente del proveedor ───────────────────────────

@router.get("/{proveedor_id}/cuenta", response_model=CCProveedorResponse)
def obtener_cuenta(
    proveedor_id: UUID,
    db:           Session = Depends(get_db),
    _:            dict = Depends(get_current_user),
):
    p = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not p:
        raise HTTPException(404, "Proveedor no encontrado")
    cc = p.cuenta_corriente
    data = {c.name: getattr(cc, c.name) for c in cc.__table__.columns}
    data["saldo_actual"]   = float(data["saldo_actual"])
    data["limite_credito"] = float(data["limite_credito"])
    data["proveedor_nombre"] = p.nombre
    return CCProveedorResponse(**data)


@router.get("/{proveedor_id}/cuenta/movimientos",
            response_model=List[MovimientoCCProveedorResponse])
def listar_movimientos(
    proveedor_id: UUID,
    limit:        int = Query(50, le=200),
    db:           Session = Depends(get_db),
    _:            dict = Depends(get_current_user),
):
    p = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not p:
        raise HTTPException(404, "Proveedor no encontrado")
    movs = (
        db.query(MovimientoCCProveedor)
        .filter(MovimientoCCProveedor.cuenta_id == p.cuenta_corriente.id)
        .order_by(MovimientoCCProveedor.fecha.desc())
        .limit(limit)
        .all()
    )
    result = []
    for m in movs:
        d = {c.name: getattr(m, c.name) for c in m.__table__.columns}
        d["monto"] = float(d["monto"])
        result.append(MovimientoCCProveedorResponse(**d))
    return result


@router.post("/{proveedor_id}/cuenta/pagar", response_model=CCProveedorResponse)
def registrar_pago(
    proveedor_id: UUID,
    data:         PagoProveedorRequest,
    db:           Session = Depends(get_db),
    _:            dict = Depends(get_current_user),
):
    """Registra un pago a proveedor (reduce la deuda de DGC)."""
    p = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not p:
        raise HTTPException(404, "Proveedor no encontrado")
    cc = p.cuenta_corriente
    mov = MovimientoCCProveedor(
        cuenta_id=cc.id,
        tipo=TipoMovimientoProveedor.credito,
        monto=data.monto,
        descripcion=data.descripcion or f"Pago a proveedor ${data.monto:,.2f}",
    )
    cc.saldo_actual = float(cc.saldo_actual) - data.monto
    db.add(mov)
    db.commit()
    db.refresh(cc)
    d = {c.name: getattr(cc, c.name) for c in cc.__table__.columns}
    d["saldo_actual"]    = float(d["saldo_actual"])
    d["limite_credito"]  = float(d["limite_credito"])
    d["proveedor_nombre"] = p.nombre
    return CCProveedorResponse(**d)


@router.post("/{proveedor_id}/cuenta/ajuste", response_model=CCProveedorResponse)
def ajuste_manual(
    proveedor_id: UUID,
    data:         AjusteManualCCProveedor,
    db:           Session = Depends(get_db),
    _:            dict = Depends(get_current_user),
):
    p = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not p:
        raise HTTPException(404, "Proveedor no encontrado")
    cc = p.cuenta_corriente
    mov = MovimientoCCProveedor(
        cuenta_id=cc.id,
        tipo=data.tipo,
        monto=data.monto,
        descripcion=data.descripcion,
    )
    if data.tipo == TipoMovimientoProveedor.debito:
        cc.saldo_actual = float(cc.saldo_actual) + data.monto
    else:
        cc.saldo_actual = float(cc.saldo_actual) - data.monto
    db.add(mov)
    db.commit()
    db.refresh(cc)
    d = {c.name: getattr(cc, c.name) for c in cc.__table__.columns}
    d["saldo_actual"]    = float(d["saldo_actual"])
    d["limite_credito"]  = float(d["limite_credito"])
    d["proveedor_nombre"] = p.nombre
    return CCProveedorResponse(**d)