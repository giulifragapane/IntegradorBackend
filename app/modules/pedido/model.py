# app/modules/pedido/model.py
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Column, JSON, Numeric
from sqlmodel import Field, Relationship, SQLModel

from app.core.base import Base


class EstadoPedido(SQLModel, table=True):
    __tablename__ = "estados_pedido"

    codigo: str = Field(primary_key=True, max_length=30)
    nombre: str = Field(max_length=80, nullable=False)
    descripcion: str | None = Field(default=None)
    orden: int = Field(default=0, nullable=False)
    es_terminal: bool = Field(default=False, nullable=False)


class FormaPago(SQLModel, table=True):
    __tablename__ = "formas_pago"

    codigo: str = Field(primary_key=True, max_length=30)
    nombre: str = Field(max_length=80, nullable=False)
    descripcion: str | None = Field(default=None)
    habilitado: bool = Field(default=True, nullable=False)


class Pedido(Base, table=True):
    __tablename__ = "pedidos"

    usuario_id: int = Field(foreign_key="usuarios.id", nullable=False)
    direccion_entrega_id: int | None = Field(default=None, foreign_key="direcciones_entrega.id")

    estado_codigo: str = Field(
        default="PENDIENTE",
        foreign_key="estados_pedido.codigo",
        nullable=False,
        max_length=30,
    )

    forma_pago_codigo: str = Field(
        foreign_key="formas_pago.codigo",
        nullable=False,
        max_length=30,
    )

    subtotal: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        sa_column=Column(Numeric(10, 2), nullable=False),
    )

    descuento: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        sa_column=Column(Numeric(10, 2), nullable=False),
    )

    costo_envio: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        sa_column=Column(Numeric(10, 2), nullable=False),
    )

    total: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        sa_column=Column(Numeric(10, 2), nullable=False),
    )

    notas: str | None = Field(default=None)

    detalles: list["DetallePedido"] = Relationship(
        back_populates="pedido",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    historial_estados: list["HistorialEstadoPedido"] = Relationship(
        back_populates="pedido",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    pagos: list["Pago"] = Relationship(
        back_populates="pedido",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    estado_rel: Optional["EstadoPedido"] = Relationship()
    forma_pago_rel: Optional["FormaPago"] = Relationship()

    @property
    def estado(self) -> str:
        return self.estado_codigo

    @property
    def forma_pago(self) -> str:
        return self.forma_pago_codigo


class DetallePedido(Base, table=True):
    __tablename__ = "detalle_pedidos"

    pedido_id: int | None = Field(default=None, foreign_key="pedidos.id")
    producto_id: int = Field(foreign_key="productos.id", nullable=False)

    cantidad: int = Field(gt=0, nullable=False)

    personalizacion: list[int] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )

    producto_nombre: str = Field(max_length=150, nullable=False)
    precio_unitario: Decimal = Field(
        ge=0,
        sa_column=Column(Numeric(10, 2), nullable=False),
    )
    subtotal: Decimal = Field(
        ge=0,
        sa_column=Column(Numeric(10, 2), nullable=False),
    )

    pedido: Optional["Pedido"] = Relationship(back_populates="detalles")


class HistorialEstadoPedido(Base, table=True):
    __tablename__ = "historial_estados_pedido"

    pedido_id: int = Field(foreign_key="pedidos.id", nullable=False)

    estado_desde_codigo: str | None = Field(
        default=None,
        foreign_key="estados_pedido.codigo",
        max_length=30,
    )

    estado_hacia_codigo: str = Field(
        foreign_key="estados_pedido.codigo",
        nullable=False,
        max_length=30,
    )

    observacion: str | None = Field(default=None)

    pedido: Optional["Pedido"] = Relationship(back_populates="historial_estados")


class Pago(Base, table=True):
    __tablename__ = "pagos"

    pedido_id: int = Field(foreign_key="pedidos.id", nullable=False)

    forma_pago_codigo: str = Field(
        foreign_key="formas_pago.codigo",
        nullable=False,
        max_length=30,
    )

    mp_payment_id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, unique=True, index=True, nullable=True),
    )
    mp_status: str = Field(default="pending", max_length=30, nullable=False)
    mp_status_detail: str | None = Field(default=None, max_length=100)

    transaction_amount: Decimal = Field(
        ge=0,
        sa_column=Column(Numeric(10, 2), nullable=False),
    )

    payment_method_id: str | None = Field(default=None, max_length=50)

    external_reference: str = Field(
        index=True,
        unique=True,
        nullable=False,
        max_length=100,
    )

    idempotency_key: str = Field(
        index=True,
        unique=True,
        nullable=False,
        max_length=100,
    )

    pedido: Optional["Pedido"] = Relationship(back_populates="pagos")
    forma_pago_rel: Optional["FormaPago"] = Relationship()
