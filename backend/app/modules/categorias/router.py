from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.categorias.model import Categoria
from app.modules.categorias.schemas import (
    CategoriaCreate, CategoriaUpdate, CategoriaOut, CategoriaArbolOut, TipoCategoria
)
from app.modules.productos.model import Producto
from app.modules.usuarios.model import Usuario

router = APIRouter(prefix="/categorias", tags=["Categorías"])


@router.get("/", response_model=List[CategoriaOut])
def listar_categorias(
    solo_activas: bool = True,
    tipo: Optional[TipoCategoria] = None,
    padre_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    query = db.query(Categoria)
    if solo_activas:
        query = query.filter(Categoria.activo == True)
    if tipo:
        query = query.filter((Categoria.tipo == tipo) | (Categoria.tipo.is_(None)))
    if padre_id == "":
        query = query.filter(Categoria.padre_id.is_(None))
    elif padre_id is not None:
        query = query.filter(Categoria.padre_id == padre_id)
    return query.order_by(Categoria.nombre).all()


@router.get("/arbol", response_model=List[CategoriaArbolOut])
def arbol_categorias(
    tipo: Optional[TipoCategoria] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    """Categorías de nivel 1 con sus subcategorías anidadas — usado por el frontend
    para poblar los selects en cascada de categoría/subcategoría."""
    query = (
        db.query(Categoria)
        .options(joinedload(Categoria.hijas))
        .filter(Categoria.padre_id.is_(None), Categoria.activo == True)
    )
    if tipo:
        query = query.filter((Categoria.tipo == tipo) | (Categoria.tipo.is_(None)))
    categorias = query.order_by(Categoria.nombre).all()

    if tipo:
        for c in categorias:
            c.hijas = [h for h in c.hijas if h.activo and (h.tipo == tipo or h.tipo is None)]
    return categorias


@router.post("/", response_model=CategoriaOut, status_code=status.HTTP_201_CREATED)
def crear_categoria(
    data: CategoriaCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    if data.padre_id:
        padre = db.query(Categoria).filter(Categoria.id == str(data.padre_id)).first()
        if not padre:
            raise HTTPException(status_code=404, detail="Categoría padre no encontrada")
        if padre.padre_id is not None:
            raise HTTPException(status_code=422, detail="Solo se admiten dos niveles: categoría y subcategoría")

    existente = db.query(Categoria).filter(
        Categoria.nombre == data.nombre,
        Categoria.padre_id == (str(data.padre_id) if data.padre_id else None),
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="Ya existe una categoría con ese nombre en ese nivel")

    categoria = Categoria(**data.model_dump())
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


@router.patch("/{categoria_id}", response_model=CategoriaOut)
def actualizar_categoria(
    categoria_id: str,
    data: CategoriaUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    categoria = db.query(Categoria).filter(Categoria.id == categoria_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(categoria, field, value)

    db.commit()
    db.refresh(categoria)
    return categoria


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_categoria(
    categoria_id: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    categoria = db.query(Categoria).filter(Categoria.id == categoria_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    if categoria.hijas:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar: tiene subcategorías. Eliminalas primero o desactivá la categoría."
        )

    en_uso = db.query(Producto).filter(Producto.categoria_id == categoria_id).count()
    if en_uso:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: {en_uso} producto(s) usan esta categoría. Desactivala en cambio."
        )

    db.delete(categoria)
    db.commit()