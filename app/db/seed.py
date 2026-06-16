# app/db/seed.py
from sqlmodel import Session, select

from app.core.security import hash_password
from app.modules.pedido.model import EstadoPedido, FormaPago
from app.modules.producto.model import UnidadMedida
from app.modules.usuario.model import Rol, Usuario, UsuarioRol


def seed_data(session: Session) -> None:
    seed_roles(session)
    seed_estados_pedido(session)
    seed_formas_pago(session)
    seed_unidades_medida(session)
    seed_admin_user(session)
    session.commit()


def seed_roles(session: Session) -> None:
    roles = [
        ("ADMIN", "Administrador", "Acceso completo al sistema."),
        ("STOCK", "Stock", "Gestión de stock y disponibilidad de productos."),
        ("PEDIDOS", "Pedidos", "Gestión y cambio de estado de pedidos."),
        ("CLIENT", "Cliente", "Cliente de la tienda."),
    ]

    for codigo, nombre, descripcion in roles:
        existing = session.get(Rol, codigo)
        if not existing:
            session.add(
                Rol(
                    codigo=codigo,
                    nombre=nombre,
                    descripcion=descripcion,
                )
            )


def seed_estados_pedido(session: Session) -> None:
    estados = [
        ("PENDIENTE", "Pendiente", "Pedido creado, pendiente de confirmación.", 1, False),
        ("CONFIRMADO", "Confirmado", "Pedido confirmado.", 2, False),
        ("EN_PREP", "En preparación", "Pedido en preparación.", 3, False),
        ("ENTREGADO", "Entregado", "Pedido entregado.", 4, True),
        ("CANCELADO", "Cancelado", "Pedido cancelado.", 5, True),
    ]

    for codigo, nombre, descripcion, orden, es_terminal in estados:
        existing = session.get(EstadoPedido, codigo)

        if existing:
            existing.nombre = nombre
            existing.descripcion = descripcion
            existing.orden = orden
            existing.es_terminal = es_terminal
        else:
            session.add(
                EstadoPedido(
                    codigo=codigo,
                    nombre=nombre,
                    descripcion=descripcion,
                    orden=orden,
                    es_terminal=es_terminal,
                )
            )


def seed_formas_pago(session: Session) -> None:
    formas_pago = [
        ("EFECTIVO", "Efectivo", "Pago en efectivo al recibir el pedido.", True),
        ("MERCADOPAGO", "MercadoPago", "Pago mediante MercadoPago.", True),
        ("TRANSFERENCIA", "Transferencia", "Pago mediante transferencia bancaria.", True),
    ]

    for codigo, nombre, descripcion, habilitado in formas_pago:
        existing = session.get(FormaPago, codigo)

        if existing:
            existing.nombre = nombre
            existing.descripcion = descripcion
            existing.habilitado = habilitado
        else:
            session.add(
                FormaPago(
                    codigo=codigo,
                    nombre=nombre,
                    descripcion=descripcion,
                    habilitado=habilitado,
                )
            )


def seed_unidades_medida(session: Session) -> None:
    unidades = [
        ("unidad", "ud", "unidad"),
        ("porción", "por", "unidad"),
        ("kilogramo", "kg", "peso"),
        ("litro", "L", "volumen"),
        ("gramo", "g", "peso"),
        ("mililitro", "ml", "volumen"),
    ]

    for nombre, abreviatura, tipo in unidades:
        existing = session.exec(
            select(UnidadMedida).where(UnidadMedida.abreviatura == abreviatura)
        ).first()

        if existing:
            existing.nombre = nombre
            existing.tipo = tipo
        else:
            session.add(
                UnidadMedida(
                    nombre=nombre,
                    abreviatura=abreviatura,
                    tipo=tipo,
                )
            )


def seed_admin_user(session: Session) -> None:
    admin_email = "admin@admin.com"

    existing_admin = session.exec(
        select(Usuario).where(Usuario.email == admin_email)
    ).first()

    if existing_admin:
        return

    admin = Usuario(
        nombre="Admin",
        apellido="Sistema",
        email=admin_email,
        celular=None,
        password_hash=hash_password("admin123"),
        disabled=False,
    )

    admin.roles.append(
        UsuarioRol(
            rol_codigo="ADMIN",
        )
    )

    session.add(admin)
