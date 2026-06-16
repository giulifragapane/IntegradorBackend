# app/modules/ingrediente/schema.py
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class IngredienteBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    descripcion: str
    es_alergeno: bool = False
    stock_cantidad: int = Field(default=0, ge=0)


# ── Entrada ───────────────────────────────────────────────────────────────────
class IngredienteCreate(IngredienteBase):
    pass


class IngredienteUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=100)
    descripcion: Optional[str] = None
    es_alergeno: Optional[bool] = None
    stock_cantidad: Optional[int] = Field(None, ge=0)


# ── Salida ───────────────────────────────────────────────────────────────────
class IngredienteRead(IngredienteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class IngredienteList(BaseModel):
    data: List[IngredienteRead]
    total: int