# tests/test_uploads.py
"""Tests de uploads con mock de Cloudinary."""
import io
from unittest.mock import MagicMock, patch
from tests.conftest import _crear_usuario, _login
 
UPLOAD = "/api/v1/uploads/imagen"
 
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
    b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
    b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)
 
 
# ── Acceso ────────────────────────────────────────────────────────────────────
 
def test_upload_sin_autenticar(client):
    r = client.post(UPLOAD, files={"file": ("img.png", io.BytesIO(PNG), "image/png")})
    assert r.status_code == 401
 
 
def test_upload_sin_rol_admin(client, db_session):
    _crear_usuario(db_session, "cliente_up@test.com", "pass1234", "CLIENT")
    _login(client, "cliente_up@test.com", "pass1234")
    r = client.post(UPLOAD, files={"file": ("img.png", io.BytesIO(PNG), "image/png")})
    assert r.status_code == 403
 
 
def test_delete_sin_autenticar(client):
    assert client.delete(f"{UPLOAD}/test/img_id").status_code == 401
 
 
# ── Validaciones ──────────────────────────────────────────────────────────────
 
def test_tipo_pdf_rechazado(client, usuario_admin):
    _login(client, usuario_admin.email, "pass1234")
    r = client.post(UPLOAD, files={"file": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")})
    assert r.status_code == 400
 
 
def test_tipo_gif_rechazado(client, usuario_admin):
    _login(client, usuario_admin.email, "pass1234")
    r = client.post(UPLOAD, files={"file": ("img.gif", io.BytesIO(b"GIF89a"), "image/gif")})
    assert r.status_code == 400
 
 
def test_archivo_mayor_5mb(client, usuario_admin):
    _login(client, usuario_admin.email, "pass1234")
    big = io.BytesIO(b"\x00" * (6 * 1024 * 1024))
    r = client.post(UPLOAD, files={"file": ("big.png", big, "image/png")})
    assert r.status_code == 400
 
 
# ── Upload con Cloudinary mockeado ────────────────────────────────────────────
 
@patch("app.modules.upload.service.cloudinary.uploader.upload")
def test_upload_png_ok(mock_upload, client, usuario_admin):
    mock_upload.return_value = {
        "secure_url": "https://res.cloudinary.com/test/img.png",
        "public_id": "foodstore/img",
        "width": 100, "height": 100, "format": "png", "resource_type": "image",
    }
    _login(client, usuario_admin.email, "pass1234")
    r = client.post(UPLOAD, files={"file": ("img.png", io.BytesIO(PNG), "image/png")})
    assert r.status_code == 201
    assert "secure_url" in r.json()
 
 
@patch("app.modules.upload.service.cloudinary.uploader.upload")
def test_upload_jpeg_ok(mock_upload, client, usuario_admin):
    mock_upload.return_value = {
        "secure_url": "https://res.cloudinary.com/test/img.jpg",
        "public_id": "foodstore/img",
        "width": 100, "height": 100, "format": "jpeg", "resource_type": "image",
    }
    _login(client, usuario_admin.email, "pass1234")
    jpeg = bytes([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46,
                  0x00, 0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xD9])
    r = client.post(UPLOAD, files={"file": ("img.jpg", io.BytesIO(jpeg), "image/jpeg")})
    assert r.status_code == 201
 
 
# ── Delete con Cloudinary mockeado ────────────────────────────────────────────
 
@patch("app.modules.upload.service.cloudinary.uploader.destroy")
def test_delete_ok(mock_destroy, client, usuario_admin):
    mock_destroy.return_value = {"result": "ok"}
    _login(client, usuario_admin.email, "pass1234")
    r = client.delete(f"{UPLOAD}/foodstore/img")
    assert r.status_code == 204
 
 
@patch("app.modules.upload.service.cloudinary.uploader.destroy")
def test_delete_con_slashes(mock_destroy, client, usuario_admin):
    mock_destroy.return_value = {"result": "ok"}
    _login(client, usuario_admin.email, "pass1234")
    r = client.delete(f"{UPLOAD}/folder/sub/img_id")
    assert r.status_code == 204
    assert mock_destroy.called