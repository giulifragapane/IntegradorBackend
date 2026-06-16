# app/modules/usuario/router.py
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_session
from app.core.deps import get_current_active_user, require_role
from app.core.rate_limiter import (
    check_login_rate_limit,
    check_register_rate_limit,
    clear_login_failures,
    register_login_failure,
)
from app.modules.usuario.model import Usuario
from app.modules.usuario.schema import Token, UsuarioCreate, UsuarioRead
from app.modules.usuario.service import UsuarioService
from app.modules.usuario.unit_of_work import UsuarioUnitOfWork

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"


def get_usuario_uow(
    session: Annotated[Session, Depends(get_session)],
) -> UsuarioUnitOfWork:
    return UsuarioUnitOfWork(session)


def _set_auth_cookies(response: Response, token: Token) -> None:
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=token.access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )

    if token.refresh_token:
        response.set_cookie(
            key=REFRESH_TOKEN_COOKIE,
            value=token.refresh_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        )


def _delete_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE,
        httponly=True,
        samesite="lax",
        secure=False,
    )


@router.post(
    "/register",
    response_model=UsuarioRead,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: Request,
    user_in: UsuarioCreate,
    uow: Annotated[UsuarioUnitOfWork, Depends(get_usuario_uow)],
):
    check_register_rate_limit(request)

    with uow:
        service = UsuarioService(uow)
        return service.register(user_in)


def _login_impl(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm,
    uow: UsuarioUnitOfWork,
) -> Token:
    check_login_rate_limit(request, form_data.username)

    with uow:
        service = UsuarioService(uow)

        try:
            token = service.authenticate(
                form_data.username,
                form_data.password,
            )
        except HTTPException as exc:
            if exc.status_code == status.HTTP_401_UNAUTHORIZED:
                register_login_failure(request, form_data.username)
            raise

        clear_login_failures(request, form_data.username)
        _set_auth_cookies(response, token)

        return token


@router.post("/login", response_model=Token)
def login(
    request: Request,
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    uow: Annotated[UsuarioUnitOfWork, Depends(get_usuario_uow)],
):
    return _login_impl(request, response, form_data, uow)


@router.post("/token", response_model=Token)
def login_token_compatibilidad(
    request: Request,
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    uow: Annotated[UsuarioUnitOfWork, Depends(get_usuario_uow)],
):
    return _login_impl(request, response, form_data, uow)


@router.post("/refresh", response_model=Token)
def refresh_token(
    request: Request,
    response: Response,
    uow: Annotated[UsuarioUnitOfWork, Depends(get_usuario_uow)],
):
    refresh_cookie = request.cookies.get(REFRESH_TOKEN_COOKIE)

    if not refresh_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No hay refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    with uow:
        service = UsuarioService(uow)
        token = service.refresh_session(refresh_cookie)
        _set_auth_cookies(response, token)
        return token


@router.post("/logout")
def logout(response: Response):
    _delete_auth_cookies(response)
    return {"mensaje": "Sesión cerrada exitosamente"}


@router.get("/me", response_model=UsuarioRead)
def read_me(
    current_user: Annotated[Usuario, Depends(get_current_active_user)],
):
    return current_user


@router.get("/privado")
def ruta_privada(
    current_user: Annotated[Usuario, Depends(get_current_active_user)],
):
    roles = [
        str(usuario_rol.rol_codigo)
        for usuario_rol in current_user.roles
    ]

    return {
        "mensaje": f"¡Hola, {current_user.nombre}! Accediste a una ruta privada.",
        "tus_roles": roles,
    }


@router.get("/admin/usuarios", response_model=list[UsuarioRead])
def list_users(
    _admin: Annotated[Usuario, Depends(require_role(["ADMIN"]))],
    uow: Annotated[UsuarioUnitOfWork, Depends(get_usuario_uow)],
):
    with uow:
        service = UsuarioService(uow)
        return service.list_all()


@router.post("/admin/usuarios/{user_id}/desactivar", response_model=UsuarioRead)
def deactivate_user(
    user_id: int,
    _admin: Annotated[Usuario, Depends(require_role(["ADMIN"]))],
    uow: Annotated[UsuarioUnitOfWork, Depends(get_usuario_uow)],
):
    with uow:
        service = UsuarioService(uow)
        return service.set_disabled(user_id, disabled=True)


@router.post("/admin/usuarios/{user_id}/activar", response_model=UsuarioRead)
def activate_user(
    user_id: int,
    _admin: Annotated[Usuario, Depends(require_role(["ADMIN"]))],
    uow: Annotated[UsuarioUnitOfWork, Depends(get_usuario_uow)],
):
    with uow:
        service = UsuarioService(uow)
        return service.set_disabled(user_id, disabled=False)
