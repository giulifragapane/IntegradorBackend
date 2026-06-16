# PARCIAL 2 - BACKEND

## Backend (FastAPI + SQLModel)

Proyecto backend desarrollado con **FastAPI + SQLModel + PostgreSQL**, organizado por módulos y arquitectura por capas:

- Router
- Schema
- Service
- Repository
- Unit of Work
- Model

El proyecto comenzó como un catálogo de productos, categorías e ingredientes, y en la Parte 2 se extendió con autenticación, roles, permisos, direcciones de entrega, pedidos y gestión de usuarios.

---

## Lista de Verificación del Proyecto Integrador

### Base del proyecto

- [X] Entorno: Uso de `.venv`, `requirements.txt` y FastAPI funcionando en modo desarrollo.
- [X] Modelado: Tablas creadas con SQLModel incluyendo relaciones `Relationship` 1:N y N:N.
- [X] Validación: Uso de schemas Pydantic, `Annotated`, `Query` y validaciones de datos.
- [X] CRUD Persistente: Endpoints funcionales para crear, leer, actualizar y borrar en PostgreSQL.
- [X] Seguridad de Datos: Uso de `response_model` para evitar filtrar datos sensibles.
- [X] Estructura: Código organizado por módulos: routers, schemas, services, repositories, models y Unit of Work.
- [X] Soft Delete: Uso de `deleted_at` para bajas lógicas.
- [X] Timestamps: Uso de `created_at`, `updated_at` y `deleted_at` mediante modelo base.

---

## Funcionalidades implementadas

### Catálogo

- [X] CRUD de categorías.
- [X] CRUD de ingredientes.
- [X] CRUD de productos.
- [X] Relaciones producto-categoría e producto-ingrediente.
- [X] Categorías jerárquicas mediante `parent_id`.
- [X] Validación de categorías e ingredientes repetidos en productos.
- [X] Validación para evitar eliminar categorías o ingredientes asociados a productos.
- [X] Endpoint específico para modificar stock y disponibilidad.

### Autenticación y seguridad

- [X] Registro de usuarios.
- [X] Login con email y contraseña.
- [X] Hash de contraseña con bcrypt.
- [X] JWT con expiración.
- [X] Token guardado en cookie `HttpOnly`.
- [X] Logout eliminando cookie.
- [X] Endpoint `/me` para obtener el usuario autenticado.
- [X] Protección de rutas privadas.

### Roles y permisos

Roles implementados:

- `ADMIN`
- `STOCK`
- `PEDIDOS`
- `CLIENT`

Permisos principales:

- [X] Lectura pública del catálogo.
- [X] Crear, editar y eliminar catálogo solo para `ADMIN`.
- [X] Actualizar stock/disponibilidad para `ADMIN` y `STOCK`.
- [X] Gestión de pedidos para `ADMIN` y `PEDIDOS`.
- [X] Clientes pueden crear y consultar sus propios pedidos.
- [X] Seed inicial de roles y usuario administrador.

Usuario administrador inicial:

```txt
email: admin@admin.com
password: admin123
```

### Direcciones de entrega

- [X] Crear dirección.
- [X] Listar direcciones del usuario autenticado.
- [X] Actualizar dirección.
- [X] Marcar dirección como principal.
- [X] Eliminar dirección con soft delete.
- [X] Cada usuario solo puede gestionar sus propias direcciones.
- [X] Si se elimina la dirección principal, se reasigna otra automáticamente.
- [X] Si es la primera dirección del usuario, se marca como principal.

### Pedidos

- [X] Crear pedido desde carrito.
- [X] Validar dirección del usuario.
- [X] Validar productos activos, disponibles y con stock suficiente.
- [X] Descontar stock al crear pedido.
- [X] Guardar snapshot del producto en el detalle: nombre, precio unitario y subtotal.
- [X] Calcular total del pedido.
- [X] Listar pedidos del cliente autenticado.
- [X] Listar pedidos para `ADMIN` y `PEDIDOS`.
- [X] Cambiar estado del pedido.
- [X] Validar transiciones de estado desde el service.
- [X] Cancelar pedido.
- [X] Devolver stock al cancelar pedido.

Estados implementados:

```txt
PENDIENTE
CONFIRMADO
EN_PREP
EN_CAMINO
ENTREGADO
CANCELADO
```

Transiciones válidas:

```txt
PENDIENTE  -> CONFIRMADO / CANCELADO
CONFIRMADO -> EN_PREP / CANCELADO
EN_PREP    -> EN_CAMINO
EN_CAMINO  -> ENTREGADO
ENTREGADO  -> final
CANCELADO  -> final
```

Formas de pago implementadas como enum:

```txt
MERCADOPAGO
EFECTIVO
TRANSFERENCIA
```

> Nota: La entidad `Pago` no fue implementada porque no era requerida para esta entrega.

### Gestión admin de usuarios

- [X] Listar usuarios activos.
- [X] Editar usuario.
- [X] Cambiar roles de usuario.
- [X] Deshabilitar usuario.
- [X] Soft delete de usuario.
- [X] Acceso permitido solo para `ADMIN`.

---

## Endpoints principales

### Auth

```txt
POST /api/v1/auth/register
POST /api/v1/auth/token
POST /api/v1/auth/logout
GET  /api/v1/auth/me
```

### Catálogo

```txt
GET    /productos/
GET    /productos/{producto_id}
POST   /productos/
PATCH  /productos/{producto_id}
DELETE /productos/{producto_id}
PATCH  /productos/{producto_id}/disponibilidad

GET    /categorias/
POST   /categorias/
PATCH  /categorias/{categoria_id}
DELETE /categorias/{categoria_id}

GET    /ingredientes/
POST   /ingredientes/
PATCH  /ingredientes/{ingrediente_id}
DELETE /ingredientes/{ingrediente_id}
```

### Direcciones

```txt
GET    /api/v1/direcciones/
POST   /api/v1/direcciones/
PATCH  /api/v1/direcciones/{direccion_id}
PATCH  /api/v1/direcciones/{direccion_id}/principal
DELETE /api/v1/direcciones/{direccion_id}
```

### Pedidos

```txt
POST  /api/v1/pedidos/
GET   /api/v1/pedidos/
GET   /api/v1/pedidos/{pedido_id}
PATCH /api/v1/pedidos/{pedido_id}/estado
PATCH /api/v1/pedidos/{pedido_id}/cancelar
```

### Admin usuarios

```txt
GET    /api/v1/admin/usuarios
PATCH  /api/v1/admin/usuarios/{user_id}
DELETE /api/v1/admin/usuarios/{user_id}
PATCH  /api/v1/admin/usuarios/{user_id}/roles
```

---

## Ejecución del proyecto

### Requisitos

- Python 3.11 o superior
- pip

Crear entorno virtual:

```bash
python -m venv .venv
```

Activar entorno virtual e instalar dependencias:

### Windows
```bash
.\.venv\Scripts\Activate.ps1
```

### Linux / macOS
```bash
source .venv/bin/activate
```

### Dependencias
```bash
pip install -r requirements.txt
```

Una vez activado el entorno virtual e instaladas las dependencias, ejecutar la aplicación con:
```bash
python -m fastapi dev app/main.py
```

Swagger:

```txt
http://localhost:8000/docs
```

---

## Variables de entorno

Ejemplo de `.env`:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=fastapi_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

SECRET_KEY=secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

## Pruebas realizadas

Se realizaron pruebas manuales desde Swagger y una prueba general automática mediante script.

Se validó:

- [X] Endpoints públicos funcionando sin login.
- [X] Endpoints protegidos devolviendo 401 sin autenticación.
- [X] Restricciones por rol devolviendo 403 cuando corresponde.
- [X] Login admin y login cliente.
- [X] Creación y cancelación de pedidos.
- [X] Descuento y devolución de stock.
- [X] Cambios de estado válidos.
- [X] Rechazo de transiciones inválidas.
- [X] Gestión admin de usuarios.

---

## Nota final

Se intentó cumplir con los puntos requeridos por la consigna, manteniendo una estructura clara, modular y extensible.
