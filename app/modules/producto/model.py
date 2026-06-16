# app/modules/producto/model.py
from typing import List, TYPE_CHECKING, Optional
from decimal import Decimal
from sqlmodel import SQLModel, Field, Relationship, Column, Numeric, TEXT
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime, timezone

from app.core.base import Base

# Contiene SOLO el modelo de tabla SQLModel de Producto.
# Los schemas Pydantic de entrada/salida viven en schemas.py.

if TYPE_CHECKING:
    from app.modules.categoria.model import Categoria
    from app.modules.ingrediente.model import Ingrediente


class UnidadMedida(Base, table=True):
    __tablename__ = "unidades_medida"

    nombre: str = Field(max_length=80, unique=True, nullable=False)
    abreviatura: str = Field(max_length=10, unique=True, nullable=False)
    tipo: str = Field(default="contable", max_length=20, nullable=False)


class ProductoCategoria(SQLModel, table=True):
    __tablename__ = "producto_categoria"

    producto_id: int = Field(foreign_key="productos.id", primary_key=True)
    categoria_id: int = Field(foreign_key="categorias.id", primary_key=True)
    es_principal: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)

    producto: Optional["Producto"] = Relationship(back_populates="categorias")
    categoria: Optional["Categoria"] = Relationship(back_populates="productos")


class ProductoIngrediente(SQLModel, table=True):
    __tablename__ = "producto_ingrediente"

    producto_id: int = Field(foreign_key="productos.id", primary_key=True)
    ingrediente_id: int = Field(foreign_key="ingredientes.id", primary_key=True)

    cantidad: Decimal = Field(
        default=Decimal("1.00"),
        ge=0,
        sa_column=Column(Numeric(10, 2), nullable=False),
    )

    unidad_medida_id: int | None = Field(default=None, foreign_key="unidades_medida.id")

    es_removible: bool = Field(default=False, nullable=False)

    producto: Optional["Producto"] = Relationship(back_populates="ingredientes")
    ingrediente: Optional["Ingrediente"] = Relationship(back_populates="productos")
    unidad_medida: Optional["UnidadMedida"] = Relationship()


# ──────────────────────────────────────────────
# Modelo principal
# ──────────────────────────────────────────────
class Producto(Base, table=True):
    __tablename__ = "productos"

    nombre: str = Field(max_length=150, nullable=False)
    descripcion: str = Field(nullable=False)
    precio_base: Decimal = Field(ge=0, sa_column=Column(Numeric(10, 2), nullable=False))
    imagenes_url: List[str] = Field(default_factory=list, sa_column=Column(ARRAY(TEXT), nullable=False))
    stock_cantidad: int = Field(default=0, ge=0, nullable=False)
    disponible: bool = Field(default=True, nullable=False)

    unidad_venta_id: int | None = Field(default=None, foreign_key="unidades_medida.id")

    # Relación con UnidadMedida
    unidad_venta: Optional["UnidadMedida"] = Relationship()

    # Relación N:N con Categoria a través de ProductoCategoria
    categorias: List["ProductoCategoria"] = Relationship(back_populates="producto")

    # Relación N:N con Ingrediente a través de ProductoIngrediente
    ingredientes: List["ProductoIngrediente"] = Relationship(back_populates="producto")
