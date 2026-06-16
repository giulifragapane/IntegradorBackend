# app/modules/categoria/service.py
from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.categoria.model import Categoria
from app.modules.categoria.schema import CategoriaCreate, CategoriaRead, CategoriaUpdate, CategoriaList
from app.modules.categoria.unit_of_work import CategoriaUnitOfWork


class CategoriaService:
    """
    Capa de lógica de negocio para Categorías.

    Responsabilidades:
    - Validaciones de dominio (alias único, etc.)
    - Coordinar repositorios a través del UoW
    - Levantar HTTPException cuando corresponde
    - NUNCA acceder directamente a la Session

    REGLA IMPORTANTE — objetos ORM y commit():
    Después de que el UoW hace commit(), SQLAlchemy expira los atributos
    del objeto ORM. Toda serialización (model_dump / model_validate)
    debe ocurrir DENTRO del bloque `with uow:`, antes de que __exit__
    dispare el commit.
    """

    def __init__(self, session: Session) -> None:
        """
        Inicializa el servicio con una sesión de base de datos.

        Args:
            session (Session): Sesión activa que será utilizada por el UnitOfWork.

        Nota:
            El servicio no maneja directamente la transacción; delega en HeroUnitOfWork.
        """
        self._session = session


    # ── Helpers privados ──────────────────────────────────────────────────────

    def _get_or_404(self, uow: CategoriaUnitOfWork, categoria_id: int) -> Categoria:
        """
        Obtiene una categoría por ID o lanza excepción HTTP 404 si no existe.

        Args:
            uow (CategoriaUnitOfWork): Unidad de trabajo activa.
            categoria_id (int): ID de la categoría.

        Returns:
            Categoria: Instancia encontrada.

        Raises:
            HTTPException: 404 si la categoría no existe.

        """
        categoria = uow.categorias.get_by_id(categoria_id)
        if not categoria:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Categoría con id={categoria_id} no encontrada",
            )
        return categoria


    def _assert_nombre_unique(self, uow: CategoriaUnitOfWork, nombre: str) -> None:
        """
        Valida que el nombre no esté en uso.

        Args:
            uow (CategoriaUnitOfWork): Unidad de trabajo activa.
            alias (str): Alias a validar.

        Raises:
            HTTPException: 409 si el nombre ya existe.

        Nota:
            Esta validación es a nivel aplicación, no reemplaza un UNIQUE en DB.
        """
        if uow.categorias.get_by_nombre(nombre):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El nombre '{nombre}' ya está en uso",
            )
    # Esta funcion es un helper para validar que el parent_id referencie a una categoría existente, si es que se proporciona.
    def _get_parent_or_404(self, uow: CategoriaUnitOfWork, parent_id: int) -> Categoria:
        parent = uow.categorias.get_by_id(parent_id)
        if not parent:
            raise HTTPException(
                status_code=404,
                detail=f"Categoría con id={parent_id} no encontrada."
            )
        return parent

    # ── Casos de uso ─────────────────────────────────────────────────────────

    def create(self, data: CategoriaCreate) -> CategoriaRead:
        """
        Crea una nueva categoría.

        Flujo:
        - Valida unicidad de nombre
        - Construye entidad desde DTO
        - Persiste usando repositorio
        - Serializa antes de cerrar la transacción

        Args:
            data (CategoriaCreate): Datos de entrada.

        Returns:
            HeroPublic: DTO de salida.
        """
        with CategoriaUnitOfWork(self._session) as uow:
            self._assert_nombre_unique(uow, data.nombre)
            if data.parent_id is not None:
                self._get_parent_or_404(uow, data.parent_id)
            categoria = Categoria.model_validate(data)
            uow.categorias.add(categoria)

            # Serializar dentro del contexto asegura acceso a atributos lazy
            result = CategoriaRead.model_validate(categoria)

        return result


    def get_all_active(self, offset: int = 0, limit: int = 20) -> CategoriaList:
        """
        Obtiene lista paginada de héroes activos.

        Args:
            offset (int): Desplazamiento.
            limit (int): Límite de resultados.

        Returns:
            CategoriaList: DTO con lista de categorías y total.

        Nota:
            El total se calcula con una query separada.
        """
        with CategoriaUnitOfWork(self._session) as uow:
            categorias = uow.categorias.get_active(offset=offset, limit=limit)
            total = uow.categorias.count()

            result = CategoriaList(
                data=[CategoriaRead.model_validate(c) for c in categorias],
                total=total,
            )

        return result
    
    def get_all(self, offset: int = 0, limit: int = 20) -> CategoriaList:
        """
        Obtiene lista paginada de héroes activos.

        Args:
            offset (int): Desplazamiento.
            limit (int): Límite de resultados.

        Returns:
            CategoriaList: DTO con lista de categorías y total.

        Nota:
            El total se calcula con una query separada.
        """
        with CategoriaUnitOfWork(self._session) as uow:
            categorias = uow.categorias.get_all(offset=offset, limit=limit)
            total = len(categorias) #Cantidad por página

            result = CategoriaList(
                data=[CategoriaRead.model_validate(c) for c in categorias],
                total=total,
            )

        return result


    def get_by_id(self, categoria_id: int) -> CategoriaRead:
        """
        Obtiene una categoría por ID.

        Args:
            categoria_id (int): ID de la categoría.

        Returns:
            CategoriaRead: DTO de la categoría.

        Raises:
            HTTPException: 404 si no existe.
        """
        with CategoriaUnitOfWork(self._session) as uow:
            categoria = self._get_or_404(uow, categoria_id)
            result = CategoriaRead.model_validate(categoria)

        return result


    def update(self, categoria_id: int, data: CategoriaUpdate) -> CategoriaRead:
        """
        Actualiza una categoría existente de forma parcial (PATCH).

        Flujo:
        - Obtiene entidad
        - Valida nombre si cambia
        - Aplica cambios dinámicamente
        - Persiste cambios

        Args:
            categoria_id (int): ID de la categoría.
            data (CategoriaUpdate): Datos parciales.

        Returns:
            CategoriaRead: DTO actualizado.
        """
        with CategoriaUnitOfWork(self._session) as uow:
            categoria = self._get_or_404(uow, categoria_id)

            if data.nombre and data.nombre != categoria.nombre:
                self._assert_nombre_unique(uow, data.nombre)

            if data.parent_id is not None and data.parent_id != categoria.parent_id:
                self._get_parent_or_404(uow, data.parent_id)
                
            if data.parent_id == categoria_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Una categoría no puede ser padre de si misma.",
                )
            
            # Solo campos enviados por el cliente
            patch = data.model_dump(exclude_unset=True)

            for field, value in patch.items():
                setattr(categoria, field, value)

            categoria.updated_at = uow.now
            uow.categorias.add(categoria)
            result = CategoriaRead.model_validate(categoria)

        return result
    
    def  get_by_nombre(self, nombre: str) -> CategoriaRead:
        """
        Busca una categoría por su nombre.

        Args:
            nombre (str): Nombre de la categoría a buscar.

        Returns:
            CategoriaRead: DTO de la categoría encontrada.

        Raises:
            HTTPException: 404 si no se encuentra una categoría con el nombre dado.
        """
        with CategoriaUnitOfWork(self._session) as uow:
            categoria = uow.categorias.get_by_nombre(nombre)
            if not categoria:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Categoría con nombre='{nombre}' no encontrada.",
                )
            result = CategoriaRead.model_validate(categoria)

        return result

    
    def soft_delete(self, categoria_id: int) -> None:
        """
        Realiza un borrado lógico de la categoría.

        Flujo:
        - Obtiene entidad
        - Marca como inactivo
        - Persiste cambio

        Args:
            categoria_id (int): ID de la categoría.

        Nota:
            No elimina físicamente el registro de la base de datos.
        """
        with CategoriaUnitOfWork(self._session) as uow:
            subcategorias = uow.categorias.get_by_parent_id(categoria_id)
            if subcategorias:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se puede eliminar una categoría que tiene subcategorías asociadas."
            )
            categoria = self._get_or_404(uow, categoria_id)
            if categoria.productos:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se puede eliminar una categoría asociada a uno o más productos."
                )
            categoria = self._get_or_404(uow, categoria_id)
            categoria.deleted_at = uow.now
            categoria.updated_at = uow.now
            uow.categorias.add(categoria)