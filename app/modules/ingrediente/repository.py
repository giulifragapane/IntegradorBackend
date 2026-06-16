# app/modules/ingrediente/repository.py
from sqlmodel import select, Session
from sqlalchemy import func
from app.core.repository import BaseRepository
from app.modules.ingrediente.model import Ingrediente


class IngredienteRepository(BaseRepository[Ingrediente]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Ingrediente)

    def get_by_nombre(self, nombre: str) -> Ingrediente | None:
        return self.session.exec(
            select(Ingrediente).where(Ingrediente.nombre == nombre)
    ).first()

    def get_alergenos(self, offset: int = 0, limit: int = 20) -> list[Ingrediente]:
        
        return list(
            self.session.exec(
                select(Ingrediente)
                .where(Ingrediente.es_alergeno)
                .offset(offset)
                .limit(limit)
        ).all())

    def count(self) -> int:
        """
        Cuenta la cantidad total de ingredientes activos.
        Returns:
            int: Total de registros en la tabla Ingredientes.
        return len(self.session.exec(select(Ingrediente)).all())
        """
        return self.session.exec(
            select(func.count())
            .select_from(Ingrediente)
            .where(Ingrediente.deleted_at.is_(None))
        ).one()