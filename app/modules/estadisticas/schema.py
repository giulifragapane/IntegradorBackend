# app/modules/estadisticas/schema.py
from decimal import Decimal
from pydantic import BaseModel


class ResumenResponse(BaseModel):
    ventas_hoy: Decimal
    ingresos_hoy: Decimal
    ingresos_mes_actual: Decimal
    ticket_promedio: Decimal
    pedidos_activos: int
    pedidos_total: int


class VentasPeriodoItem(BaseModel):
    periodo: str
    cantidad_pedidos: int
    total_vendido: Decimal


class ProductoTopItem(BaseModel):
    producto_id: int
    producto_nombre: str
    cantidad_vendida: int
    ingresos_total: Decimal


class PedidosEstadoItem(BaseModel):
    estado_codigo: str
    estado_nombre: str
    cantidad: int


class IngresosFormaPagoItem(BaseModel):
    forma_pago_codigo: str
    forma_pago_nombre: str
    ingresos_total: Decimal
    cantidad_pedidos: int
