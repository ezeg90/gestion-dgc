# Sistema de Gestión DGC

API REST para gestión de distribución, clientes y finanzas.

## Stack

- **Backend**: FastAPI + Python 3.12
- **Base de datos**: PostgreSQL 16 (Render)
- **ORM**: SQLAlchemy 2.0 + Alembic
- **Auth**: JWT con python-jose
- **Deploy**: Render (backend) + Vercel (frontend)

## Estructura

```
backend/
├── app/
│   ├── core/           # config, BD, auth, dependencies
│   └── modules/        # un módulo por dominio de negocio
│       ├── usuarios/
│       ├── clientes/
│       ├── productos/
│       ├── precios/
│       ├── pedidos/
│       ├── rutas/
│       ├── remitos/
│       ├── cobranzas/
│       ├── cuentas_corrientes/
│       ├── cheques/
│       ├── proveedores/
│       └── gastos/
├── Dockerfile
└── requirements.txt
```

## Levantar en local (Windows)

```bash
# 1. Clonar el repo
git clone https://github.com/ezeg90/gestion-dgc.git
cd gestion-dgc/backend

# 2. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
copy .env.example .env
# Editar .env con tus credenciales de Render

# 5. Levantar el servidor
uvicorn app.main:app --reload
```

Documentación disponible en: http://localhost:8000/docs

## Deploy en Render

- **Build command**: `pip install -r requirements.txt`
- **Start command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Variables de entorno**: `DATABASE_URL`, `SECRET_KEY`, `ENVIRONMENT=production`
