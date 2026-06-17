# Foodstore — Backend (API)

**Video de presentación:** [carpeta en Google Drive](https://drive.google.com/drive/folders/1VGVLJdY9Qo6D388iF_YlcTaDRHvbVLUC?usp=drive_link)

API REST del proyecto **Foodstore**, desarrollada con FastAPI. Centraliza la lógica de negocio del sistema: catálogo, autenticación con roles, direcciones, pedidos, pagos con Mercado Pago, carga de imágenes con Cloudinary, estadísticas para el dashboard admin y actualizaciones en tiempo real vía WebSocket.

Los frontends que consumen esta API son [`store_final`](../store_final) (cliente) e [`IntegradorAdmin`](../IntegradorAdmin) (administración).

## Stack

| Categoría | Tecnología |
|-----------|------------|
| Framework web | FastAPI |
| ORM / modelos | SQLModel |
| Base de datos | PostgreSQL |
| Validación | Pydantic |
| Autenticación | JWT en cookie HttpOnly (python-jose, passlib/bcrypt) |
| Imágenes | Cloudinary SDK |
| Pagos | Mercado Pago SDK |
| Tiempo real | WebSockets (Starlette/FastAPI) |
| HTTP cliente (tests) | HTTPX |
| Testing | pytest, pytest-asyncio, pytest-cov, pytest-mock |

## Requisitos previos

- Python 3.11 o superior
- PostgreSQL en ejecución
- Entorno virtual recomendado (`.venv`)

## Cómo correr en local

1. Entrá a la carpeta del proyecto:

```bash
cd IntegradorBackend
```

2. Creá y activá el entorno virtual:

**Windows (PowerShell):**

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Instalá dependencias:

```bash
pip install -r requirements.txt
```

4. Configurá variables de entorno copiando `.env.example` a `.env` y completando PostgreSQL, JWT, Cloudinary y Mercado Pago según tu entorno.

Variables mínimas:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=tu_password
POSTGRES_DB=fastapi_parcial
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

SECRET_KEY=tu_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

CLOUDINARY_CLOUD_NAME=tu_cloud_name
CLOUDINARY_API_KEY=tu_api_key
CLOUDINARY_API_SECRET=tu_api_secret

MP_ACCESS_TOKEN=TEST-tu-access-token
FRONTEND_URL=http://localhost:5173
```

5. Levantá la aplicación:

```bash
python -m fastapi dev app/main.py
```

6. Documentación interactiva en `http://localhost:8000/docs`.

**Usuario admin de prueba** (seed al iniciar):

```txt
email: admin@admin.com
password: admin123
```

### Tests

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

## Qué hay en el repositorio

Arquitectura por **módulos** con capas separadas en cada dominio:

```
app/
  main.py              # entrada, middlewares, routers, lifespan
  core/                # config, DB, seguridad, WebSocket, excepciones, rate limit, logging
  db/                  # seed inicial
  modules/
    usuario/           # auth, registro, roles
    categoria/         # categorías y subcategorías
    ingrediente/       # ingredientes
    producto/          # productos y relaciones
    direccion/         # direcciones de entrega
    pedido/            # pedidos, estados, WebSocket
    pago/              # Mercado Pago y webhooks
    upload/            # imágenes en Cloudinary
    estadisticas/      # KPIs y métricas del dashboard
    admin/             # gestión de usuarios
tests/                 # suite automatizada con pytest
```

Cada módulo sigue el patrón: **router → schema → service → repository → unit of work → model**.

**Funcionalidades principales**

- **Catálogo:** CRUD de categorías, ingredientes y productos; soft delete; stock y disponibilidad.
- **Auth:** registro, login, logout, JWT en cookie, rate limiting en login/registro.
- **Pedidos:** creación desde carrito, transiciones de estado validadas, cancelación con devolución de stock.
- **Pagos:** preferencias de Mercado Pago, webhook y rutas de retorno al frontend.
- **Upload:** subida y eliminación de imágenes en Cloudinary.
- **Estadísticas:** resumen, ventas por período, top productos, pedidos por estado e ingresos por forma de pago.
- **Observabilidad:** exception handlers centralizados, logging por request, timing y `X-Request-ID`.
- **Tiempo real:** WebSocket en `/api/v1/ws/pedidos` para eventos de pedidos y pagos.

## Roles

| Rol | Uso principal |
|-----|----------------|
| `ADMIN` | Acceso total al sistema |
| `STOCK` | Lectura de catálogo y actualización de stock |
| `PEDIDOS` | Gestión de pedidos |
| `CLIENT` | Compras, direcciones y pedidos propios |

## Endpoints destacados

| Área | Prefijo / ruta | Descripción |
|------|----------------|-------------|
| Auth | `/api/v1/auth/` | Registro, login, logout, `/me` |
| Catálogo | `/productos/`, `/categorias/`, `/ingredientes/` | CRUD del catálogo |
| Direcciones | `/api/v1/direcciones/` | CRUD de direcciones del cliente |
| Pedidos | `/api/v1/pedidos/` | Crear, listar, cambiar estado, cancelar |
| Pagos | `/api/v1/pagos/` | Crear pago MP, webhook, consulta |
| Upload | `/api/v1/uploads/` | Subir y eliminar imágenes |
| Estadísticas | `/api/v1/estadisticas/` | Métricas del dashboard admin |
| Admin | `/api/v1/admin/` | Gestión de usuarios |
| WebSocket | `/api/v1/ws/pedidos` | Eventos en tiempo real |

La lista completa está en Swagger: `http://localhost:8000/docs`.
