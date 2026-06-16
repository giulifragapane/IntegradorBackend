# app/modules/producto/unit_of_work.py
from sqlmodel import Session
from app.core.unit_of_work import UnitOfWork
from app.modules.producto.repository import ProductoRepository, UnidadMedidaRepository
from app.modules.ingrediente.repository import IngredienteRepository
from app.modules.categoria.repository import CategoriaRepository

class ProductoUnitOfWork(UnitOfWork):
    """
    UoW específico del módulo producto.
    - Expone los repositorios que el servicio necesita coordinar.
    - Al entrar al contexto (with uow:) todos los repositorios
    comparten la misma Session → misma transacción.
    """

    def __init__(self, session: Session) -> None:

        super().__init__(session)
        self.productos = ProductoRepository(session)
        self.unidades_medida = UnidadMedidaRepository(session)
        self.categorias = CategoriaRepository(session)
        self.ingredientes = IngredienteRepository(session)