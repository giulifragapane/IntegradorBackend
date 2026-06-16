# app/modules/ingrediente/model.py
from typing import List, TYPE_CHECKING
from sqlmodel import Field, Relationship

from app.core.base import Base
from app.modules.producto.model import ProductoIngrediente

if TYPE_CHECKING:
    from app.modules.producto.model import ProductoIngrediente


class Ingrediente(Base, table=True):
    __tablename__ = "ingredientes"

    nombre: str = Field(max_length=100, unique=True, nullable=False)
    descripcion: str = Field(nullable=False)
    es_alergeno: bool = Field(default=False, nullable=False)
    stock_cantidad: int = Field(default=0, ge=0, nullable=False)

    productos: List["ProductoIngrediente"] = Relationship(back_populates="ingrediente")