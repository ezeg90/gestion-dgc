import uuid
from sqlalchemy import Column, String, Numeric, Text, Enum as SAEnum, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class CondicionIvaProveedor(str, enum.Enum):
    responsable_inscripto = "responsable_inscripto"
    monotributo           = "monotributo"
    exento                = "exento"
    consumidor_final      = "consumidor_final"


class EstadoProveedor(str, enum.Enum):
    activo   = "activo"
    inactivo = "inactivo"


class EstadoCCProveedor(str, enum.Enum):
    activa     = "activa"
    suspendida = "suspendida"
    bloqueada  = "bloqueada"


class TipoMovimientoProveedor(str, enum.Enum):
    debito  = "debito"   # DGC le debe al proveedor
    credito = "credito"  # DGC paga al proveedor


class Proveedor(Base):
    __tablename__ = "proveedores"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre        = Column(String(200), nullable=False)
    cuit          = Column(String(20),  unique=True, nullable=True)
    telefono      = Column(String(50),  nullable=True)
    email         = Column(String(150), nullable=True)
    direccion     = Column(String(200), nullable=True)
    localidad     = Column(String(100), nullable=True)
    condicion_iva = Column(SAEnum(CondicionIvaProveedor, name="condicion_iva_proveedor"),
                           nullable=False, default=CondicionIvaProveedor.responsable_inscripto)
    rubro         = Column(String(100), nullable=True)
    cbu           = Column(String(22),  nullable=True)
    alias         = Column(String(100), nullable=True)
    banco         = Column(String(100), nullable=True)
    contacto      = Column(String(150), nullable=True)
    estado        = Column(SAEnum(EstadoProveedor, name="estado_proveedor"),
                           nullable=False, default=EstadoProveedor.activo)
    observaciones = Column(Text, nullable=True)
    created_at    = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at    = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    cuenta_corriente = relationship("CuentaCorrienteProveedor", back_populates="proveedor",
                                    uselist=False, cascade="all, delete-orphan")
    gastos           = relationship("Gasto", back_populates="proveedor")


class CuentaCorrienteProveedor(Base):
    __tablename__ = "cuentas_corrientes_proveedores"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proveedor_id   = Column(UUID(as_uuid=True),
                            nullable=False, unique=True)
    saldo_actual   = Column(Numeric(14, 2), nullable=False, default=0)
    limite_credito = Column(Numeric(14, 2), nullable=False, default=0)
    estado         = Column(SAEnum(EstadoCCProveedor, name="estado_cc_proveedor"),
                            nullable=False, default=EstadoCCProveedor.activa)
    created_at     = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at     = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    proveedor  = relationship("Proveedor", back_populates="cuenta_corriente")
    movimientos = relationship("MovimientoCCProveedor", back_populates="cuenta",
                               order_by="MovimientoCCProveedor.fecha.desc()",
                               cascade="all, delete-orphan")


class MovimientoCCProveedor(Base):
    __tablename__ = "movimientos_cc_proveedores"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cuenta_id           = Column(UUID(as_uuid=True), nullable=False)
    tipo                = Column(SAEnum(TipoMovimientoProveedor, name="tipo_movimiento_proveedor"),
                                 nullable=False)
    monto               = Column(Numeric(14, 2), nullable=False)
    descripcion         = Column(Text, nullable=True)
    referencia_gasto_id = Column(UUID(as_uuid=True), nullable=True)
    fecha               = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    created_at          = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    cuenta = relationship("CuentaCorrienteProveedor", back_populates="movimientos")