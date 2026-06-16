# app/modules/pedido/router.py
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_active_user, require_role
from app.modules.pedido.schema import PedidoCreate, PedidoEstadoUpdate, PedidoList, PedidoRead
from app.modules.pedido.service import PedidoService
from app.modules.usuario.schema import UsuarioRead

router = APIRouter(prefix="/api/v1/pedidos", tags=["pedidos"])


def get_pedido_service(session: Session = Depends(get_session)) -> PedidoService:
    return PedidoService(session)


def usuario_tiene_rol(usuario: UsuarioRead, roles_permitidos: list[str]) -> bool:
    roles_usuario = getattr(usuario, "roles", []) or []
    valores_permitidos = [str(rol) for rol in roles_permitidos]

    for rol in roles_usuario:
        if isinstance(rol, str) and rol in valores_permitidos:
            return True

        rol_codigo = getattr(rol, "rol_codigo", None)
        if rol_codigo is not None and str(rol_codigo) in valores_permitidos:
            return True

        codigo = getattr(rol, "codigo", None)
        if codigo is not None and str(codigo) in valores_permitidos:
            return True

    return False


@router.post(
    "/",
    response_model=PedidoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un pedido desde el carrito",
)
async def create_pedido(
    data: PedidoCreate,
    current_user: Annotated[UsuarioRead, Depends(get_current_active_user)],
    svc: PedidoService = Depends(get_pedido_service),
) -> PedidoRead:
    return await svc.create(current_user.id, data)


@router.get(
    "/",
    response_model=PedidoList,
    status_code=status.HTTP_200_OK,
    summary="Listar pedidos",
)
def list_pedidos(
    current_user: Annotated[UsuarioRead, Depends(get_current_active_user)],
    offset: Annotated[int, Query(ge=0, description="Cantidad de registros a omitir")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Cantidad máxima de registros")] = 20,
    svc: PedidoService = Depends(get_pedido_service),
) -> PedidoList:
    es_staff_pedidos = usuario_tiene_rol(current_user, ["ADMIN", "PEDIDOS"])
    return svc.get_all_for_user(
        usuario_id=current_user.id,
        es_staff_pedidos=es_staff_pedidos,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{pedido_id}",
    response_model=PedidoRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener pedido por ID",
)
def get_pedido(
    pedido_id: int,
    current_user: Annotated[UsuarioRead, Depends(get_current_active_user)],
    svc: PedidoService = Depends(get_pedido_service),
) -> PedidoRead:
    es_staff_pedidos = usuario_tiene_rol(current_user, ["ADMIN", "PEDIDOS"])
    return svc.get_by_id_for_user(
        pedido_id=pedido_id,
        usuario_id=current_user.id,
        es_staff_pedidos=es_staff_pedidos,
    )


@router.patch(
    "/{pedido_id}/estado",
    response_model=PedidoRead,
    status_code=status.HTTP_200_OK,
    summary="Cambiar estado de pedido",
)
async def update_estado_pedido(
    pedido_id: int,
    data: PedidoEstadoUpdate,
    _staff: Annotated[UsuarioRead, Depends(require_role(["ADMIN", "PEDIDOS"]))],
    svc: PedidoService = Depends(get_pedido_service),
) -> PedidoRead:
    return await svc.update_estado(pedido_id, data)


@router.patch(
    "/{pedido_id}/cancelar",
    response_model=PedidoRead,
    status_code=status.HTTP_200_OK,
    summary="Cancelar pedido propio",
)
async def cancelar_mi_pedido(
    pedido_id: int,
    current_user: Annotated[UsuarioRead, Depends(get_current_active_user)],
    svc: PedidoService = Depends(get_pedido_service),
) -> PedidoRead:
    return await svc.cancelar_mi_pedido(pedido_id, current_user.id)
