# app/modules/ingrediente/service.py
from fastapi import HTTPException, status
from sqlmodel import Session
from app.modules.ingrediente.schema import IngredienteCreate, IngredienteUpdate, IngredienteRead, IngredienteList
from app.modules.ingrediente.model import Ingrediente
from app.modules.ingrediente.unit_of_work import IngredienteUnitOfWork

class IngredienteService:

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _get_or_404(self, uow: IngredienteUnitOfWork, ingrediente_id: int) -> Ingrediente:
        """
        Obtiene un ingrediente por ID o lanza excepción HTTP 404 si no existe.

        Args:
            uow (IngredienteUnitOfWork): Unidad de trabajo activa.
            ingrediente_id (int): ID de la categoría.

        Returns:
            Ingrediente: Instancia encontrada.

        Raises:
            HTTPException: 404 si la categoría no existe.

        """
        ingrediente = uow.ingredientes.get_by_id(ingrediente_id)
        if not ingrediente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ingrediente con id={ingrediente_id} no encontrado",
            )
        return ingrediente


    def _assert_nombre_unique(self, uow: IngredienteUnitOfWork, nombre: str) -> None:
        """
        Valida que el nombre no esté en uso.

        Args:
            uow (IngredienteUnitOfWork): Unidad de trabajo activa.
            alias (str): Alias a validar.

        Raises:
            HTTPException: 409 si el nombre ya existe.

        Nota:
            Esta validación es a nivel aplicación, no reemplaza un UNIQUE en DB.
        """
        if uow.ingredientes.get_by_nombre(nombre):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El nombre '{nombre}' ya está en uso",
            )

    # ── Casos de uso ─────────────────────────────────────────────────────────

    def create(self, data: IngredienteCreate) -> IngredienteRead:
        """
        Crea una nueva categoría.

        Flujo:
        - Valida unicidad de nombre
        - Construye entidad desde DTO
        - Persiste usando repositorio
        - Serializa antes de cerrar la transacción

        Args:
            data (IngredienteCreate): Datos de entrada.

        Returns:
            HeroPublic: DTO de salida.
        """
        with IngredienteUnitOfWork(self._session) as uow:
            self._assert_nombre_unique(uow, data.nombre)

            ingrediente = Ingrediente.model_validate(data)
            uow.ingredientes.add(ingrediente)

            # Serializar dentro del contexto asegura acceso a atributos lazy
            result = IngredienteRead.model_validate(ingrediente)

        return result


    def get_all_active(self, offset: int = 0, limit: int = 20) -> IngredienteList:
        """
        Obtiene lista paginada de ingredientes activos.

        Args:
            offset (int): Desplazamiento.
            limit (int): Límite de resultados.

        Returns:
            IngredienteList: DTO con lista de categorías y total.

        Nota:
            El total se calcula con una query separada.
        """
        with IngredienteUnitOfWork(self._session) as uow:
            ingredientes = uow.ingredientes.get_active(offset=offset, limit=limit)
            total = uow.ingredientes.count()

            result = IngredienteList(
                data=[IngredienteRead.model_validate(c) for c in ingredientes],
                total=total,
            )

        return result
    
    def get_all(self, offset: int = 0, limit: int = 20) -> IngredienteList:
        """
        Obtiene lista paginada de todos los ingredientes.

        Args:
            offset (int): Desplazamiento.
            limit (int): Límite de resultados.

        Returns:
            CategoriaList: DTO con lista de categorías y total.

        Nota:
            El total se calcula con una query separada.
        """
        with IngredienteUnitOfWork(self._session) as uow:
            ingredientes = uow.ingredientes.get_all(offset=offset, limit=limit)
            total = len(ingredientes)

            result = IngredienteList(
                data=[IngredienteRead.model_validate(c) for c in ingredientes],
                total=total,
            )

        return result


    def get_alergenos(self, offset: int = 0, limit: int = 20) -> IngredienteList:
 
        with IngredienteUnitOfWork(self._session) as uow:
            ingredientes = uow.ingredientes.get_alergenos(offset=offset, limit=limit)
            total = len(ingredientes)

            result = IngredienteList(
                data=[IngredienteRead.model_validate(c) for c in ingredientes],
                total=total,
            )

        return result


    def get_by_id(self, ingrediente_id: int) -> IngredienteRead:
        """
        Obtiene una ingrediente por ID.

        Args:
            ingrediente_id (int): ID de la categoría.

        Returns:
            IngredienteRead: DTO de la categoría.

        Raises:
            HTTPException: 404 si no existe.
        """
        with IngredienteUnitOfWork(self._session) as uow:
            ingrediente = self._get_or_404(uow, ingrediente_id)
            result = IngredienteRead.model_validate(ingrediente)

        return result


    def update(self, ingrediente_id: int, data: IngredienteUpdate) -> IngredienteRead:
        """
        Actualiza un ingrediente existente de forma parcial (PATCH).

        Flujo:
        - Obtiene entidad
        - Valida nombre si cambia
        - Aplica cambios dinámicamente
        - Persiste cambios

        Args:
            ingrediente_id (int): ID de la categoría.
            data (IngredienteUpdate): Datos parciales.

        Returns:
            IngredienteRead: DTO actualizado.
        """
        with IngredienteUnitOfWork(self._session) as uow:
            ingrediente = self._get_or_404(uow, ingrediente_id)

            if data.nombre and data.nombre != ingrediente.nombre:
                self._assert_nombre_unique(uow, data.nombre)

            # Solo campos enviados por el cliente
            patch = data.model_dump(exclude_unset=True)

            for field, value in patch.items():
                setattr(ingrediente, field, value)

            ingrediente.updated_at = uow.now
            uow.ingredientes.add(ingrediente)
            result = IngredienteRead.model_validate(ingrediente)

        return result
    
    def  get_by_nombre(self, nombre: str) -> IngredienteRead:
        """
        Busca una categoría por su nombre.

        Args:
            nombre (str): Nombre de la categoría a buscar.

        Returns:
            IngredienteRead: DTO de la categoría encontrada.

        Raises:
            HTTPException: 404 si no se encuentra una categoría con el nombre dado.
        """
        with IngredienteUnitOfWork(self._session) as uow:
            ingrediente = uow.ingredientes.get_by_nombre(nombre)
            if not ingrediente:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Ingrediente con nombre='{nombre}' no encontrado",
                )
            result = IngredienteRead.model_validate(ingrediente)

        return result
    
    def soft_delete(self, ingrediente_id: int) -> None:
        """
        Realiza un borrado lógico de la categoría.

        Flujo:
        - Obtiene entidad
        - Marca como inactivo
        - Persiste cambio

        Args:
            ingrediente_id (int): ID de la categoría.

        Nota:
            No elimina físicamente el registro de la base de datos.
        """
        with IngredienteUnitOfWork(self._session) as uow:
            ingrediente = self._get_or_404(uow, ingrediente_id)
            if ingrediente.productos:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se puede eliminar un ingrediente asociado a uno o más productos."
                )
            ingrediente.deleted_at = uow.now
            ingrediente.updated_at = uow.now
            uow.ingredientes.add(ingrediente)