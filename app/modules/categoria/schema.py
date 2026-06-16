# app/modules/categoria/schema.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# ── Base schema para la categoría, con campos comunes a creación y actualización
class CategoriaBase(BaseModel):
    nombre: str = Field(..., max_length=100) # nombre obligatorio, no puede ser nulo, debe ser único y su longitud máxima es de 100 caracteres
    descripcion: str
    imagen_url: str = ""
    color: Optional[str] = None
    parent_id: Optional[int] = None

# ── Entrada ───────────────────────────────────────────────────────────────────
class CategoriaCreate(CategoriaBase):
    pass

class CategoriaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=100)
    descripcion: Optional[str] = None
    imagen_url: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[int] = None

# ── Salida ───────────────────────────────────────────────────────────────────
class CategoriaRead(CategoriaBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class CategoriaList(BaseModel):
    data: List[CategoriaRead]
    total: int