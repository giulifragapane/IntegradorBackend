# app/modules/producto/service.py
# Lógica de negocio y operaciones CRUD para Producto con la base de datos
from fastapi import HTTPException, status
from sqlmodel import Session
from app.modules.producto.schema import (
    ProductoCreate,
    ProductoUpdate,
    ProductoRead,
    ProductoList,
    ProductoDisponibilidadUpdate,
    UnidadMedidaRead,
    UnidadMedidaList,
)
from app.modules.producto.model import Producto, ProductoCategoria, ProductoIngrediente, UnidadMedida
from app.modules.producto.unit_of_work import ProductoUnitOfWork

class ProductoService:

    def __init__(self, session: Session) -> None:
        self._session = session
    # ── Helpers privados ──────────────────────────────────────────────────────

    def _get_or_404(self, uow: ProductoUnitOfWork, producto_id: int) -> Producto:

        producto = uow.productos.get_by_id(producto_id)
        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con id={producto_id} no encontrado.",
            )
        return producto


    def _assert_nombre_unique(self, uow: ProductoUnitOfWork, nombre: str) -> None:

        if uow.productos.get_by_nombre(nombre):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El nombre '{nombre}' ya está en uso.",
            )
            
    def _validar_unidad_medida(self, uow: ProductoUnitOfWork, unidad_medida_id: int | None) -> None:
        if unidad_medida_id is None:
            return

        unidad = uow.session.get(UnidadMedida, unidad_medida_id)

        if not unidad or unidad.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unidad de medida con id={unidad_medida_id} no encontrada.",
            )
            
    def get_unidades_medida(self, offset: int = 0, limit: int = 100) -> UnidadMedidaList:
        with ProductoUnitOfWork(self._session) as uow:
            unidades = uow.unidades_medida.get_active(offset=offset, limit=limit)
            total = uow.unidades_medida.count()

            return UnidadMedidaList(
                data=[UnidadMedidaRead.model_validate(unidad) for unidad in unidades],
                total=total,
            )
        
    def create(self, data: ProductoCreate) -> ProductoRead:
        with ProductoUnitOfWork(self._session) as uow:
        # Validamos nombre único
            self._assert_nombre_unique(uow, data.nombre)
            self._validar_unidad_medida(uow, data.unidad_venta_id)

        # Creamos producto base
            producto = Producto(
                nombre=data.nombre,
                descripcion=data.descripcion,
                precio_base=data.precio_base,
                imagenes_url=data.imagenes_url,
                stock_cantidad=data.stock_cantidad,
                disponible=data.disponible,
                unidad_venta_id=data.unidad_venta_id,
            )

        # Procesamos categorías (tabla intermedia)
            # Validamos que no haya categorías repetidas en la misma solicitud
            categoria_ids = [cat.categoria_id for cat in data.categorias]
            if len(categoria_ids) != len(set(categoria_ids)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se pueden repetir categorías en el mismo producto."
                )
            
            for cat in data.categorias:
                categoria = uow.categorias.get_by_id(cat.categoria_id)

                if not categoria:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Categoría con id={cat.categoria_id} no encontrada"
                    )

                if categoria.deleted_at is not None:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail="Hay una categoría dada de baja"
                    )

                producto_categoria = ProductoCategoria(
                    categoria_id=cat.categoria_id,
                    es_principal=cat.es_principal,
                )

                producto.categorias.append(producto_categoria)

        # Procesamos ingredientes (tabla intermedia)
            # Validamos que no haya ingredientes repetidos en la misma solicitud
            ingrediente_ids = [ing.ingrediente_id for ing in data.ingredientes]
            if len(ingrediente_ids) != len(set(ingrediente_ids)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se pueden repetir ingredientes en el mismo producto."
                )
                
            for ing in data.ingredientes:
                ingrediente = uow.ingredientes.get_by_id(ing.ingrediente_id)

                if not ingrediente:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Ingrediente con id={ing.ingrediente_id} no encontrado"
                    )

                if ingrediente.deleted_at is not None:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail="Hay un ingrediente dado de baja"
                    )

                self._validar_unidad_medida(uow, ing.unidad_medida_id)

                producto_ingrediente = ProductoIngrediente(
                    ingrediente_id=ing.ingrediente_id,
                    cantidad=ing.cantidad,
                    unidad_medida_id=ing.unidad_medida_id,
                    es_removible=ing.es_removible,
                )

                producto.ingredientes.append(producto_ingrediente)
            #Persistimos
            uow.productos.add(producto)

        # Serializamos
            result = ProductoRead.model_validate(producto)

        return result



    def get_all_active(self, offset: int = 0, limit: int = 20) -> ProductoList:
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
        with ProductoUnitOfWork(self._session) as uow:
            productos = uow.productos.get_active(offset=offset, limit=limit)
            total = uow.productos.count()

            result = ProductoList(
                data=[ProductoRead.model_validate(c) for c in productos],
                total=total,
            )

        return result
    


    def get_all(self, offset: int = 0, limit: int = 20) -> ProductoList:
        """
        Obtiene lista paginada de todos los ingredientes.

        Args:
            offset (int): Desplazamiento.
            limit (int): Límite de resultados.

        Returns:
            ProductoList: DTO con lista de categorías y total.

        Nota:
            El total se calcula con una query separada.
        """
        with ProductoUnitOfWork(self._session) as uow:
            productos = uow.productos.get_all(offset=offset, limit=limit)
            total = len(productos)

            result = ProductoList(
                data=[ProductoRead.model_validate(c) for c in productos],
                total=total,
            )

        return result
    

    def get_by_id(self, producto_id: int) -> ProductoRead:
        """
        Obtiene un producto por ID.

        Args:
            producto_id (int): ID del producto.

        Returns:
            ProductoRead: DTO del producto.

        Raises:
            HTTPException: 404 si no existe.
        """
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)
            result = ProductoRead.model_validate(producto)

        return result



    def update(self, producto_id: int, data: ProductoUpdate) -> ProductoRead:
    
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)

            if data.nombre and data.nombre != producto.nombre:
                self._assert_nombre_unique(uow, data.nombre)

            patch = data.model_dump(exclude_unset=True, exclude={"categorias", "ingredientes"})
            if "unidad_venta_id" in patch:
                self._validar_unidad_medida(uow, patch["unidad_venta_id"])

            for field, value in patch.items():
                setattr(producto, field, value)
            
            # No permite dejar sin categorías
            if data.categorias is not None and len(data.categorias) == 0:
                raise HTTPException(400, "Debe tener al menos una categoría")
           
            # Validamos que no haya categorías repetidas en la misma solicitud
            if data.categorias is not None:
                categoria_ids = [cat.categoria_id for cat in data.categorias]
                if len(categoria_ids) != len(set(categoria_ids)):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No se pueden repetir categorías en el mismo producto."
                    )
                                        
            if data.categorias is not None:
                for pc in list(producto.categorias):
                    uow.session.delete(pc)
                uow.session.flush()   

                for cat in data.categorias:
                    categoria = uow.categorias.get_by_id(cat.categoria_id)
                    if not categoria:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Categoría con id={cat.categoria_id} no encontrada"
                        )
                    if categoria.deleted_at is not None:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail=f"La categoría con id={cat.categoria_id} está dada de baja"
                        )
                    producto.categorias.append(
                        ProductoCategoria(
                            producto=producto,
                            categoria=categoria,
                            es_principal=cat.es_principal
                        )
                    )

            # Validamos que no haya ingredientes repetidos en la misma solicitud
            if data.ingredientes is not None:
                ingrediente_ids = [ing.ingrediente_id for ing in data.ingredientes]
                if len(ingrediente_ids) != len(set(ingrediente_ids)):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No se pueden repetir ingredientes en el mismo producto."
                    )
        
            if data.ingredientes is not None:
                for pi in list(producto.ingredientes):
                    uow.session.delete(pi)
                uow.session.flush()

                for ing in data.ingredientes:
                    ingrediente = uow.ingredientes.get_by_id(ing.ingrediente_id)
                    if not ingrediente:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Ingrediente con id={ing.ingrediente_id} no encontrado"
                        )
                    if ingrediente.deleted_at is not None:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail=f"El ingrediente con id={ing.ingrediente_id} está dado de baja"
                        )
                    self._validar_unidad_medida(uow, ing.unidad_medida_id)

                    producto.ingredientes.append(
                        ProductoIngrediente(
                            producto=producto,
                            ingrediente=ingrediente,
                            cantidad=ing.cantidad,
                            unidad_medida_id=ing.unidad_medida_id,
                            es_removible=ing.es_removible,
                        )
                    )
                    
            producto.updated_at = uow.now            
            result = ProductoRead.model_validate(producto)

        return result

    def  get_by_nombre(self, nombre: str) -> ProductoRead:
        """
        Busca un producto por su nombre.
        Args:
            nombre (str): Nombre del producto a buscar.
        Returns:
            ProductoRead: DTO del producto encontrado.
        Raises:
            HTTPException: 404 si no se encuentra un producto con el nombre dado.
        """
        with ProductoUnitOfWork(self._session) as uow:
            producto = uow.productos.get_by_nombre(nombre)
            if not producto:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Producto con nombre='{nombre}' no encontrado",
                )
            result = ProductoRead.model_validate(producto)

        return result
    


    def update_disponibilidad(self, producto_id: int, data: ProductoDisponibilidadUpdate) -> ProductoRead:
        """
        Actualiza únicamente stock y/o disponibilidad.
        Permitido para ADMIN y STOCK desde el router.
        """
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)

            patch = data.model_dump(exclude_unset=True)

            if not patch:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Debe enviar stock_cantidad y/o disponible."
                )

            for field, value in patch.items():
                setattr(producto, field, value)

            producto.updated_at = uow.now
            uow.productos.add(producto)

            result = ProductoRead.model_validate(producto)

        return result

    def soft_delete(self, producto_id: int) -> None:
        """
        Realiza un borrado lógico del producto.
        No elimina físicamente el registro de la base de datos.
        """
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)

            producto.deleted_at = uow.now
            producto.updated_at = uow.now
            uow.productos.add(producto)