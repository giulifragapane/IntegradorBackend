# app/modules/direccion/schema.py
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class DireccionBase(BaseModel):
    alias: Optional[str] = Field(default=None, max_length=50)
    linea1: str = Field(..., min_length=1)
    linea2: Optional[str] = None
    ciudad: str = Field(..., max_length=100)
    provincia: str = Field(..., max_length=100)
    codigo_postal: Optional[str] = Field(default=None, max_length=10)
    es_principal: bool = False


class DireccionCreate(DireccionBase):
    pass


class DireccionUpdate(BaseModel):
    alias: Optional[str] = Field(default=None, max_length=50)
    linea1: Optional[str] = Field(default=None, min_length=1)
    linea2: Optional[str] = None
    ciudad: Optional[str] = Field(default=None, max_length=100)
    provincia: Optional[str] = Field(default=None, max_length=100)
    codigo_postal: Optional[str] = Field(default=None, max_length=10)
    es_principal: Optional[bool] = None


class DireccionRead(DireccionBase):
    id: int
    usuario_id: int
    model_config = ConfigDict(from_attributes=True)


class DireccionList(BaseModel):
    data: List[DireccionRead]
    total: int