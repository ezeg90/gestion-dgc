from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.precios.model import ListaPrecios, ListaPreciosItem
from app.modules.precios.schemas import (
    ListaPreciosCreate, ListaPreciosUpdate, ListaPreciosOut,
    ListaPreciosSimpleOut, SetPrecioRequest, ItemPrecioOut
)
from app.modules.usuarios.model import Usuario

router = APIRouter(prefix="/precios", tags=["Listas de precios"])


@router.get("/", response_model=List[ListaPreciosSimpleOut])
def listar_listas(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    return db.query(ListaPrecios).order_by(ListaPrecios.nombre).all()


@router.get("/{lista_id}", response_model=ListaPreciosOut)
def obtener_lista(
    lista_id: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    lista = db.query(ListaPrecios).filter(ListaPrecios.id == lista_id).first()
    if not lista:
        raise HTTPException(status_code=404, detail="Lista de precios no encontrada")
    return lista


@router.post("/", response_model=ListaPreciosOut, status_code=status.HTTP_201_CREATED)
def crear_lista(
    data: ListaPreciosCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    lista = ListaPrecios(**data.model_dump())
    db.add(lista)
    db.commit()
    db.refresh(lista)
    return lista


@router.patch("/{lista_id}", response_model=ListaPreciosOut)
def actualizar_lista(
    lista_id: str,
    data: ListaPreciosUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    lista = db.query(ListaPrecios).filter(ListaPrecios.id == lista_id).first()
    if not lista:
        raise HTTPException(status_code=404, detail="Lista de precios no encontrada")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(lista, field, value)

    db.commit()
    db.refresh(lista)
    return lista


@router.put("/{lista_id}/items", response_model=ItemPrecioOut)
def set_precio(
    lista_id: str,
    data: SetPrecioRequest,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    """Crea o actualiza el precio de un producto en la lista (upsert)"""
    lista = db.query(ListaPrecios).filter(ListaPrecios.id == lista_id).first()
    if not lista:
        raise HTTPException(status_code=404, detail="Lista de precios no encontrada")

    item = db.query(ListaPreciosItem).filter(
        ListaPreciosItem.lista_precios_id == lista_id,
        ListaPreciosItem.producto_id == str(data.producto_id),
    ).first()

    if item:
        item.precio = data.precio
    else:
        item = ListaPreciosItem(
            lista_precios_id=lista_id,
            producto_id=str(data.producto_id),
            precio=data.precio,
        )
        db.add(item)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{lista_id}/items/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_precio(
    lista_id: str,
    producto_id: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    item = db.query(ListaPreciosItem).filter(
        ListaPreciosItem.lista_precios_id == lista_id,
        ListaPreciosItem.producto_id == producto_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Precio no encontrado")

    db.delete(item)
    db.commit()
