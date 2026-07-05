from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.productos.model import Producto
from app.modules.productos.schemas import ProductoCreate, ProductoUpdate, ProductoOut, TipoArticulo
from app.modules.categorias.model import Categoria
from app.modules.usuarios.model import Usuario

router = APIRouter(prefix="/productos", tags=["Productos"])


def _resolver_nombres_categoria(productos: List[Producto]) -> None:
    """Setea categoria_nombre/subcategoria_nombre en cada instancia (no persiste),
    para que el frontend reciba el nombre legible junto con el categoria_id."""
    for p in productos:
        cat = p.categoria_rel
        if cat is None:
            p.categoria_nombre = None
            p.subcategoria_nombre = None
        elif cat.padre_id:
            p.categoria_nombre = cat.padre.nombre if cat.padre else None
            p.subcategoria_nombre = cat.nombre
        else:
            p.categoria_nombre = cat.nombre
            p.subcategoria_nombre = None


@router.get("/", response_model=List[ProductoOut])
def listar_productos(
    solo_activos: bool = True,
    tipo: Optional[TipoArticulo] = None,
    categoria_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    query = db.query(Producto).options(
        joinedload(Producto.categoria_rel).joinedload(Categoria.padre)
    )
    if solo_activos:
        query = query.filter(Producto.activo == True)
    if tipo:
        query = query.filter(Producto.tipo == tipo)
    if categoria_id:
        query = query.filter(Producto.categoria_id == categoria_id)
    productos = query.order_by(Producto.nombre).all()
    _resolver_nombres_categoria(productos)
    return productos


@router.get("/{producto_id}", response_model=ProductoOut)
def obtener_producto(
    producto_id: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    producto = (
        db.query(Producto)
        .options(joinedload(Producto.categoria_rel).joinedload(Categoria.padre))
        .filter(Producto.id == producto_id)
        .first()
    )
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    _resolver_nombres_categoria([producto])
    return producto


@router.post("/", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
def crear_producto(
    data: ProductoCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    if data.categoria_id:
        categoria = db.query(Categoria).filter(Categoria.id == str(data.categoria_id)).first()
        if not categoria:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")

    producto = Producto(**data.model_dump())
    db.add(producto)
    db.commit()
    db.refresh(producto)
    _resolver_nombres_categoria([producto])
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

    datos = data.model_dump(exclude_unset=True)
    if datos.get("categoria_id"):
        categoria = db.query(Categoria).filter(Categoria.id == str(datos["categoria_id"])).first()
        if not categoria:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")

    for field, value in datos.items():
        setattr(producto, field, value)

    db.commit()
    db.refresh(producto)
    _resolver_nombres_categoria([producto])
    return producto

