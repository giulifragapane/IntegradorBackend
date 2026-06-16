# tests/conftest.py
"""
Fixtures globales - SQLite in-memory.
Parchea ARRAY→JSON (no soportado en SQLite), bloquea el lifespan
de PostgreSQL, y resetea el rate limiter entre tests.
"""
from decimal import Decimal
from unittest.mock import patch
 
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import JSON
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool
 
from app.core.database import get_session
from app.core.security import hash_password
from app.modules.usuario.model import Usuario, UsuarioRol
from app.modules.pedido.model import DetallePedido, HistorialEstadoPedido, Pedido
 
# Importar todos los modelos para que SQLModel los registre antes de create_all
import app.modules.categoria.model       # noqa: F401
import app.modules.ingrediente.model     # noqa: F401
import app.modules.producto.model        # noqa: F401
import app.modules.usuario.model         # noqa: F401
import app.modules.pedido.model          # noqa: F401
 
 
def _patch_array():
    """ARRAY(TEXT) de PostgreSQL → JSON para SQLite."""
    from app.modules.producto.model import Producto
    col = Producto.__table__.c.get("imagenes_url")
    if col is not None and not isinstance(col.type, JSON):
        col.type = JSON()
 
 
# ─── Engine / Session ─────────────────────────────────────────────────────────
 
@pytest.fixture(scope="session")
def engine():
    _patch_array()
    _engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(_engine)
    from app.db.seed import seed_data
    with Session(_engine) as s:
        seed_data(s)
    yield _engine
    SQLModel.metadata.drop_all(_engine)
 
 
@pytest.fixture()
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()
 
 
@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Limpia el estado en memoria del rate limiter antes de cada test."""
    import app.core.rate_limiter as rl
    rl._login_failures.clear()
    rl._register_attempts.clear()
    yield
    rl._login_failures.clear()
    rl._register_attempts.clear()
 
 
@pytest.fixture()
def client(db_session, engine):
    def _override():
        yield db_session
 
    with patch("app.modules.pedido.websocket_router.engine", engine), \
         patch("app.core.database.create_db_and_tables", return_value=None), \
         patch("app.db.seed.seed_data", return_value=None):
        from app.main import app
        app.dependency_overrides[get_session] = _override
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
        app.dependency_overrides.clear()
 
 
# ─── Helpers ──────────────────────────────────────────────────────────────────
 
def _crear_usuario(session: Session, email: str, password: str, rol_codigo: str) -> Usuario:
    usuario = Usuario(
        nombre="Test",
        apellido="User",
        email=email,
        password_hash=hash_password(password),
    )
    session.add(usuario)
    session.flush()
    session.add(UsuarioRol(usuario_id=usuario.id, rol_codigo=rol_codigo))
    session.commit()
    session.refresh(usuario)
    return usuario
 
 
def _login(client: TestClient, email: str, password: str) -> None:
    r = client.post("/api/v1/auth/token", data={"username": email, "password": password})
    assert r.status_code == 200, f"Login fallido para {email}: {r.json()}"
 
 
# ─── Fixtures de rol ──────────────────────────────────────────────────────────
 
@pytest.fixture()
def admin_headers(client, db_session):
    _crear_usuario(db_session, "admin_test@test.com", "admin1234", "ADMIN")
    _login(client, "admin_test@test.com", "admin1234")
    return {}
 
 
@pytest.fixture()
def client_headers(client, db_session):
    _crear_usuario(db_session, "client_test@test.com", "client1234", "CLIENT")
    _login(client, "client_test@test.com", "client1234")
    return {}
 
 
@pytest.fixture()
def pedidos_headers(client, db_session):
    _crear_usuario(db_session, "pedidos_test@test.com", "pedidos1234", "PEDIDOS")
    _login(client, "pedidos_test@test.com", "pedidos1234")
    return {}
 
 
# ─── Factories ────────────────────────────────────────────────────────────────
 
@pytest.fixture()
def producto_factory(db_session):
    from app.modules.producto.model import Producto
 
    def _make(nombre="Producto Test", precio=Decimal("100.00"), stock=10, disponible=True):
        prod = Producto(
            nombre=nombre, descripcion="Test", precio_base=precio,
            imagenes_url=[], stock_cantidad=stock, disponible=disponible,
        )
        db_session.add(prod)
        db_session.commit()
        db_session.refresh(prod)
        return prod
 
    return _make
 
 
@pytest.fixture()
def pedido_factory(db_session, producto_factory):
    from app.modules.producto.model import Producto
 
    def _make(usuario_id: int, producto_id: int | None = None) -> Pedido:
        if producto_id is None:
            producto_id = producto_factory().id
        prod = db_session.get(Producto, producto_id)
        precio = prod.precio_base if prod else Decimal("100.00")
        nombre = prod.nombre if prod else "Producto"
 
        pedido = Pedido(
            usuario_id=usuario_id, estado_codigo="PENDIENTE",
            forma_pago_codigo="EFECTIVO", subtotal=precio,
            descuento=Decimal("0.00"), costo_envio=Decimal("0.00"), total=precio,
        )
        db_session.add(pedido)
        db_session.flush()
        db_session.add(DetallePedido(
            pedido_id=pedido.id, producto_id=producto_id, cantidad=1,
            personalizacion=[], producto_nombre=nombre,
            precio_unitario=precio, subtotal=precio,
        ))
        db_session.add(HistorialEstadoPedido(
            pedido_id=pedido.id, estado_desde_codigo=None, estado_hacia_codigo="PENDIENTE",
        ))
        db_session.commit()
        db_session.refresh(pedido)
        return pedido
 
    return _make
 
 
@pytest.fixture()
def usuario_admin(db_session) -> Usuario:
    return _crear_usuario(db_session, "admin_factory@test.com", "pass1234", "ADMIN")
 
 
@pytest.fixture()
def usuario_cliente(db_session) -> Usuario:
    return _crear_usuario(db_session, "cliente_factory@test.com", "pass1234", "CLIENT")