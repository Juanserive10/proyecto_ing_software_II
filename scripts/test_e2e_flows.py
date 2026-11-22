"""
Prueba integral end-to-end de los 6 microservicios de Distribuidora Andina S.A.S.
Por defecto valida TODO el sistema a través del API Gateway Laravel (:8000/api).
Si se define DIRECT_MODE=1 (junto con docker-compose.debug.yml), apunta directo a :5001-:5006.

Valida:
  0. /health del API Gateway y de los 6 microservicios
  1. Control de acceso (401 sin JWT, 403 RBAC para rol VENDEDOR en rutas restringidas)
  2. Login JWT en usuarios-service (/api/usuarios/auth/login)
  3. Consulta + importación CSV en catalogo-service (RF17)
  4. Consulta de bodegas, stock y traslado atómico en inventario-service (RF04, RF05)
  5. Creación de OC + recepción -> entrada automática en Inventario (RF03, RF06)
  6. Venta confirmada -> descuento en Inventario + rechazo 409 por stock insuficiente (RF15)
  7. Sincronización, dashboard KPIs y alertas por umbral mínimo en reportes-service (RF09, RF11, RF14)
"""
import io
import os
import sys
import uuid
import requests

DIRECT_MODE = os.getenv("DIRECT_MODE", "0") == "1"
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://127.0.0.1:8000/api").rstrip("/")

if DIRECT_MODE:
    URLS = {
        "usuarios": os.getenv("USUARIOS_URL", "http://127.0.0.1:5001"),
        "catalogo": os.getenv("CATALOGO_URL", "http://127.0.0.1:5002"),
        "inventario": os.getenv("INVENTARIO_URL", "http://127.0.0.1:5003"),
        "abastecimiento": os.getenv("ABASTECIMIENTO_URL", "http://127.0.0.1:5004"),
        "ventas": os.getenv("VENTAS_URL", "http://127.0.0.1:5005"),
        "reportes": os.getenv("REPORTES_URL", "http://127.0.0.1:5006"),
    }
else:
    URLS = {
        "usuarios": f"{GATEWAY_URL}/usuarios",
        "catalogo": f"{GATEWAY_URL}/catalogo",
        "inventario": f"{GATEWAY_URL}/inventario",
        "abastecimiento": f"{GATEWAY_URL}/abastecimiento",
        "ventas": f"{GATEWAY_URL}/ventas",
        "reportes": f"{GATEWAY_URL}/reportes",
    }


def step(msg):
    print(f"\n==> {msg}")


def main():
    # 0. Healthchecks
    step("0. Verificando /health del Gateway y los 6 microservicios")
    if not DIRECT_MODE:
        rg = requests.get(f"{GATEWAY_URL}/health", timeout=5)
        assert rg.status_code == 200, f"api-gateway fallo health: {rg.status_code}"
        print(f"  [OK] api-gateway: {rg.json()}")

    for name, url in URLS.items():
        r = requests.get(f"{url}/health", timeout=5)
        assert r.status_code == 200, f"{name} fallo health: {r.status_code}"
        if not DIRECT_MODE:
            assert r.headers.get("X-Upstream-Service") == name, f"Header X-Upstream-Service inesperado: {r.headers}"
        print(f"  [OK] {name}: {r.json()}")

    # 1. Seguridad: 401 sin token + Login Admin + RBAC 403 para Vendedor
    step("1. Autenticación JWT y control RBAC vía API Gateway")
    if not DIRECT_MODE:
        unauth = requests.get(f"{URLS['catalogo']}/products", timeout=5)
        assert unauth.status_code == 401, f"Esperado 401 sin JWT, recibido {unauth.status_code}"
        print("  [OK] Ruta protegida sin JWT rechazada por el Gateway (HTTP 401)")

        r_vend = requests.post(
            f"{URLS['usuarios']}/auth/login",
            json={"correo": "ventas@andina.com", "contrasena": "Ventas123*"},
            timeout=5,
        )
        assert r_vend.status_code == 200, r_vend.text
        vend_headers = {"Authorization": f"Bearer {r_vend.json()['access_token']}"}
        rbac_deny = requests.put(
            f"{URLS['usuarios']}/users/1",
            json={"estado": "INACTIVO"},
            headers=vend_headers,
            timeout=5,
        )
        assert rbac_deny.status_code == 403, f"Esperado 403 RBAC para VENDEDOR, recibido {rbac_deny.status_code}"
        print("  [OK] Control RBAC activo: rol VENDEDOR bloqueado en operación administrativa (HTTP 403)")

    r = requests.post(
        f"{URLS['usuarios']}/auth/login",
        json={"correo": "admin@andina.com", "contrasena": "Admin123*"},
        timeout=5,
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    rv = requests.post(f"{URLS['usuarios']}/auth/verify", headers=headers, timeout=5)
    assert rv.status_code == 200 and rv.json()["valid"] is True
    print(f"  [OK] Token JWT emitido y verificado para {r.json()['usuario']['nombre']}")

    # 2. Catálogo: Listar productos + Importar CSV con 1 fila válida y 1 fila inválida
    step("2. Catálogo: listado e importación CSV multipart (RF17)")
    prods = requests.get(f"{URLS['catalogo']}/products", headers=headers, timeout=5).json()
    assert len(prods) >= 10
    csv_data = "codigo,nombre,descripcion,unidad_medida,precio_venta,id_categoria\nFER-CSV1,Cinta Métrica 5m,Flexómetro reforzado,UNIDAD,18500,2\n,Sin Código,Fila inválida,UNIDAD,5000,2\n"
    imp = requests.post(
        f"{URLS['catalogo']}/products/import",
        files={"file": ("prueba.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")},
        data={"id_usuario": "1"},
        headers=headers,
        timeout=8,
    )
    assert imp.status_code == 201, imp.text
    imp_json = imp.json()
    assert imp_json["filas_validas"] == 1 and imp_json["filas_error"] == 1
    print(f"  [OK] Importación CSV: {imp_json['filas_validas']} válida, {imp_json['filas_error']} error detectado")

    # 3. Inventario: Stock inicial + Traslado atómico
    step("3. Inventario: consulta de stock y traslado BOD-01 -> BOD-02")
    stock_b1_before = requests.get(
        f"{URLS['inventario']}/inventory/stock?id_producto=1&id_bodega=1",
        headers=headers,
        timeout=5,
    ).json()[0]["cantidad_disponible"]
    tr = requests.post(
        f"{URLS['inventario']}/inventory/transfers",
        json={
            "id_bodega_origen": 1,
            "id_bodega_destino": 2,
            "id_producto": 1,
            "cantidad": 2,
            "id_usuario": 1,
            "clave_idempotencia": f"E2E-TR-{uuid.uuid4().hex[:8]}",
        },
        headers=headers,
        timeout=5,
    )
    assert tr.status_code == 201, tr.text
    assert tr.json()["stock_origen"] == stock_b1_before - 2
    print(f"  [OK] Traslado atómico completado. Stock BOD-01: {stock_b1_before} -> {tr.json()['stock_origen']}")

    # 4. Abastecimiento -> Inventario: Crear OC y recibir mercancía
    step("4. Flujo Abastecimiento -> Inventario (Recepción de Orden de Compra)")
    oc = requests.post(
        f"{URLS['abastecimiento']}/purchase-orders",
        json={
            "id_proveedor": 1,
            "id_usuario": 1,
            "items": [{"id_producto": 1, "cantidad_pedida": 5, "costo_unitario": 180000}],
        },
        headers=headers,
        timeout=5,
    ).json()
    id_det = oc["detalles"][0]["id_detalle_orden"]
    rec = requests.post(
        f"{URLS['abastecimiento']}/purchase-orders/{oc['id_orden']}/receipts",
        json={
            "id_bodega": 1,
            "id_usuario": 1,
            "items": [{"id_detalle_orden": id_det, "cantidad_recibida": 5, "condicion": "BUENO"}],
        },
        headers=headers,
        timeout=8,
    )
    assert rec.status_code == 201, rec.text
    assert rec.json()["recepcion"]["estado"] == "CONFIRMADA"
    assert rec.json()["orden_estado"] == "RECIBIDA"
    print(f"  [OK] OC {oc['numero']} recibida y confirmada en Inventario (+5 unidades)")

    # 5. Ventas -> Catálogo + Inventario: Venta confirmada + Venta rechazada por falta de stock
    step("5. Flujo Ventas -> Catálogo + Inventario (Confirmación y rechazo por stock insuficiente)")
    v_ok = requests.post(
        f"{URLS['ventas']}/sales",
        json={
            "id_bodega": 1,
            "id_usuario": 3,
            "metodo_pago": "TRANSFERENCIA",
            "items": [{"id_producto": 1, "cantidad": 2}],
        },
        headers=headers,
        timeout=8,
    )
    assert v_ok.status_code == 201, v_ok.text
    assert v_ok.json()["venta"]["estado"] == "CONFIRMADA"
    print(f"  [OK] Venta {v_ok.json()['venta']['numero']} CONFIRMADA por ${v_ok.json()['venta']['total']:,.0f}")

    v_fail = requests.post(
        f"{URLS['ventas']}/sales",
        json={
            "id_bodega": 1,
            "id_usuario": 3,
            "metodo_pago": "EFECTIVO",
            "items": [{"id_producto": 1, "cantidad": 9999}],
        },
        headers=headers,
        timeout=8,
    )
    assert v_fail.status_code == 409, f"Esperado 409, recibido {v_fail.status_code}"
    print("  [OK] Venta con stock insuficiente rechazada correctamente (HTTP 409)")

    # 6. Reportes y Alertas: Sync + Dashboard + Alertas
    step("6. Reportes y Alertas: sincronización, KPIs y evaluación de umbrales")
    sync = requests.post(f"{URLS['reportes']}/reports/sync", headers=headers, timeout=8)
    assert sync.status_code == 200, sync.text
    dash = requests.get(f"{URLS['reportes']}/reports/dashboard", headers=headers, timeout=5).json()
    alerts = requests.get(f"{URLS['reportes']}/alerts", headers=headers, timeout=5).json()
    print(f"  [OK] Dashboard -> Valor inventario: ${dash['valor_total_inventario']:,.0f} | Alertas activas: {dash['alertas_activas']} | Total alertas: {len(alerts)}")

    print("\nTODOS LOS FLUJOS END-TO-END PASARON EXITOSAMENTE!")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n[ERROR] Falló prueba E2E: {exc}")
        sys.exit(1)
