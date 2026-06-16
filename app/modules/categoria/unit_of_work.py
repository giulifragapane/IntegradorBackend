# app/modules/categoria/unit_of_work.py
from sqlmodel import Session
from app.core.unit_of_work import UnitOfWork
from app.modules.categoria.repository import CategoriaRepository

class CategoriaUnitOfWork(UnitOfWork):
    """
    UoW específico del módulo categorias.
    Expone los repositorios que el servicio necesita coordinar.

    Al entrar al contexto (with uow:) todos los repositorios
    comparten la misma Session → misma transacción.
    """

    def __init__(self, session: Session) -> None:
        """
    UnitOfWork específico del dominio Categoria.

    Extiende el UnitOfWork base y registra los repositorios necesarios
    para operar dentro de una misma transacción consistente.

    Repositorios expuestos:
        - categorias: acceso a operaciones sobre Categoria
        - teams: acceso a operaciones sobre Team (usado para validaciones
                 de integridad antes de persistir héroes)

    Args:
        session (Session): Sesión activa de base de datos compartida
                           por todos los repositorios.

    Responsabilidad:
        - Garantizar que todas las operaciones (Categoria, etc.)
          se ejecuten dentro de la misma transacción
        - Centralizar commit() y rollback() (heredado del UoW base)
        - Coordinar múltiples repositorios bajo una única unidad de trabajo

    Uso típico:

        with CategoriaUnitOfWork(session) as uow:
            categoria = Categoria(...)
            uow.categorias.add(categoria)
        """
        super().__init__(session)
        self.categorias = CategoriaRepository(session)