from sqlmodel import Session, select

from app.core.repository import BaseRepository
from app.modules.usuario.model import DireccionEntrega


class DireccionRepository(BaseRepository[DireccionEntrega]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, DireccionEntrega)
        
    def get_active_by_usuario(self, usuario_id: int, offset: int = 0, limit: int = 20) -> list[DireccionEntrega]:
        return list(
            self.session.exec(
                select(DireccionEntrega)
                .where(DireccionEntrega.usuario_id == usuario_id)
                .where(DireccionEntrega.deleted_at.is_(None))
                .offset(offset)
                .limit(limit)
            ).all()
        )

    def get_active_by_id_and_usuario(self, direccion_id: int, usuario_id: int) -> DireccionEntrega | None:
        return self.session.exec(
            select(DireccionEntrega)
            .where(DireccionEntrega.id == direccion_id)
            .where(DireccionEntrega.usuario_id == usuario_id)
            .where(DireccionEntrega.deleted_at.is_(None))
        ).first()

    def get_principal_by_usuario(self, usuario_id: int) -> DireccionEntrega | None:
        return self.session.exec(
            select(DireccionEntrega)
            .where(DireccionEntrega.usuario_id == usuario_id)
            .where(DireccionEntrega.es_principal.is_(True))
            .where(DireccionEntrega.deleted_at.is_(None))
        ).first()

    def unset_principal_by_usuario(self, usuario_id: int) -> None:
        direcciones = self.session.exec(
            select(DireccionEntrega)
            .where(DireccionEntrega.usuario_id == usuario_id)
            .where(DireccionEntrega.es_principal.is_(True))
            .where(DireccionEntrega.deleted_at.is_(None))
        ).all()

        for direccion in direcciones:
            direccion.es_principal = False
            self.session.add(direccion)

        self.session.flush()

    def count_active_by_usuario(self, usuario_id: int) -> int:
        return len(self.get_active_by_usuario(usuario_id=usuario_id, offset=0, limit=100000))