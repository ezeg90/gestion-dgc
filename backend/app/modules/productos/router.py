from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.productos.model import Producto
from app.modules.productos.schemas import ProductoCreate, ProductoUpdate, ProductoOut, TipoArticulo
from app.modules.usuarios.model import Usuario

router = APIRouter(prefix="/productos", tags=["Productos"])


@router.get("/", response_model=List[ProductoOut])
def listar_productos(
    solo_activos: bool = True,
    tipo: Optional[TipoArticulo] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    query = db.query(Producto)
    if solo_activos:
        query = query.filter(Producto.activo == True)
    if tipo:
        query = query.filter(Producto.tipo == tipo)
    return query.order_by(Producto.nombre).all()


@router.get("/{producto_id}", response_model=ProductoOut)
def obtener_producto(
    producto_id: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.post("/", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
def crear_producto(
    data: ProductoCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    producto = Producto(**data.model_dump())
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


@router.patch("/{producto_id}", response_model=ProductoOut)
def actualizar_producto(
    producto_id: str,
    data: ProductoUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(producto, field, value)

    db.commit()
    db.refresh(producto)
    return producto
