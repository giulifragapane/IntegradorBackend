# app/modules/direccion/unit_of_work.py
from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.direccion.repository import DireccionRepository
from app.modules.pedido.repository import PedidoRepository


class DireccionUnitOfWork(UnitOfWork):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.direcciones = DireccionRepository(session)
        self.pedidos = PedidoRepository(session)