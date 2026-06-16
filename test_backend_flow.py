import requests

BASE_URL = "http://localhost:8000"

ADMIN_EMAIL = "admin@admin.com"
ADMIN_PASSWORD = "admin123"

CLIENT_EMAIL = "cliente2@cliente.com"
CLIENT_PASSWORD = "cliente123"

PRODUCTO_ID = 1
DIRECCION_ID = 3


def check(nombre, response, expected_status):
    if response.status_code == expected_status:
        print(f"✅ {nombre}")
    else:
        print(f"❌ {nombre}")
        print(f"   Esperado: {expected_status}")
        print(f"   Recibido: {response.status_code}")
        try:
            print(f"   Respuesta: {response.json()}")
        except Exception:
            print(f"   Respuesta: {response.text}")


def login(email, password):
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/api/v1/auth/token",
        data={
            "username": email,
            "password": password,
        },
    )
    check(f"Login {email}", response, 200)
    return session


def main():
    print("\n=== PRUEBAS BACKEND PARTE 2 ===\n")

    public_session = requests.Session()

    # Público
    check("GET productos público", public_session.get(f"{BASE_URL}/productos/"), 200)
    check("GET categorías público", public_session.get(f"{BASE_URL}/categorias/"), 200)
    check("GET ingredientes público", public_session.get(f"{BASE_URL}/ingredientes/"), 200)

    check("POST producto sin login debe fallar", public_session.post(f"{BASE_URL}/productos/", json={}), 401)
    check("GET admin usuarios sin login debe fallar", public_session.get(f"{BASE_URL}/api/v1/admin/usuarios"), 401)
    check("GET pedidos sin login debe fallar", public_session.get(f"{BASE_URL}/api/v1/pedidos/"), 401)
    check("GET direcciones sin login debe fallar", public_session.get(f"{BASE_URL}/api/v1/direcciones/"), 401)

    # Cliente
    client = login(CLIENT_EMAIL, CLIENT_PASSWORD)

    check("GET /me cliente", client.get(f"{BASE_URL}/api/v1/auth/me"), 200)
    check("GET direcciones cliente", client.get(f"{BASE_URL}/api/v1/direcciones/"), 200)
    check("POST producto como cliente debe fallar", client.post(f"{BASE_URL}/productos/", json={}), 403)
    check("GET admin usuarios como cliente debe fallar", client.get(f"{BASE_URL}/api/v1/admin/usuarios"), 403)

    pedido_body = {
        "direccion_entrega_id": DIRECCION_ID,
        "forma_pago": "EFECTIVO",
        "detalles": [
            {
                "producto_id": PRODUCTO_ID,
                "cantidad": 1
            }
        ]
    }

    pedido_response = client.post(f"{BASE_URL}/api/v1/pedidos/", json=pedido_body)
    check("Crear pedido como cliente", pedido_response, 201)

    pedido_id = None
    if pedido_response.status_code == 201:
        pedido_id = pedido_response.json()["id"]

    check("GET pedidos cliente", client.get(f"{BASE_URL}/api/v1/pedidos/"), 200)

    if pedido_id:
        check(
            "Cliente no puede cambiar estado manualmente",
            client.patch(
                f"{BASE_URL}/api/v1/pedidos/{pedido_id}/estado",
                json={"estado": "CONFIRMADO"},
            ),
            403,
        )

        check(
            "Cliente cancela su pedido",
            client.patch(f"{BASE_URL}/api/v1/pedidos/{pedido_id}/cancelar"),
            200,
        )

    # Admin
    admin = login(ADMIN_EMAIL, ADMIN_PASSWORD)

    check("GET admin usuarios como admin", admin.get(f"{BASE_URL}/api/v1/admin/usuarios"), 200)
    check("GET pedidos como admin", admin.get(f"{BASE_URL}/api/v1/pedidos/"), 200)

    pedido_admin_response = client.post(f"{BASE_URL}/api/v1/pedidos/", json=pedido_body)
    check("Crear pedido para probar estados", pedido_admin_response, 201)

    if pedido_admin_response.status_code == 201:
        pedido_estado_id = pedido_admin_response.json()["id"]

        check(
            "Transición inválida PENDIENTE -> ENTREGADO debe fallar",
            admin.patch(
                f"{BASE_URL}/api/v1/pedidos/{pedido_estado_id}/estado",
                json={"estado": "ENTREGADO"},
            ),
            400,
        )

        check(
            "Admin cambia PENDIENTE -> CONFIRMADO",
            admin.patch(
                f"{BASE_URL}/api/v1/pedidos/{pedido_estado_id}/estado",
                json={"estado": "CONFIRMADO"},
            ),
            200,
        )

        check(
            "Admin cambia CONFIRMADO -> EN_PREP",
            admin.patch(
                f"{BASE_URL}/api/v1/pedidos/{pedido_estado_id}/estado",
                json={"estado": "EN_PREP"},
            ),
            200,
        )

    print("\n=== FIN DE PRUEBAS ===\n")


if __name__ == "__main__":
    main()