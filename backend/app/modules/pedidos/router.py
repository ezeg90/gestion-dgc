from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.pedidos.model import Pedido, PedidoItem
from app.modules.pedidos.schemas import PedidoCreate, PedidoUpdate, PedidoOut, PedidoListOut
from app.modules.clientes.model import Cliente
from app.modules.productos.model import Producto
from app.modules.precios.model import ListaPreciosItem
from app.modules.usuarios.model import Usuario

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


def resolver_precio(
    producto_id: str,
    lista_precios_id: Optional[str],
    precio_manual: Optional[Decimal],
    db: Session,
) -> Decimal:
    """
    Resuelve el precio a aplicar con esta cascada:
    1. Precio manual enviado en el item (precio especial por pedido)
    2. Precio de la lista asignada al cliente
    3. Error si no hay precio disponible
    """
    if precio_manual is not None:
        return precio_manual

    if lista_precios_id:
        item = db.query(ListaPreciosItem).filter(
            ListaPreciosItem.lista_precios_id == lista_precios_id,
            ListaPreciosItem.producto_id == producto_id,
        ).first()
        if item:
            return Decimal(str(item.precio))

    raise HTTPException(
        status_code=422,
        detail=f"No hay precio definido para el producto {producto_id}. "
               "Asignale una lista de precios al cliente o enviá el precio manualmente.",
    )


@router.get("/", response_model=List[PedidoListOut])
def listar_pedidos(
    cliente_id: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    query = db.query(Pedido)

    if cliente_id:
        query = query.filter(Pedido.cliente_id == cliente_id)
    if estado:
        query = query.filter(Pedido.estado == estado)
    if fecha_desde:
        query = query.filter(Pedido.fecha_pedido >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Pedido.fecha_pedido <= fecha_hasta)

    return query.order_by(Pedido.created_at.desc()).all()


@router.get("/{pedido_id}", response_model=PedidoOut)
def obtener_pedido(
    pedido_id: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return pedido


@router.post("/", response_model=PedidoOut, status_code=status.HTTP_201_CREATED)
def crear_pedido(
    data: PedidoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # Verificar cliente existe y está activo
    cliente = db.query(Cliente).filter(
        Cliente.id == str(data.cliente_id),
        Cliente.estado == "activo",
    ).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado o inactivo")

    # Construir items resolviendo precios
    pedido_items = []
    total = Decimal("0")

    for item_data in data.items:
        producto = db.query(Producto).filter(
            Producto.id == str(item_data.producto_id),
            Producto.activo == True,
        ).first()
        if not producto:
            raise HTTPException(
                status_code=404,
                detail=f"Producto {item_data.producto_id} no encontrado o inactivo",
            )

        precio = resolver_precio(
            producto_id=str(item_data.producto_id),
            lista_precios_id=str(cliente.lista_precios_id) if cliente.lista_precios_id else None,
            precio_manual=item_data.precio_unitario,
            db=db,
        )

        subtotal = Decimal(str(item_data.cantidad)) * precio
        total += subtotal

        pedido_items.append(PedidoItem(
            producto_id=str(item_data.producto_id),
            cantidad=item_data.cantidad,
            precio_unitario=precio,
            subtotal=subtotal,
            observacion=None,
        ))

    # Crear el pedido
    pedido = Pedido(
        cliente_id=str(data.cliente_id),
        usuario_id=str(current_user.id),
        fecha_entrega=data.fecha_entrega,
        observaciones=data.observaciones,
        total=total,
        items=pedido_items,
    )
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return pedido


@router.patch("/{pedido_id}", response_model=PedidoOut)
def actualizar_pedido(
    pedido_id: str,
    data: PedidoUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    # No permitir editar pedidos ya entregados o cancelados
    if pedido.estado in ("entregado", "cancelado"):
        raise HTTPException(
            status_code=400,
            detail=f"No se puede modificar un pedido en estado '{pedido.estado}'",
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(pedido, field, value)

    db.commit()
    db.refresh(pedido)
    return pedido


@router.delete("/{pedido_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancelar_pedido(
    pedido_id: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    """Cancela un pedido — solo si está en estado pendiente"""
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    if pedido.estado != "pendiente":
        raise HTTPException(
            status_code=400,
            detail=f"Solo se pueden cancelar pedidos pendientes. Estado actual: '{pedido.estado}'",
        )

    pedido.estado = "cancelado"
    db.commit()
