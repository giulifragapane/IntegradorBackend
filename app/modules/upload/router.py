# app/modules/upload/router.py
from typing import Annotated
import urllib.parse

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.deps import require_role
from app.modules.upload import service
from app.modules.upload.schema import CloudinaryResponse
from app.modules.usuario.model import Usuario

router = APIRouter(prefix="/api/v1/uploads", tags=["uploads"])

ALLOWED_MIME_TYPES = {"image/jpg", "image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024


@router.post(
    "/imagen",
    response_model=CloudinaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir imagen a Cloudinary",
)
async def upload_image(
    _admin: Annotated[Usuario, Depends(require_role(["ADMIN"]))],
    file: UploadFile = File(...),
) -> CloudinaryResponse:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato no soportado. Permitidos: jpg, jpeg, png y webp.",
        )

    file_bytes = await file.read()

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen excede el límite de 5 MB.",
        )

    return service.upload_image(file_bytes)


@router.delete(
    "/imagen/{public_id:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar imagen de Cloudinary por public_id",
)
async def delete_image(
    public_id: str,
    _admin: Annotated[Usuario, Depends(require_role(["ADMIN"]))],
) -> None:
    decoded_public_id = urllib.parse.unquote(public_id)
    service.delete_image(decoded_public_id)
