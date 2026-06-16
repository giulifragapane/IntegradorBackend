# app/modules/producto/repository.py
from sqlmodel import select, Session
from app.core.repository import BaseRepository
from app.modules.producto.model import Producto, UnidadMedida
from sqlalchemy import func

# Acá van todas las consultas específicas del producto.

class ProductoRepository(BaseRepository[Producto]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Producto)

    # buscar productos por nombre
    def get_by_nombre(self, nombre: str) -> Producto | None:
        return self.session.exec(
            select(Producto).where(Producto.nombre == nombre)
    ).first()


    def count(self) -> int:
        """
        Cuenta la cantidad total de productos activos.
        Returns:
            int: Total de registros en la tabla Producto.
        return len(self.session.exec(select(Producto)).all())
        """
        return self.session.exec(
            select(func.count())
            .select_from(Producto)
            .where(Producto.deleted_at.is_(None))
        ).one()
        
class UnidadMedidaRepository(BaseRepository[UnidadMedida]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, UnidadMedida)

    def count(self) -> int:
        return self.session.exec(
            select(func.count())
            .select_from(UnidadMedida)
            .where(UnidadMedida.deleted_at.is_(None))
        ).one()