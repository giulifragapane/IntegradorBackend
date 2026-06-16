# app/modules/usuario/model.py
from datetime import datetime, timezone

from sqlmodel import Field, Relationship, SQLModel

from app.core.base import Base


class Rol(SQLModel, table=True):
    __tablename__ = "roles"

    codigo: str = Field(primary_key=True, max_length=30)
    nombre: str = Field(unique=True, max_length=50, nullable=False)
    descripcion: str | None = None

    usuarios: list["UsuarioRol"] = Relationship(back_populates="rol")


class UsuarioRol(SQLModel, table=True):
    __tablename__ = "usuarios_roles"

    usuario_id: int = Field(foreign_key="usuarios.id", primary_key=True)
    rol_codigo: str = Field(foreign_key="roles.codigo", primary_key=True, max_length=30)
    asignado_por_id: int | None = Field(default=None, foreign_key="usuarios.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expired_at: datetime | None = Field(default=None, nullable=True)

    usuario: "Usuario" = Relationship(
        back_populates="roles",
        sa_relationship_kwargs={
            "foreign_keys": "[UsuarioRol.usuario_id]",
        },
    )

    rol: Rol = Relationship(back_populates="usuarios")


class DireccionEntrega(Base, table=True):
    __tablename__ = "direcciones_entrega"

    usuario_id: int = Field(foreign_key="usuarios.id")

    alias: str | None = Field(default=None, max_length=50)
    linea1: str
    linea2: str | None = None
    ciudad: str = Field(max_length=100)
    provincia: str = Field(max_length=100)
    codigo_postal: str | None = Field(default=None, max_length=10)
    es_principal: bool = Field(default=False)

    usuario: "Usuario" = Relationship(back_populates="direcciones")


class Usuario(Base, table=True):
    __tablename__ = "usuarios"

    nombre: str = Field(max_length=80, nullable=False)
    apellido: str = Field(max_length=80, nullable=False)
    email: str = Field(index=True, unique=True, nullable=False)
    celular: str | None = Field(default=None, max_length=20)
    password_hash: str = Field(nullable=False)
    disabled: bool = Field(default=False)

    roles: list["UsuarioRol"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={
            "foreign_keys": "[UsuarioRol.usuario_id]",
            "cascade": "all, delete-orphan",
        },
    )

    direcciones: list["DireccionEntrega"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
        },
    )
