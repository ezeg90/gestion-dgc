from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# Importar TODOS los modelos para que SQLAlchemy los registre al arrancar
from app.modules.usuarios.model import Usuario
from app.modules.clientes.model import Cliente
from app.modules.productos.model import Producto
from app.modules.precios.model import ListaPrecios, ListaPreciosItem
from app.modules.rutas.model import Ruta, RutaParada
from app.modules.pedidos.model import Pedido, PedidoItem
from app.modules.remitos.model import Remito, RemitoPedido
from app.modules.cuentas_corrientes.model import CuentaCorriente, MovimientoCuentaCorriente
from app.modules.cheques.model import ChequeEmitido
from app.modules.proveedores.model import Proveedor, CuentaCorrienteProveedor, MovimientoCCProveedor
from app.modules.gastos.model import Gasto

# Routers
from app.modules.usuarios.router import router as usuarios_router
from app.modules.clientes.router import router as clientes_router
from app.modules.productos.router import router as productos_router
from app.modules.precios.router import router as precios_router
from app.modules.pedidos.router import router as pedidos_router
from app.modules.remitos.router import router as remitos_router
from app.modules.cuentas_corrientes.router import router as cuentas_router
from app.modules.cheques.router import router as cheques_router
from app.modules.proveedores.router import router as proveedores_router
from app.modules.gastos.router import router as gastos_router

app = FastAPI(
    title="Sistema de Gestión DGC",
    description="API REST para gestión de distribución, clientes y finanzas",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

ALLOWED_ORIGINS = [
    "https://ezeg90.github.io",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(usuarios_router,  prefix="/api/v1")
app.include_router(clientes_router,  prefix="/api/v1")
app.include_router(productos_router, prefix="/api/v1")
app.include_router(precios_router,   prefix="/api/v1")
app.include_router(pedidos_router,   prefix="/api/v1")
app.include_router(remitos_router,   prefix="/api/v1")
app.include_router(cuentas_router,   prefix="/api/v1")
app.include_router(cheques_router,   prefix="/api/v1")
app.include_router(proveedores_router, prefix="/api/v1")
app.include_router(gastos_router,      prefix="/api/v1")

@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}
