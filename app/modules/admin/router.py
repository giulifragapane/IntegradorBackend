# app/modules/admin/router.py
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import require_role
from app.modules.usuario.model import Usuario
from app.modules.usuario.schema import (
    UsuarioAdminUpdate,
    UsuarioList,
    UsuarioRead,
    UsuarioRolesUpdate,
)
from app.modules.usuario.service import UsuarioService
from app.modules.usuario.unit_of_work import UsuarioUnitOfWork


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def get_usuario_uow(
    session: Annotated[Session, Depends(get_session)],
) -> UsuarioUnitOfWork:
    return UsuarioUnitOfWork(session)


@router.get(
    "/usuarios",
    response_model=UsuarioList,
    status_code=status.HTTP_200_OK,
    summary="Listar usuarios paginados con filtro opcional por rol",
)
def list_usuarios_admin(
    _admin: Annotated[Usuario, Depends(require_role(["ADMIN"]))],
    offset: Annotated[int, Query(ge=0, description="Cantidad de registros a omitir")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Cantidad máxima de registros")] = 20,
    rol: Annotated[str | None, Query(description="Filtro opcional por rol")] = None,
    uow: Annotated[UsuarioUnitOfWork, Depends(get_usuario_uow)] = None,
) -> UsuarioList:
    with uow:
        service = UsuarioService(uow)
        return service.list_admin(offset=offset, limit=limit, rol=rol)


@router.patch(
    "/usuarios/{user_id}",
    response_model=UsuarioRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar datos de un usuario",
)
def update_usuario_admin(
    user_id: int,
    data: UsuarioAdminUpdate,
    _admin: Annotated[Usuario, Depends(require_role(["ADMIN"]))],
    uow: Annotated[UsuarioUnitOfWork, Depends(get_usuario_uow)],
) -> UsuarioRead:
    with uow:
        service = UsuarioService(uow)
        return service.update_admin(user_id, data)


@router.delete(
    "/usuarios/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar usuario con soft delete",
)
def delete_usuario_admin(
    user_id: int,
    _admin: Annotated[Usuario, Depends(require_role(["ADMIN"]))],
    uow: Annotated[UsuarioUnitOfWork, Depends(get_usuario_uow)],
) -> None:
    with uow:
        service = UsuarioService(uow)
        service.soft_delete_admin(user_id)


@router.patch(
    "/usuarios/{user_id}/roles",
    response_model=UsuarioRead,
    status_code=status.HTTP_200_OK,
    summary="Asignar roles a un usuario",
)
def update_usuario_roles_admin(
    user_id: int,
    data: UsuarioRolesUpdate,
    _admin: Annotated[Usuario, Depends(require_role(["ADMIN"]))],
    uow: Annotated[UsuarioUnitOfWork, Depends(get_usuario_uow)],
) -> UsuarioRead:
    with uow:
        service = UsuarioService(uow)
        return service.update_roles(user_id, data)