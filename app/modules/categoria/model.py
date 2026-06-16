# app/modules/categoria/model.py
from typing import Optional, TYPE_CHECKING, List
from sqlmodel import Field, Relationship
from sqlalchemy import BigInteger, Column, ForeignKey

from app.core.base import Base

# Contiene SOLO el modelo de tabla SQLModel de Categoría.
# Los schemas Pydantic de entrada/salida viven en schemas.py.

if TYPE_CHECKING:
    from app.modules.producto.model import ProductoCategoria

# Define la tabla SQLModel con table=True para que se cree en la base de datos
class Categoria(Base, table=True):

    __tablename__ = "categorias"

    nombre: str = Field(max_length=100, unique=True, nullable=False) #nombre obligatorio, no puede ser nulo, debe ser único y su longitud máxima es de 100 caracteres
    descripcion: str = Field(nullable=False) #descripción obligatoria, no puede ser nula, se espera que contenga información detallada sobre la categoría
    imagen_url: str = Field(nullable=False) #url obligatoria, no puede ser nula
    color: Optional[str] = Field(default=None, nullable=True)
    
    parent_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            ForeignKey("categorias.id", ondelete="SET NULL"),
            nullable=True
        )
    )

    # Relación recursiva para categorías padre-hijo
    parent: Optional["Categoria"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Categoria.id"}
    )

    children: List["Categoria"] = Relationship(
        back_populates="parent"
    )

    productos: list["ProductoCategoria"] = Relationship(back_populates="categoria")