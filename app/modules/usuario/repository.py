# app/modules/usuario/repository.py
from sqlmodel import Session, select
from sqlalchemy import func

from app.core.repository import BaseRepository
from app.modules.usuario.model import Rol, Usuario, UsuarioRol


class UsuarioRepository(BaseRepository[Usuario]):

    def __init__(self, session: Session):
        super().__init__(session, Usuario)

    def get_by_email(self, email: str) -> Usuario | None:
        return self.session.exec(
            select(Usuario).where(Usuario.email == email)
        ).first()

    def get_all_paginated(self, offset: int = 0, limit: int = 20) -> list[Usuario]:
        return list(
            self.session.exec(
                select(Usuario)
                .where(Usuario.deleted_at.is_(None))
                .offset(offset)
                .limit(limit)
            ).all()
        )

    def count_active(self) -> int:
        return self.session.exec(
            select(func.count())
            .select_from(Usuario)
            .where(Usuario.deleted_at.is_(None))
        ).one()

    def get_by_role(self, rol_codigo: str, offset: int = 0, limit: int = 20) -> list[Usuario]:
        return list(
            self.session.exec(
                select(Usuario)
                .join(UsuarioRol, Usuario.id == UsuarioRol.usuario_id)
                .where(Usuario.deleted_at.is_(None))
                .where(UsuarioRol.rol_codigo == rol_codigo)
                .offset(offset)
                .limit(limit)
            ).all()
        )

    def count_by_role(self, rol_codigo: str) -> int:
        return self.session.exec(
            select(func.count())
            .select_from(Usuario)
            .join(UsuarioRol, Usuario.id == UsuarioRol.usuario_id)
            .where(Usuario.deleted_at.is_(None))
            .where(UsuarioRol.rol_codigo == rol_codigo)
        ).one()

    def clear_roles(self, usuario_id: int) -> None:
        roles_actuales = self.session.exec(
            select(UsuarioRol).where(UsuarioRol.usuario_id == usuario_id)
        ).all()

        for usuario_rol in roles_actuales:
            self.session.delete(usuario_rol)

        self.session.flush()

    def update(self, usuario: Usuario) -> Usuario:
        self.session.flush()
        self.session.refresh(usuario)
        return usuario


class RolRepository(BaseRepository[Rol]):

    def __init__(self, session: Session):
        super().__init__(session, Rol)

    def get_by_codigo(self, codigo: str) -> Rol | None:
        return self.session.get(Rol, codigo)
