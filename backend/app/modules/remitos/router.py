from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from datetime import date

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.remitos.model import Remito, RemitoPedido
from app.modules.remitos.schemas import RemitoCreate, RemitoUpdate, RemitoOut, RemitoDetalleOut, RemitoItemOut
from app.modules.pedidos.model import Pedido, PedidoItem
from app.modules.clientes.model import Cliente
from app.modules.productos.model import Producto
from app.modules.usuarios.model import Usuario

router = APIRouter(prefix="/remitos", tags=["Remitos"])


def generar_numero(db: Session) -> str:
    """Genera número correlativo REM-00001"""
    ultimo = db.query(Remito).order_by(Remito.created_at.desc()).first()
    if not ultimo or not ultimo.numero:
        return "REM-00001"
    try:
        n = int(ultimo.numero.split("-")[1]) + 1
    except Exception:
        n = 1
    return f"REM-{n:05d}"


@router.get("/", response_model=List[RemitoOut])
def listar_remitos(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    remitos = db.query(Remito).order_by(Remito.created_at.desc()).all()
    result = []
    for r in remitos:
        r_out = RemitoOut(
            id=r.id, numero=r.numero, cliente_id=r.cliente_id,
            usuario_id=r.usuario_id, fecha=r.fecha, estado=r.estado,
            observaciones=r.observaciones, created_at=r.created_at,
            pedido_ids=[rp.pedido_id for rp in r.remito_pedidos]
        )
        result.append(r_out)
    return result


@router.get("/{remito_id}", response_model=RemitoDetalleOut)
def obtener_remito(
    remito_id: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    remito = db.query(Remito).filter(Remito.id == remito_id).first()
    if not remito:
        raise HTTPException(status_code=404, detail="Remito no encontrado")

    cliente = db.query(Cliente).filter(Cliente.id == remito.cliente_id).first()

    # Consolidar items de todos los pedidos del remito
    items_map = {}
    forma_pago = "cuenta_corriente"
    for rp in remito.remito_pedidos:
        pedido = db.query(Pedido).filter(Pedido.id == rp.pedido_id).first()
        if pedido:
            forma_pago = pedido.forma_pago
            for item in pedido.items:
                producto = db.query(Producto).filter(Producto.id == item.producto_id).first()
                if not producto:
                    continue
                key = str(item.producto_id)
                if key in items_map:
                    items_map[key]["cantidad"] += Decimal(str(item.cantidad))
                    items_map[key]["subtotal"] += Decimal(str(item.subtotal))
                else:
                    items_map[key] = {
                        "producto_nombre": producto.nombre,
                        "producto_unidad": producto.unidad_medida,
                        "cantidad":        Decimal(str(item.cantidad)),
                        "precio_unitario": Decimal(str(item.precio_unitario)),
                        "subtotal":        Decimal(str(item.subtotal)),
                    }

    items = [RemitoItemOut(**v) for v in items_map.values()]
    total = sum(i.subtotal for i in items)

    return RemitoDetalleOut(
        id=remito.id, numero=remito.numero, fecha=remito.fecha,
        estado=remito.estado, observaciones=remito.observaciones,
        cliente_nombre=cliente.razon_social if cliente else "—",
        cliente_direccion=cliente.direccion if cliente else None,
        cliente_localidad=cliente.localidad if cliente else None,
        cliente_cuit=cliente.cuit if cliente else None,
        cliente_condicion_iva=cliente.condicion_iva if cliente else "—",
        items=items, total=total, forma_pago=forma_pago,
        pedido_ids=[rp.pedido_id for rp in remito.remito_pedidos]
    )


@router.post("/", response_model=RemitoOut, status_code=status.HTTP_201_CREATED)
def crear_remito(
    data: RemitoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # Validar que todos los pedidos existen y son del mismo cliente
    pedidos = []
    cliente_id = None
    for pid in data.pedido_ids:
        pedido = db.query(Pedido).filter(Pedido.id == str(pid)).first()
        if not pedido:
            raise HTTPException(status_code=404, detail=f"Pedido {pid} no encontrado")
        if pedido.estado not in ("entregado", "pendiente", "en_ruta"):
            raise HTTPException(
                status_code=400,
                detail=f"El pedido {pid} está en estado '{pedido.estado}' y no puede incluirse en un remito"
            )
        if cliente_id is None:
            cliente_id = str(pedido.cliente_id)
        elif str(pedido.cliente_id) != cliente_id:
            raise HTTPException(
                status_code=400,
                detail="Todos los pedidos del remito deben ser del mismo cliente"
            )
        # Verificar que no tenga ya un remito
        ya_en_remito = db.query(RemitoPedido).filter(RemitoPedido.pedido_id == str(pid)).first()
        if ya_en_remito:
            raise HTTPException(
                status_code=400,
                detail=f"El pedido {pid} ya tiene un remito asignado"
            )
        pedidos.append(pedido)

    numero = generar_numero(db)
    remito = Remito(
        numero=numero,
        cliente_id=cliente_id,
        usuario_id=str(current_user.id),
        fecha=data.fecha or date.today(),
        observaciones=data.observaciones,
    )
    db.add(remito)
    db.flush()  # para obtener el ID antes del commit

    for pedido in pedidos:
        db.add(RemitoPedido(remito_id=str(remito.id), pedido_id=str(pedido.id)))

    # Generar débito automático en cuenta corriente
    _registrar_debito_por_remito(remito, pedidos, db)

    db.commit()
    db.refresh(remito)

    return RemitoOut(
        id=remito.id, numero=remito.numero, cliente_id=remito.cliente_id,
        usuario_id=remito.usuario_id, fecha=remito.fecha, estado=remito.estado,
        observaciones=remito.observaciones, created_at=remito.created_at,
        pedido_ids=[rp.pedido_id for rp in remito.remito_pedidos]
    )


@router.patch("/{remito_id}", response_model=RemitoOut)
def actualizar_remito(
    remito_id: str,
    data: RemitoUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    remito = db.query(Remito).filter(Remito.id == remito_id).first()
    if not remito:
        raise HTTPException(status_code=404, detail="Remito no encontrado")
    if remito.estado == "anulado":
        raise HTTPException(status_code=400, detail="No se puede modificar un remito anulado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(remito, field, value)

    db.commit()
    db.refresh(remito)

    return RemitoOut(
        id=remito.id, numero=remito.numero, cliente_id=remito.cliente_id,
        usuario_id=remito.usuario_id, fecha=remito.fecha, estado=remito.estado,
        observaciones=remito.observaciones, created_at=remito.created_at,
        pedido_ids=[rp.pedido_id for rp in remito.remito_pedidos]
    )


def _registrar_debito_por_remito(remito, pedidos, db):
    """Genera automáticamente el débito en cuenta corriente al emitir un remito"""
    from app.modules.cuentas_corrientes.model import CuentaCorriente, MovimientoCuentaCorriente
    from decimal import Decimal

    cc = db.query(CuentaCorriente).filter(
        CuentaCorriente.cliente_id == str(remito.cliente_id)
    ).first()
    if not cc:
        return  # cliente sin cuenta corriente, no hacer nada

    total = sum(
        Decimal(str(item.subtotal))
        for pedido in pedidos
        for item in pedido.items
    )
    if total <= 0:
        return

    mov = MovimientoCuentaCorriente(
        cuenta_corriente_id=str(cc.id),
        tipo="debito",
        monto=total,
        referencia_tipo="remito",
        referencia_id=remito.id,
        descripcion=f"Remito {remito.numero}",
        usuario_id=str(remito.usuario_id) if remito.usuario_id else None,
    )
    db.add(mov)

    # Recalcular saldo
    movs = db.query(MovimientoCuentaCorriente).filter(
        MovimientoCuentaCorriente.cuenta_corriente_id == cc.id
    ).all()
    cc.saldo_actual = sum(
        Decimal(str(m.monto)) if m.tipo == "debito" else -Decimal(str(m.monto))
        for m in movs
    ) + total  # incluir el que acabamos de agregar
    db.add(cc)
