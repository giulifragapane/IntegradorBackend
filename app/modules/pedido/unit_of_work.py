# app/modules/pedido/unit_of_work.py
from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.direccion.repository import DireccionRepository
from app.modules.pedido.repository import PedidoRepository
from app.modules.producto.repository import ProductoRepository


class PedidoUnitOfWork(UnitOfWork):
    """
    UoW del módulo pedidos.
    Coordina pedidos, productos y direcciones dentro de la misma transacción.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.pedidos = PedidoRepository(session)
        self.productos = ProductoRepository(session)
        self.direcciones = DireccionRepository(session)