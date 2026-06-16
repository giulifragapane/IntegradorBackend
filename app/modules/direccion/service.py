from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.direccion.schema import DireccionCreate, DireccionUpdate, DireccionRead, DireccionList
from app.modules.direccion.unit_of_work import DireccionUnitOfWork
from app.modules.usuario.model import DireccionEntrega


class DireccionService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_or_404(self, uow: DireccionUnitOfWork, direccion_id: int, usuario_id: int) -> DireccionEntrega:
        direccion = uow.direcciones.get_active_by_id_and_usuario(direccion_id, usuario_id)
        if not direccion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dirección no encontrada.",
            )
        return direccion

    def get_my_direcciones(self, usuario_id: int, offset: int = 0, limit: int = 20) -> DireccionList:
        with DireccionUnitOfWork(self._session) as uow:
            direcciones = uow.direcciones.get_active_by_usuario(usuario_id, offset, limit)
            total = uow.direcciones.count_active_by_usuario(usuario_id)
            result = DireccionList(
                data=[DireccionRead.model_validate(d) for d in direcciones],
                total=total,
            )
        return result

    def create(self, usuario_id: int, data: DireccionCreate) -> DireccionRead:
        with DireccionUnitOfWork(self._session) as uow:
            direcciones_activas = uow.direcciones.get_active_by_usuario(usuario_id, 0, 100)

            # Si es la primera dirección del usuario, queda como principal automáticamente.
            es_primera_direccion = len(direcciones_activas) == 0

            if data.es_principal or es_primera_direccion:
                uow.direcciones.unset_principal_by_usuario(usuario_id)

            direccion = DireccionEntrega(
                usuario_id=usuario_id,
                alias=data.alias,
                linea1=data.linea1,
                linea2=data.linea2,
                ciudad=data.ciudad,
                provincia=data.provincia,
                codigo_postal=data.codigo_postal,
                es_principal=data.es_principal or es_primera_direccion,
            )

            uow.direcciones.add(direccion)
            result = DireccionRead.model_validate(direccion)
        return result

    def update(self, direccion_id: int, usuario_id: int, data: DireccionUpdate) -> DireccionRead:
        with DireccionUnitOfWork(self._session) as uow:
            direccion = self._get_or_404(uow, direccion_id, usuario_id)

            patch = data.model_dump(exclude_unset=True)

            if patch.get("es_principal") is True:
                uow.direcciones.unset_principal_by_usuario(usuario_id)

            for field, value in patch.items():
                setattr(direccion, field, value)

            direccion.updated_at = uow.now
            uow.direcciones.add(direccion)
            result = DireccionRead.model_validate(direccion)
        return result

    def soft_delete(self, direccion_id: int, usuario_id: int) -> None:
        with DireccionUnitOfWork(self._session) as uow:
            direccion = self._get_or_404(uow, direccion_id, usuario_id)

            # Verificar si la dirección está siendo utilizada
            if uow.pedidos.exists_active_by_direccion(direccion_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "No se puede eliminar la dirección porque está "
                        "asociada a un pedido pendiente o en curso."
                    ),
                )
            era_principal = direccion.es_principal

            direccion.deleted_at = uow.now
            direccion.updated_at = uow.now
            direccion.es_principal = False
            uow.direcciones.add(direccion)

            # Si la dirección eliminada era la principal, se asigna otra dirección activa como principal.
            if era_principal:
                direcciones_restantes = uow.direcciones.get_active_by_usuario(usuario_id, 0, 100)

                for otra_direccion in direcciones_restantes:
                    if otra_direccion.id != direccion_id:
                        otra_direccion.es_principal = True
                        otra_direccion.updated_at = uow.now
                        uow.direcciones.add(otra_direccion)
                        break

    def set_principal(self, direccion_id: int, usuario_id: int) -> DireccionRead:
        with DireccionUnitOfWork(self._session) as uow:
            direccion = self._get_or_404(uow, direccion_id, usuario_id)
            uow.direcciones.unset_principal_by_usuario(usuario_id)
            direccion.es_principal = True
            direccion.updated_at = uow.now
            uow.direcciones.add(direccion)
            result = DireccionRead.model_validate(direccion)
        return result