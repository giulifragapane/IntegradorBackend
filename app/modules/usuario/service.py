# app/modules/usuario/service.py
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.core.unit_of_work import UnitOfWork
from app.modules.usuario.model import Usuario, UsuarioRol
from app.modules.usuario.schema import (
    Token,
    UsuarioAdminUpdate,
    UsuarioCreate,
    UsuarioList,
    UsuarioRead,
    UsuarioRolesUpdate,
)


class UsuarioService:

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def _get_or_404(self, user_id: int) -> Usuario:
        user = self.uow.usuarios.get_by_id(user_id)

        if not user or user.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado.",
            )

        return user

    def _roles_usuario(self, usuario: Usuario) -> list[str]:
        return [str(usuario_rol.rol_codigo).upper() for usuario_rol in usuario.roles]

    def _es_cliente_puro(self, usuario: Usuario) -> bool:
        roles = self._roles_usuario(usuario)
        return "CLIENT" in roles and not any(rol in roles for rol in ["ADMIN", "STOCK", "PEDIDOS"])

    def register(self, user_in: UsuarioCreate) -> Usuario:
        if self.uow.usuarios.get_by_email(user_in.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El email ya está en uso.",
            )

        rol_client = self.uow.roles.get_by_codigo("CLIENT")
        if not rol_client:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No existe el rol CLIENT. Ejecutá el seed inicial.",
            )

        usuario = Usuario(
            nombre=user_in.nombre,
            apellido=user_in.apellido,
            email=user_in.email,
            celular=user_in.celular,
            password_hash=hash_password(user_in.password),
        )

        usuario.roles.append(
            UsuarioRol(
                rol_codigo="CLIENT",
            )
        )

        return self.uow.usuarios.add(usuario)


    def _validar_usuario_activo(self, user: Usuario | None) -> Usuario:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if user.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cuenta de usuario eliminada.",
            )

        if user.disabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuario deshabilitado.",
            )

        return user

    def _crear_tokens(self, user: Usuario) -> Token:
        role_values = [str(usuario_rol.rol_codigo) for usuario_rol in user.roles]

        token_data = {
            "sub": user.email,
            "roles": role_values,
        }

        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data=token_data)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            refresh_expires_in=settings.refresh_token_expire_days * 24 * 60 * 60,
        )

    def authenticate(self, email: str, password: str) -> Token:
        user = self.uow.usuarios.get_by_email(email)

        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = self._validar_usuario_activo(user)
        return self._crear_tokens(user)

    def refresh_session(self, refresh_token: str) -> Token:
        payload = decode_refresh_token(refresh_token)

        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido o expirado.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        email = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido o expirado.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = self.uow.usuarios.get_by_email(email)
        user = self._validar_usuario_activo(user)

        return self._crear_tokens(user)

    def list_all(self) -> list[Usuario]:
        return self.uow.usuarios.get_all()

    def list_admin(self, offset: int = 0, limit: int = 20, rol: str | None = None) -> UsuarioList:
        if rol is not None:
            rol = rol.upper()

            if rol == "CLIENT":
                return UsuarioList(data=[], total=0)

            usuarios = [
                usuario
                for usuario in self.uow.usuarios.get_by_role(rol, 0, 10000)
                if not self._es_cliente_puro(usuario)
            ]
        else:
            usuarios = [
                usuario
                for usuario in self.uow.usuarios.get_all()
                if usuario.deleted_at is None and not self._es_cliente_puro(usuario)
            ]

        total = len(usuarios)
        usuarios_paginados = usuarios[offset: offset + limit]

        return UsuarioList(
            data=[UsuarioRead.model_validate(usuario) for usuario in usuarios_paginados],
            total=total,
        )

    def update_admin(self, user_id: int, data: UsuarioAdminUpdate) -> Usuario:
        user = self._get_or_404(user_id)
        patch = data.model_dump(exclude_unset=True)

        if "email" in patch and patch["email"] != user.email:
            existing = self.uow.usuarios.get_by_email(patch["email"])
            if existing and existing.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El email ya está en uso.",
                )

        for field, value in patch.items():
            setattr(user, field, value)

        user.updated_at = self.uow.now
        return self.uow.usuarios.update(user)

    def soft_delete_admin(self, user_id: int) -> None:
        user = self._get_or_404(user_id)

        user.deleted_at = self.uow.now
        user.updated_at = self.uow.now
        user.disabled = True

        self.uow.usuarios.update(user)

    def update_roles(self, user_id: int, data: UsuarioRolesUpdate) -> Usuario:
        user = self._get_or_404(user_id)

        roles_unicos = list(dict.fromkeys([rol.upper() for rol in data.roles]))

        if "ADMIN" in roles_unicos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede asignar el rol ADMIN desde administración de usuarios.",
            )

        if "CLIENT" in roles_unicos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede asignar el rol CLIENT desde administración de usuarios.",
            )

        for rol_codigo in roles_unicos:
            if not self.uow.roles.get_by_codigo(rol_codigo):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Rol {rol_codigo} no encontrado.",
                )

        self.uow.usuarios.clear_roles(user.id)
        user.roles.clear()

        for rol_codigo in roles_unicos:
            user.roles.append(
                UsuarioRol(
                    usuario_id=user.id,
                    rol_codigo=rol_codigo,
                )
            )

        user.updated_at = self.uow.now
        return self.uow.usuarios.update(user)

    def set_disabled(self, user_id: int, disabled: bool) -> Usuario:
        user = self._get_or_404(user_id)

        user.disabled = disabled
        user.updated_at = self.uow.now

        return self.uow.usuarios.update(user)
