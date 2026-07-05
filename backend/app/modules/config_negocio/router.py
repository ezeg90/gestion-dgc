from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.config_negocio.model import ConfigNegocio
from app.modules.config_negocio.schemas import ConfigNegocioOut, ConfigNegocioUpdate
from app.modules.usuarios.model import Usuario

router = APIRouter(prefix="/config-negocio", tags=["Configuración"])


def _get_or_create(db: Session) -> ConfigNegocio:
    config = db.query(ConfigNegocio).filter(ConfigNegocio.id == 1).first()
    if not config:
        # Red de seguridad por si el seed del SQL no se corrió — no debería pasar
        # en producción, pero evita un 500 feo si falta la fila.
        config = ConfigNegocio(id=1, aplica_iva=True, tasa_iva=21.00)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.get("/", response_model=ConfigNegocioOut)
def obtener_config(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    return _get_or_create(db)


@router.patch("/", response_model=ConfigNegocioOut)
def actualizar_config(
    data: ConfigNegocioUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    config = _get_or_create(db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(config, field, value)
    db.commit()
    db.refresh(config)
    return config
