# app/modules/upload/service.py
import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, status

from app.core.config import settings
from app.modules.upload.schema import CloudinaryResponse


def _configure_cloudinary() -> None:
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )


def _validate_cloudinary_config() -> None:
    if (
        not settings.cloudinary_cloud_name
        or not settings.cloudinary_api_key
        or not settings.cloudinary_api_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Faltan configurar variables de Cloudinary.",
        )


def upload_image(file_bytes: bytes, folder: str = "foodstore") -> CloudinaryResponse:
    _validate_cloudinary_config()
    _configure_cloudinary()

    try:
        result = cloudinary.uploader.upload(
            file_bytes,
            folder=folder,
            resource_type="image",
            allowed_formats=["jpg", "jpeg", "png", "webp"],
            overwrite=False,
            unique_filename=True,
        )

        return CloudinaryResponse(
            secure_url=result["secure_url"],
            public_id=result["public_id"],
            width=result.get("width", 0),
            height=result.get("height", 0),
            format=result.get("format", ""),
            resource_type=result.get("resource_type", "image"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al subir imagen a Cloudinary: {exc}",
        ) from exc


def delete_image(public_id: str) -> None:
    _validate_cloudinary_config()
    _configure_cloudinary()

    try:
        result = cloudinary.uploader.destroy(public_id)
        if result.get("result") not in ("ok", "not found"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error al eliminar imagen: {result}",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al eliminar imagen en Cloudinary: {exc}",
        ) from exc
