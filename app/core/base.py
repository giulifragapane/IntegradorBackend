# app/core/base.py
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone

"""
---MODELO BASE DE TODOS LOS MODELOS (Plantilla)---
Clase base para los modelos SQLModel, con campos comunes como id, created_at, updated_at y deleted_at.
Es la clase de la que heredan todos los modelos de la aplicación para evitar repetir estos campos en cada modelo.

"""
class Base(SQLModel):
    id: int = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),nullable=False)
    deleted_at: datetime | None = Field(default=None,nullable=True)

"""
Cada vez que creás un modelo (ej: Producto, Categoría):
- Heredás de Base: class Producto(Base, table=True)
- Automáticamente tenés un id autoincremental, timestamps de creación/actualización, y un campo para soft delete.
- Esto te ahorra repetir código y mantiene consistencia en todos los modelos.
"""