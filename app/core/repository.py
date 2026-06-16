#app/core/repository.py
from sqlmodel import Session, SQLModel, select
from typing import Generic, TypeVar, Type, Sequence

"""
---EL QUE HABLA CON LA BD (El que hace el CRUD)---
- NO tiene lógica de negocio ni levanta HTTPException.
- Es la capa de acceso a datos, responsable de interactuar con la base de datos.


Repositorio genérico para operaciones CRUD básicas.
- Proporciona métodos comunes para interactuar con la base de datos.
- Es la capa de acceso a datos, sin lógica de negocio ni manejo de excepciones HTTP.
- Cada repositorio específico (e.g., CategoriaRepository) hereda de esta clase y puede agregar métodos personalizados.
- El UnitOfWork inyecta la sesión de base de datos y el modelo correspondiente a cada repositorio.
- Usa tipado genérico para mantener la flexibilidad y seguridad de tipos.

IMPORTANTE: NO hace commit ni rollback (significa que no se manejan transacciones directamente). 
El manejo de transacciones lo hace el UnitOfWork. 
El repositorio solo marca los cambios (add, delete) y el UnitOfWork decide cuándo persistirlos (es decir, guardar los cambios o revertirlos).
"""

# TypeVar para tipar el modelo específico que maneja cada repositorio concreto.
# ModelT es un tipo genérico que representa cualquier modelo que herede de SQLModel.
ModelT = TypeVar("ModelT", bound=SQLModel)


class BaseRepository(Generic[ModelT]):
    """
    Repositorio genérico que implementa operaciones CRUD básicas
    para cualquier modelo basado en SQLModel.

    Principio: el repositorio solo habla con la DB.
    No contiene lógica de negocio ni levanta HTTPException.

    Este repositorio sirve como clase base para repositorios específicos,
    donde se agregan queries más complejas o reglas de acceso particulares.

    Tipado:
    - Usa Generic[ModelT] para mantener tipado fuerte en cada repositorio concreto.
    Generic[ModelT] es una forma de decir "este repositorio va a manejar un modelo específico que hereda de SQLModel".
    """
    def __init__(self, session: Session, model: Type[ModelT]) -> None:
        """
        Inicializa el repositorio con una sesión de base de datos y el modelo asociado.

        Args:
            session (Session): Sesión activa de SQLModel/SQLAlchemy.
                               Es inyectada generalmente por el UnitOfWork.
            model (Type[ModelT]): Clase del modelo que este repositorio gestiona.
        """
        self.session = session
        self.model = model

    def get_by_id(self, record_id: int) -> ModelT | None:
        """
        Obtiene una entidad por su ID primario.

        Args:
            record_id (int): Identificador único del registro.

        Returns:
            ModelT | None: Instancia del modelo si existe, o None si no se encuentra.

        Nota:
            No lanza excepciones. El manejo de "no encontrado" debe hacerse en la capa de servicio.
        """
        return self.session.get(self.model, record_id)
    
    def get_all(self, offset: int = 0, limit: int = 20) -> Sequence[ModelT]:
        """
        Obtiene una lista paginada de entidades.

        Args:
            offset (int): Cantidad de registros a omitir (paginación).
            limit (int): Cantidad máxima de registros a devolver.

        Returns:
            Sequence[ModelT]: Lista de entidades recuperadas.

        Nota:
            No garantiza orden si no se especifica explícitamente en la query.
        """
        return self.session.exec(
            select(self.model).offset(offset).limit(limit)
        ).all()
    
    def get_active(self, offset: int = 0, limit: int = 20) -> Sequence[ModelT]:
        """
            Obtiene registros activos (no eliminados lógicamente).

        Args:
            offset (int): Registros a omitir.
            limit (int): Máximo de registros a devolver.

        Returns:
            Sequence[ModelT]: Lista de entidades activas.
        """
        return self.session.exec(
            select(self.model)
            .where(self.model.deleted_at.is_(None))
            .offset(offset)
            .limit(limit)
        ).all()

    def add(self, instance: ModelT) -> ModelT:
        """
        Persiste una nueva entidad en la sesión actual.

        Flujo:
        - add(): marca la entidad para inserción
        - flush(): ejecuta INSERT en la DB sin commit (genera ID)
        - refresh(): sincroniza el estado del objeto con la DB

        Args:
            instance (ModelT): Instancia a persistir.

        Returns:
            ModelT: La misma instancia, con su ID ya generado.

        Importante:
            NO hace commit. Esto lo maneja el UnitOfWork.
        """
        self.session.add(instance) #registra el objeto para insert
        self.session.flush()  # obtiene el ID sin hacer commit
        self.session.refresh(instance)
        return instance

    def delete(self, instance: ModelT) -> None:
        """
        Marca una entidad para eliminación en la base de datos.

        Flujo:
        - delete(): marca para borrado
        - flush(): ejecuta DELETE sin commit

        Args:
            instance (ModelT): Instancia a eliminar.

        Importante:
            NO hace commit. El UnitOfWork decide cuándo persistir el cambio.
        """
        self.session.delete(instance)
        self.session.flush()