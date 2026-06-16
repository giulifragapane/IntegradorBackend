# app/modules/pedido/repository.py
from sqlmodel import Session, select
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app.core.repository import BaseRepository
from app.modules.pedido.model import Pedido


class PedidoRepository(BaseRepository[Pedido]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Pedido)

    def get_active_by_id(self, pedido_id: int) -> Pedido | None:
        return self.session.exec(
            select(Pedido)
            .options(selectinload(Pedido.detalles))
            .where(Pedido.id == pedido_id)
            .where(Pedido.deleted_at.is_(None))
        ).first()

    def get_active_by_id_and_usuario(self, pedido_id: int, usuario_id: int) -> Pedido | None:
        return self.session.exec(
            select(Pedido)
            .options(selectinload(Pedido.detalles))
            .where(Pedido.id == pedido_id)
            .where(Pedido.usuario_id == usuario_id)
            .where(Pedido.deleted_at.is_(None))
        ).first()

    def get_active_by_usuario(self, usuario_id: int, offset: int = 0, limit: int = 20) -> list[Pedido]:
        return list(
            self.session.exec(
                select(Pedido)
                .options(selectinload(Pedido.detalles))
                .where(Pedido.usuario_id == usuario_id)
                .where(Pedido.deleted_at.is_(None))
                .order_by(Pedido.created_at.desc())
                .offset(offset)
                .limit(limit)
            ).all()
        )

    def get_active_all(self, offset: int = 0, limit: int = 20) -> list[Pedido]:
        return list(
            self.session.exec(
                select(Pedido)
                .options(selectinload(Pedido.detalles))
                .where(Pedido.deleted_at.is_(None))
                .order_by(Pedido.created_at.desc())
                .offset(offset)
                .limit(limit)
            ).all()
        )

    def count_active_by_usuario(self, usuario_id: int) -> int:
        return self.session.exec(
            select(func.count())
            .select_from(Pedido)
            .where(Pedido.usuario_id == usuario_id)
            .where(Pedido.deleted_at.is_(None))
        ).one()

    def count_active_all(self) -> int:
        return self.session.exec(
            select(func.count())
            .select_from(Pedido)
            .where(Pedido.deleted_at.is_(None))
        ).one()

    def exists_active_by_direccion(self, direccion_id: int) -> bool:
        return (
            self.session.exec(
                select(Pedido)
                .where(Pedido.direccion_entrega_id == direccion_id)
                .where(Pedido.deleted_at.is_(None))
                .where(
                    Pedido.estado_codigo.notin_(
                        [
                            "ENTREGADO",
                            "CANCELADO",
                        ]
                    )
                )
            ).first()
            is not None
        )