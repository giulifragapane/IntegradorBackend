# app/modules/ingrediente/unit_of_work.py
from sqlmodel import Session
from app.core.unit_of_work import UnitOfWork
from app.modules.ingrediente.repository import IngredienteRepository


class IngredienteUnitOfWork(UnitOfWork):
    """
    UoW del módulo ingredientes.
    
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.ingredientes = IngredienteRepository(session)