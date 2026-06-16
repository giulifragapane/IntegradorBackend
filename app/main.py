# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.core.database import create_db_and_tables, engine
from app.core.config import settings
from app.core.logger import get_logger, setup_logging
from app.core.middleware.logging_middleware import LoggingMiddleware
from app.core.middleware.timing_middleware import TimingMiddleware
from app.core.exceptions.exception_handlers import register_exception_handlers
from app.db.seed import seed_data
from app.modules.admin.router import router as admin_router
from app.modules.categoria.router import router as categoria_router
from app.modules.direccion.router import router as direccion_router
from app.modules.estadisticas.router import router as estadisticas_router
from app.modules.ingrediente.router import router as ingrediente_router
from app.modules.pago.router import router as pago_router
from app.modules.pedido.router import router as pedido_router
from app.modules.pedido.websocket_router import router as pedido_websocket_router
from app.modules.producto.router import router as producto_router
from app.modules.upload.router import router as upload_router
from app.modules.usuario.router import router as auth_router

# Configurar logging ANTES de cualquier otra cosa.
setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app.startup — creando tablas y ejecutando seed")
    create_db_and_tables()
    try:
        with Session(engine) as session:
            seed_data(session)
        logger.info("seed.completed")
    except Exception as e:
        logger.warning("seed.failed (continuamos sin seed): %s", e)
    yield
    logger.info("app.shutdown")

app = FastAPI(
    title="API Parcial",
    description="API para el parcial de programación - Backend",
    version="1.0.0",
    lifespan=lifespan,
)


register_exception_handlers(app)

app.add_middleware(LoggingMiddleware)

app.add_middleware(TimingMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(categoria_router)
app.include_router(ingrediente_router)
app.include_router(producto_router)
app.include_router(auth_router)
app.include_router(direccion_router)
app.include_router(pedido_router)
app.include_router(admin_router)
app.include_router(upload_router)
app.include_router(estadisticas_router)
app.include_router(pago_router)
app.include_router(pedido_websocket_router)
