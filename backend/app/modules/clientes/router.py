from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.clientes.model import Cliente
from app.modules.clientes.schemas import ClienteCreate, ClienteUpdate, ClienteOut, ClienteListOut
from app.modules.usuarios.model import Usuario

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("/", response_model=List[ClienteListOut])
def listar_clientes(
    estado: Optional[str] = Query(None),
    localidad: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Buscar por nombre o CUIT"),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    query = db.query(Cliente)

    if estado:
        query = query.filter(Cliente.estado == estado)
    if localidad:
        query = query.filter(Cliente.localidad.ilike(f"%{localidad}%"))
    if q:
        query = query.filter(
            Cliente.razon_social.ilike(f"%{q}%") | Cliente.cuit.ilike(f"%{q}%")
        )

    return query.order_by(Cliente.razon_social).all()


@router.get("/{cliente_id}", response_model=ClienteOut)
def obtener_cliente(
    cliente_id: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.post("/", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def crear_cliente(
    data: ClienteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cliente = Cliente(**data.model_dump(), created_by=current_user.id)
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.patch("/{cliente_id}", response_model=ClienteOut)
def actualizar_cliente(
    cliente_id: str,
    data: ClienteUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cliente, field, value)

    db.commit()
    db.refresh(cliente)
    return cliente


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_cliente(
    cliente_id: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    """Soft delete — cambia estado a inactivo, no borra el registro"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    cliente.estado = "inactivo"
    db.commit()
