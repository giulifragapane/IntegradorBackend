# app/modules/pedido/schema.py
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Entrada ───────────────────────────────────────────────────────────────────
class DetallePedidoCreate(BaseModel):
    producto_id: int
    cantidad: int = Field(..., gt=0)
    personalizacion: List[int] = Field(default_factory=list)


class PedidoCreate(BaseModel):
    direccion_entrega_id: Optional[int] = None
    forma_pago: str = Field(..., max_length=30)
    notas: Optional[str] = None
    descuento: Decimal = Field(default=Decimal("0.00"), ge=0)
    costo_envio: Decimal = Field(default=Decimal("0.00"), ge=0)
    detalles: List[DetallePedidoCreate] = Field(..., min_length=1)

    @field_validator("descuento", "costo_envio")
    @classmethod
    def redondear_importes(cls, value: Decimal) -> Decimal:
        return round(value, 2)


class PedidoEstadoUpdate(BaseModel):
    estado: str = Field(..., max_length=30)


# ── Salida ───────────────────────────────────────────────────────────────────
class DetallePedidoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    cantidad: int
    personalizacion: List[int]
    producto_nombre: str
    precio_unitario: Decimal
    subtotal: Decimal


class PedidoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    direccion_entrega_id: Optional[int]
    estado: str
    forma_pago: str
    subtotal: Decimal
    descuento: Decimal
    costo_envio: Decimal
    total: Decimal
    notas: Optional[str]
    detalles: List[DetallePedidoRead] = Field(default_factory=list)


class PedidoList(BaseModel):
    data: List[PedidoRead]
    total: int
