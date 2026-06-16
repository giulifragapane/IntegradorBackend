# app/modules/usuario/schema.py
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

ROLES_VALIDOS = {"ADMIN", "STOCK", "PEDIDOS", "CLIENT"}


class UsuarioBase(BaseModel):
    nombre: str = Field(..., max_length=80)
    apellido: str = Field(..., max_length=80)
    email: EmailStr = Field(..., max_length=254)
    celular: str | None = Field(default=None, max_length=20)


class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=6)


class UsuarioUpdate(BaseModel):
    nombre: str | None = Field(None, max_length=80)
    apellido: str | None = Field(None, max_length=80)
    email: EmailStr | None = Field(None, max_length=254)
    celular: str | None = Field(None, max_length=20)


class UsuarioAdminUpdate(UsuarioUpdate):
    disabled: bool | None = None


class UsuarioRolesUpdate(BaseModel):
    roles: list[str] = Field(..., min_length=1)

    @field_validator("roles")
    @classmethod
    def validar_roles(cls, roles: list[str]) -> list[str]:
        roles_normalizados = [rol.upper() for rol in roles]

        roles_invalidos = [rol for rol in roles_normalizados if rol not in ROLES_VALIDOS]
        if roles_invalidos:
            raise ValueError(f"Roles inválidos: {', '.join(roles_invalidos)}")

        return roles_normalizados


class UsuarioRolRead(BaseModel):
    rol_codigo: str
    model_config = ConfigDict(from_attributes=True)


class UsuarioRead(UsuarioBase):
    id: int
    disabled: bool
    roles: list[UsuarioRolRead] = []
    model_config = ConfigDict(from_attributes=True)


class UsuarioList(BaseModel):
    data: list[UsuarioRead]
    total: int


class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int | None = None
