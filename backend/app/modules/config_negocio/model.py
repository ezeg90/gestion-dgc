from sqlalchemy import Column, SmallInteger, String, Boolean, Numeric, CheckConstraint

from app.core.database import Base


class ConfigNegocio(Base):
    __tablename__ = "config_negocio"

    id              = Column(SmallInteger, primary_key=True, default=1)
    nombre_fantasia = Column(String(150), nullable=True)
    aplica_iva      = Column(Boolean, nullable=False, default=True)
    tasa_iva        = Column(Numeric(5, 2), nullable=False, default=21.00)

    __table_args__ = (
        CheckConstraint("id = 1", name="chk_config_negocio_singleton"),
    )
