from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.modules.usuarios.router import router as usuarios_router
from app.modules.clientes.router import router as clientes_router
from app.modules.productos.router import router as productos_router
from app.modules.precios.router import router as precios_router
from app.modules.pedidos.router import router as pedidos_router

app = FastAPI(
    title="Sistema de Gestión DGC",
    description="API REST para gestión de distribución, clientes y finanzas",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else [
        "https://tu-frontend.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(usuarios_router,  prefix="/api/v1")
app.include_router(clientes_router,  prefix="/api/v1")
app.include_router(productos_router, prefix="/api/v1")
app.include_router(precios_router,   prefix="/api/v1")
app.include_router(pedidos_router,   prefix="/api/v1")


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}

