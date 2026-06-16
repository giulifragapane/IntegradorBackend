# app/modules/pago/repository.py
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from app.modules.pedido.model import Pago, Pedido


class PagoRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_pedido_active_by_id(self, pedido_id: int) -> Pedido | None:
        return self.session.exec(
            select(Pedido)
            .options(selectinload(Pedido.detalles), selectinload(Pedido.pagos))
            .where(Pedido.id == pedido_id)
            .where(Pedido.deleted_at.is_(None))
        ).first()

    def get_pago_by_pedido(self, pedido_id: int) -> Pago | None:
        return self.session.exec(
            select(Pago).where(Pago.pedido_id == pedido_id)
        ).first()

    def get_pago_by_external_reference(self, external_reference: str) -> Pago | None:
        return self.session.exec(
            select(Pago).where(Pago.external_reference == external_reference)
        ).first()

    def get_pago_by_mp_payment_id(self, mp_payment_id: int) -> Pago | None:
        return self.session.exec(
            select(Pago).where(Pago.mp_payment_id == mp_payment_id)
        ).first()

    def save(self, pago: Pago) -> Pago:
        self.session.add(pago)
        self.session.flush()
        self.session.refresh(pago)
        return pago
