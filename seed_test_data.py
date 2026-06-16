from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlmodel import SQLModel, Session, select

from app.core.database import create_db_and_tables, engine
from app.core.security import hash_password
from app.db.seed import seed_data

from app.modules.usuario.model import Usuario, UsuarioRol, DireccionEntrega
from app.modules.usuario.schema import UsuarioRolesUpdate
from app.modules.usuario.service import UsuarioService
from app.modules.usuario.unit_of_work import UsuarioUnitOfWork

from app.modules.categoria.model import Categoria
from app.modules.ingrediente.model import Ingrediente
from app.modules.producto.model import (
    Producto,
    ProductoCategoria,
    ProductoIngrediente,
    UnidadMedida,
)
from app.modules.pedido.model import (
    DetallePedido,
    EstadoPedido,
    FormaPago,
    HistorialEstadoPedido,
    Pago,
    Pedido,
)


def check(nombre: str, condicion: bool) -> None:
    if condicion:
        print(f"✅ {nombre}")
    else:
        raise Exception(f"❌ Falló prueba: {nombre}")


def buscar_unidad(session: Session, abreviatura: str) -> UnidadMedida:
    unidad = session.exec(
        select(UnidadMedida).where(UnidadMedida.abreviatura == abreviatura)
    ).first()

    if not unidad:
        raise Exception(f"No se encontró la unidad de medida {abreviatura}")

    return unidad


def crear_pago(
    pedido: Pedido,
    forma_pago_codigo: str,
    monto: Decimal,
    mp_status: str = "pending",
    mp_status_detail: str | None = "pending_waiting_payment",
    payment_method_id: str | None = None,
    mp_payment_id: int | None = None,
) -> Pago:
    return Pago(
        pedido=pedido,
        forma_pago_codigo=forma_pago_codigo,
        mp_payment_id=mp_payment_id,
        mp_status=mp_status,
        mp_status_detail=mp_status_detail,
        transaction_amount=monto,
        payment_method_id=payment_method_id or forma_pago_codigo.lower(),
        external_reference=str(uuid4()),
        idempotency_key=str(uuid4()),
    )


def agregar_historial(
    pedido: Pedido,
    estado_desde: str | None,
    estado_hacia: str,
    observacion: str,
) -> None:
    pedido.historial_estados.append(
        HistorialEstadoPedido(
            estado_desde_codigo=estado_desde,
            estado_hacia_codigo=estado_hacia,
            observacion=observacion,
        )
    )


def crear_detalle(
    pedido: Pedido,
    producto: Producto,
    cantidad: int,
    personalizacion: list[int] | None = None,
) -> DetallePedido:
    subtotal = producto.precio_base * cantidad

    detalle = DetallePedido(
        pedido=pedido,
        producto_id=producto.id,
        cantidad=cantidad,
        personalizacion=personalizacion or [],
        producto_nombre=producto.nombre,
        precio_unitario=producto.precio_base,
        subtotal=subtotal,
    )

    producto.stock_cantidad -= cantidad

    if producto.stock_cantidad == 0:
        producto.disponible = False

    return detalle


def crear_pedido(
    session: Session,
    usuario_id: int,
    direccion_id: int,
    forma_pago_codigo: str,
    estado_codigo: str,
    items: list[tuple[Producto, int, list[int]]],
    descuento: Decimal = Decimal("0.00"),
    costo_envio: Decimal = Decimal("500.00"),
    notas: str | None = None,
    mp_status: str = "pending",
    mp_status_detail: str | None = "pending_waiting_payment",
    payment_method_id: str | None = None,
    mp_payment_id: int | None = None,
) -> Pedido:
    pedido = Pedido(
        usuario_id=usuario_id,
        direccion_entrega_id=direccion_id,
        estado_codigo="PENDIENTE",
        forma_pago_codigo=forma_pago_codigo,
        subtotal=Decimal("0.00"),
        descuento=descuento,
        costo_envio=costo_envio,
        total=Decimal("0.00"),
        notas=notas,
    )

    agregar_historial(
        pedido=pedido,
        estado_desde=None,
        estado_hacia="PENDIENTE",
        observacion="Pedido creado desde seed de prueba.",
    )

    subtotal_pedido = Decimal("0.00")

    for producto, cantidad, personalizacion in items:
        detalle = crear_detalle(
            pedido=pedido,
            producto=producto,
            cantidad=cantidad,
            personalizacion=personalizacion,
        )
        pedido.detalles.append(detalle)
        subtotal_pedido += detalle.subtotal
        session.add(producto)

    total = subtotal_pedido - descuento + costo_envio

    pedido.subtotal = subtotal_pedido
    pedido.total = total

    if estado_codigo != "PENDIENTE":
        agregar_historial(
            pedido=pedido,
            estado_desde="PENDIENTE",
            estado_hacia=estado_codigo,
            observacion=f"Pedido avanzado a {estado_codigo} desde seed de prueba.",
        )
        pedido.estado_codigo = estado_codigo

    pedido.pagos.append(
        crear_pago(
            pedido=pedido,
            forma_pago_codigo=forma_pago_codigo,
            monto=total,
            mp_status=mp_status,
            mp_status_detail=mp_status_detail,
            payment_method_id=payment_method_id,
            mp_payment_id=mp_payment_id,
        )
    )

    session.add(pedido)
    session.flush()

    return pedido


def main():
    print("Limpiando base de datos...")
    SQLModel.metadata.drop_all(engine)

    print("Creando tablas...")
    create_db_and_tables()

    with Session(engine) as session:
        print("Cargando seed base...")
        seed_data(session)

        # ── Verificaciones de seed base ─────────────────────
        estados = session.exec(select(EstadoPedido)).all()
        formas_pago = session.exec(select(FormaPago)).all()
        unidades = session.exec(select(UnidadMedida)).all()

        codigos_estados = [estado.codigo for estado in estados]
        codigos_formas_pago = [forma.codigo for forma in formas_pago]
        abreviaturas_unidades = [unidad.abreviatura for unidad in unidades]

        check("Estados de pedido cargados", len(estados) == 5)
        check("Estado EN_CAMINO eliminado", "EN_CAMINO" not in codigos_estados)
        check("FormaPago EFECTIVO cargada", "EFECTIVO" in codigos_formas_pago)
        check("FormaPago MERCADOPAGO cargada", "MERCADOPAGO" in codigos_formas_pago)
        check("FormaPago TRANSFERENCIA cargada", "TRANSFERENCIA" in codigos_formas_pago)
        check("Unidades de medida cargadas", "ud" in abreviaturas_unidades and "g" in abreviaturas_unidades)

        unidad_ud = buscar_unidad(session, "ud")
        unidad_g = buscar_unidad(session, "g")
        unidad_ml = buscar_unidad(session, "ml")

        # ── Categorías ─────────────────────────────
        cat_pizzas = Categoria(
            nombre="Pizzas",
            descripcion="Pizzas artesanales",
            imagen_url="https://placehold.co/600x400?text=Pizzas",
            color="#ef4444",
        )
        cat_empanadas = Categoria(
            nombre="Empanadas",
            descripcion="Empanadas caseras",
            imagen_url="https://placehold.co/600x400?text=Empanadas",
            color="#f97316",
        )
        cat_bebidas = Categoria(
            nombre="Bebidas",
            descripcion="Bebidas frías",
            imagen_url="https://placehold.co/600x400?text=Bebidas",
            color="#3b82f6",
        )

        session.add(cat_pizzas)
        session.add(cat_empanadas)
        session.add(cat_bebidas)
        session.flush()

        # ── Ingredientes con stock ─────────────────
        ing_mozzarella = Ingrediente(
            nombre="Mozzarella",
            descripcion="Queso mozzarella",
            es_alergeno=False,
            stock_cantidad=5000,
        )
        ing_jamon = Ingrediente(
            nombre="Jamón",
            descripcion="Jamón cocido",
            es_alergeno=False,
            stock_cantidad=3000,
        )
        ing_tomate = Ingrediente(
            nombre="Tomate",
            descripcion="Salsa de tomate",
            es_alergeno=False,
            stock_cantidad=4000,
        )
        ing_mani = Ingrediente(
            nombre="Maní",
            descripcion="Ingrediente alérgeno de prueba",
            es_alergeno=True,
            stock_cantidad=1000,
        )

        session.add(ing_mozzarella)
        session.add(ing_jamon)
        session.add(ing_tomate)
        session.add(ing_mani)
        session.flush()

        check("Ingredientes con stock cargados", ing_mozzarella.stock_cantidad == 5000)
        check("Ingrediente alérgeno cargado", ing_mani.es_alergeno is True)

        # ── Productos con unidad de venta ──────────
        pizza = Producto(
            nombre="Pizza Mozzarella",
            descripcion="Pizza clásica con mozzarella",
            precio_base=Decimal("8500.00"),
            imagenes_url=["https://placehold.co/600x400?text=Pizza+Mozzarella"],
            stock_cantidad=10,
            disponible=True,
            unidad_venta_id=unidad_ud.id,
        )
        pizza.categorias.append(
            ProductoCategoria(
                categoria_id=cat_pizzas.id,
                es_principal=True,
            )
        )
        pizza.ingredientes.append(
            ProductoIngrediente(
                ingrediente_id=ing_mozzarella.id,
                cantidad=Decimal("250.00"),
                unidad_medida_id=unidad_g.id,
                es_removible=True,
            )
        )
        pizza.ingredientes.append(
            ProductoIngrediente(
                ingrediente_id=ing_tomate.id,
                cantidad=Decimal("100.00"),
                unidad_medida_id=unidad_g.id,
                es_removible=True,
            )
        )

        empanada = Producto(
            nombre="Empanada de Jamón y Queso",
            descripcion="Empanada casera de jamón y queso",
            precio_base=Decimal("1200.00"),
            imagenes_url=["https://placehold.co/600x400?text=Empanada+JyQ"],
            stock_cantidad=30,
            disponible=True,
            unidad_venta_id=unidad_ud.id,
        )
        empanada.categorias.append(
            ProductoCategoria(
                categoria_id=cat_empanadas.id,
                es_principal=True,
            )
        )
        empanada.ingredientes.append(
            ProductoIngrediente(
                ingrediente_id=ing_jamon.id,
                cantidad=Decimal("50.00"),
                unidad_medida_id=unidad_g.id,
                es_removible=False,
            )
        )
        empanada.ingredientes.append(
            ProductoIngrediente(
                ingrediente_id=ing_mozzarella.id,
                cantidad=Decimal("40.00"),
                unidad_medida_id=unidad_g.id,
                es_removible=False,
            )
        )

        bebida = Producto(
            nombre="Coca Cola 500ml",
            descripcion="Gaseosa individual",
            precio_base=Decimal("1800.00"),
            imagenes_url=["https://placehold.co/600x400?text=Coca+Cola"],
            stock_cantidad=20,
            disponible=True,
            unidad_venta_id=unidad_ud.id,
        )
        bebida.categorias.append(
            ProductoCategoria(
                categoria_id=cat_bebidas.id,
                es_principal=True,
            )
        )

        jugo = Producto(
            nombre="Jugo de Naranja 1L",
            descripcion="Jugo natural de naranja",
            precio_base=Decimal("2500.00"),
            imagenes_url=["https://placehold.co/600x400?text=Jugo+Naranja"],
            stock_cantidad=15,
            disponible=True,
            unidad_venta_id=unidad_ml.id,
        )
        jugo.categorias.append(
            ProductoCategoria(
                categoria_id=cat_bebidas.id,
                es_principal=True,
            )
        )

        session.add(pizza)
        session.add(empanada)
        session.add(bebida)
        session.add(jugo)
        session.flush()

        check("Producto con unidad de venta cargado", pizza.unidad_venta_id == unidad_ud.id)
        check("ProductoIngrediente con cantidad/unidad cargado", pizza.ingredientes[0].unidad_medida_id == unidad_g.id)

        # ── Usuarios ───────────────────────────────
        stock_user = Usuario(
            nombre="Stock",
            apellido="Sistema",
            email="stock@test.com",
            celular=None,
            password_hash=hash_password("stock123"),
            disabled=False,
        )
        stock_user.roles.append(UsuarioRol(rol_codigo="STOCK"))

        pedidos_user = Usuario(
            nombre="Pedidos",
            apellido="Sistema",
            email="pedidos@test.com",
            celular=None,
            password_hash=hash_password("pedidos123"),
            disabled=False,
        )
        pedidos_user.roles.append(UsuarioRol(rol_codigo="PEDIDOS"))

        cliente = Usuario(
            nombre="Cliente",
            apellido="Prueba",
            email="cliente@test.com",
            celular="3511234567",
            password_hash=hash_password("cliente123"),
            disabled=False,
        )
        cliente.roles.append(UsuarioRol(rol_codigo="CLIENT"))

        cliente2 = Usuario(
            nombre="Cliente",
            apellido="MercadoPago",
            email="cliente.mp@test.com",
            celular="3517654321",
            password_hash=hash_password("cliente123"),
            disabled=False,
        )
        cliente2.roles.append(UsuarioRol(rol_codigo="CLIENT"))

        session.add(stock_user)
        session.add(pedidos_user)
        session.add(cliente)
        session.add(cliente2)
        session.flush()

        check("Usuario STOCK cargado", stock_user.id is not None)
        check("Usuario PEDIDOS cargado", pedidos_user.id is not None)
        check("Usuario CLIENT cargado", cliente.id is not None)
        check("Segundo CLIENT cargado", cliente2.id is not None)

        # ── Direcciones sin latitud/longitud ─────────
        direccion = DireccionEntrega(
            usuario_id=cliente.id,
            alias="Casa",
            linea1="Av. Siempre Viva 742",
            linea2=None,
            ciudad="Córdoba",
            provincia="Córdoba",
            codigo_postal="5000",
            es_principal=True,
        )
        direccion2 = DireccionEntrega(
            usuario_id=cliente2.id,
            alias="Trabajo",
            linea1="Bv. San Juan 100",
            linea2="Piso 2",
            ciudad="Córdoba",
            provincia="Córdoba",
            codigo_postal="5000",
            es_principal=True,
        )

        session.add(direccion)
        session.add(direccion2)
        session.flush()

        check("Dirección cargada sin latitud/longitud", not hasattr(direccion, "latitud") and not hasattr(direccion, "longitud"))

        # ── Pedidos con varias formas de pago, estados y personalización ─────
        pedido_efectivo_pendiente = crear_pedido(
            session=session,
            usuario_id=cliente.id,
            direccion_id=direccion.id,
            forma_pago_codigo="EFECTIVO",
            estado_codigo="PENDIENTE",
            items=[
                (pizza, 1, [ing_tomate.id]),
                (bebida, 2, []),
            ],
            costo_envio=Decimal("500.00"),
            notas="Efectivo pendiente con personalización: sin tomate.",
            mp_status="pending",
            mp_status_detail="cash_pending",
            payment_method_id="cash",
        )

        pedido_mp_pendiente = crear_pedido(
            session=session,
            usuario_id=cliente2.id,
            direccion_id=direccion2.id,
            forma_pago_codigo="MERCADOPAGO",
            estado_codigo="PENDIENTE",
            items=[
                (empanada, 3, []),
                (jugo, 1, []),
            ],
            costo_envio=Decimal("500.00"),
            notas="MercadoPago pendiente para probar /api/v1/pagos/crear.",
            mp_status="pending",
            mp_status_detail="pending_waiting_payment",
            payment_method_id="mercadopago",
        )

        pedido_mp_aprobado = crear_pedido(
            session=session,
            usuario_id=cliente2.id,
            direccion_id=direccion2.id,
            forma_pago_codigo="MERCADOPAGO",
            estado_codigo="CONFIRMADO",
            items=[
                (pizza, 1, [ing_mozzarella.id]),
            ],
            costo_envio=Decimal("500.00"),
            notas="MercadoPago aprobado simulado.",
            mp_status="approved",
            mp_status_detail="accredited",
            payment_method_id="account_money",
            mp_payment_id=987654321,
        )

        pedido_transferencia_cancelado = crear_pedido(
            session=session,
            usuario_id=cliente.id,
            direccion_id=direccion.id,
            forma_pago_codigo="TRANSFERENCIA",
            estado_codigo="CANCELADO",
            items=[
                (empanada, 2, []),
            ],
            costo_envio=Decimal("500.00"),
            notas="Transferencia cancelada para probar estado terminal.",
            mp_status="rejected",
            mp_status_detail="transfer_cancelled",
            payment_method_id="bank_transfer",
        )

        session.commit()

        # ── Checks de pedidos/pagos ─────────────────
        check("Pedido EFECTIVO creado", pedido_efectivo_pendiente.id is not None)
        check("Pedido MERCADOPAGO pendiente creado", pedido_mp_pendiente.id is not None)
        check("Pedido MERCADOPAGO aprobado creado", pedido_mp_aprobado.id is not None)
        check("Pedido TRANSFERENCIA cancelado creado", pedido_transferencia_cancelado.id is not None)

        check("DetallePedido con personalización cargado", pedido_efectivo_pendiente.detalles[0].personalizacion == [ing_tomate.id])
        check("Historial inicial cargado", pedido_efectivo_pendiente.historial_estados[0].estado_hacia_codigo == "PENDIENTE")
        check("Historial de confirmado cargado", pedido_mp_aprobado.historial_estados[-1].estado_hacia_codigo == "CONFIRMADO")
        check("Pago MercadoPago pendiente cargado", pedido_mp_pendiente.pagos[0].mp_status == "pending")
        check("Pago MercadoPago aprobado cargado", pedido_mp_aprobado.pagos[0].mp_status == "approved")
        check("Pago con external_reference cargado", pedido_mp_pendiente.pagos[0].external_reference is not None)
        check("Pago con idempotency_key cargado", pedido_mp_pendiente.pagos[0].idempotency_key is not None)
        check("Pago con mp_payment_id simulado cargado", pedido_mp_aprobado.pagos[0].mp_payment_id == 987654321)


        # ── Checks anti-regresión de consignas ───────────────
        import os

        archivos_py = []
        for raiz, _, archivos in os.walk("app"):
            for archivo in archivos:
                if archivo.endswith(".py"):
                    archivos_py.append(os.path.join(raiz, archivo))

        archivos_enums = [archivo for archivo in archivos_py if archivo.endswith("enums.py")]
        check("No existen archivos enums.py en app", len(archivos_enums) == 0)

        contenido_backend = ""
        for archivo in archivos_py:
            with open(archivo, "r", encoding="utf-8") as f:
                contenido_backend += f.read() + "\n"

        check("No se importa from enum import Enum", "from enum import Enum" not in contenido_backend)
        check("No se importan módulos enums", ".enums import" not in contenido_backend and "import app.modules.pedido.enums" not in contenido_backend)
        check("DireccionEntrega no tiene latitud", not hasattr(DireccionEntrega, "latitud"))
        check("DireccionEntrega no tiene longitud", not hasattr(DireccionEntrega, "longitud"))

        from app.core.websocket import websocket_manager

        check("WebSocket Manager tiene rooms", hasattr(websocket_manager, "rooms"))
        check("WebSocket permite broadcast por rol", hasattr(websocket_manager, "broadcast_to_roles"))
        check("WebSocket permite broadcast por pedido", hasattr(websocket_manager, "broadcast_to_order"))
        check("WebSocket permite suscripción a pedido", hasattr(websocket_manager, "join_order_room"))

        columnas_pago = Pago.__table__.columns.keys()
        columnas_pago_requeridas = [
            "mp_payment_id",
            "mp_status",
            "mp_status_detail",
            "transaction_amount",
            "payment_method_id",
            "external_reference",
            "idempotency_key",
        ]

        for columna in columnas_pago_requeridas:
            check(f"Pago tiene columna {columna}", columna in columnas_pago)

        check("Pago ya no tiene columna estado vieja", "estado" not in columnas_pago)
        check("Pago ya no tiene columna monto vieja", "monto" not in columnas_pago)
        check("Pago ya no tiene columna referencia_externa vieja", "referencia_externa" not in columnas_pago)

        # ── Pruebas de reglas admin/roles ──────────
        with UsuarioUnitOfWork(session) as uow:
            service = UsuarioService(uow)

            listado_admin = service.list_admin(offset=0, limit=100)
            emails_listados = [usuario.email for usuario in listado_admin.data]

            check("Listado admin no muestra CLIENT", "cliente@test.com" not in emails_listados)
            check("Listado admin muestra STOCK", "stock@test.com" in emails_listados)
            check("Listado admin muestra PEDIDOS", "pedidos@test.com" in emails_listados)

            try:
                service.update_roles(
                    cliente.id,
                    UsuarioRolesUpdate(roles=["ADMIN"]),
                )
                raise Exception("❌ Falló prueba: permitió asignar ADMIN")
            except HTTPException as exc:
                check("No permite asignar ADMIN desde admin usuarios", exc.status_code == 400)

            try:
                service.update_roles(
                    pedidos_user.id,
                    UsuarioRolesUpdate(roles=["CLIENT"]),
                )
                raise Exception("❌ Falló prueba: permitió asignar CLIENT desde admin usuarios")
            except HTTPException as exc:
                check("No permite asignar CLIENT desde admin usuarios", exc.status_code == 400)

        print("\nDatos de prueba cargados correctamente.")
        print("Admin: admin@admin.com / admin123")
        print("Stock: stock@test.com / stock123")
        print("Pedidos: pedidos@test.com / pedidos123")
        print("Cliente: cliente@test.com / cliente123")
        print("Cliente MP: cliente.mp@test.com / cliente123")
        print("\nPedidos creados:")
        print(f"- EFECTIVO PENDIENTE: pedido_id={pedido_efectivo_pendiente.id}")
        print(f"- MERCADOPAGO PENDIENTE: pedido_id={pedido_mp_pendiente.id}")
        print(f"- MERCADOPAGO CONFIRMADO/APROBADO: pedido_id={pedido_mp_aprobado.id}")
        print(f"- TRANSFERENCIA CANCELADO: pedido_id={pedido_transferencia_cancelado.id}")
        print("\nPara probar MercadoPago backend:")
        print(f"POST /api/v1/pagos/crear con pedido_id={pedido_mp_pendiente.id}")
        print("\nSeed test data Parte 3 OK.")


if __name__ == "__main__":
    main()
