"""
Suite de 15 pruebas de rendimiento en Locust para Distribuidora Andina S.A.S.
Integrante: Juan Sebastián Rivera Valencia
Microservicios cubiertos: Inventario y Almacenes (5003), Abastecimiento (5004),
Ventas (5005) y Reportes y Alertas (5006).

Ejecución:
  locust -f locustfile.py --headless -u 30 -r 5 -t 60s --csv=resultados_normal
  locust -f locustfile.py --headless -u 100 -r 15 -t 60s --csv=resultados_pico
  locust -f locustfile.py --headless -u 200 -r 30 -t 60s --csv=resultados_estres
"""
import os
import random
import uuid
from locust import HttpUser, task, between

INVENTARIO_HOST = os.getenv("INVENTARIO_URL", "http://localhost:5003")
ABASTECIMIENTO_HOST = os.getenv("ABASTECIMIENTO_URL", "http://localhost:5004")
VENTAS_HOST = os.getenv("VENTAS_URL", "http://localhost:5005")
REPORTES_HOST = os.getenv("REPORTES_URL", "http://localhost:5006")


class InventarioVentasPerformanceUser(HttpUser):
    wait_time = between(0.3, 1.2)
    host = INVENTARIO_HOST

    # --- INVENTARIO Y ALMACENES (PR-01 a PR-06) ---
    @task(6)
    def pr01_consultar_stock_general(self):
        self.client.get(f"{INVENTARIO_HOST}/inventory/stock", name="PR01 GET /inventory/stock")

    @task(5)
    def pr02_consultar_stock_por_bodega(self):
        bodega = random.choice([1, 2])
        self.client.get(f"{INVENTARIO_HOST}/inventory/stock?id_bodega={bodega}", name="PR02 GET /inventory/stock?id_bodega")

    @task(5)
    def pr03_consultar_stock_por_producto(self):
        prod = random.randint(1, 10)
        self.client.get(f"{INVENTARIO_HOST}/inventory/stock?id_producto={prod}", name="PR03 GET /inventory/stock?id_producto")

    @task(4)
    def pr04_consultar_kardex(self):
        self.client.get(f"{INVENTARIO_HOST}/inventory/movements?limit=50", name="PR04 GET /inventory/movements")

    @task(3)
    def pr05_listar_bodegas(self):
        self.client.get(f"{INVENTARIO_HOST}/warehouses", name="PR05 GET /warehouses")

    @task(2)
    def pr06_registrar_entrada_stock(self):
        self.client.post(
            f"{INVENTARIO_HOST}/inventory/movements",
            json={
                "tipo": "ENTRADA",
                "id_producto": random.randint(1, 10),
                "cantidad": 5,
                "id_bodega_destino": random.choice([1, 2]),
                "id_usuario": 1,
                "tipo_referencia": "LOAD_TEST",
                "clave_idempotencia": f"LT-ENT-{uuid.uuid4().hex[:12]}",
            },
            name="PR06 POST /inventory/movements (ENTRADA)",
        )

    @task(1)
    def pr07_registrar_traslado_bodegas(self):
        with self.client.post(
            f"{INVENTARIO_HOST}/inventory/transfers",
            json={
                "id_bodega_origen": 1,
                "id_bodega_destino": 2,
                "id_producto": random.randint(1, 10),
                "cantidad": 1,
                "id_usuario": 1,
                "clave_idempotencia": f"LT-TR-{uuid.uuid4().hex[:12]}",
            },
            name="PR07 POST /inventory/transfers",
            catch_response=True,
        ) as resp:
            if resp.status_code in (201, 409):
                resp.success()

    # --- ABASTECIMIENTO (PR-08 a PR-10) ---
    @task(3)
    def pr08_listar_proveedores(self):
        self.client.get(f"{ABASTECIMIENTO_HOST}/suppliers", name="PR08 GET /suppliers")

    @task(3)
    def pr09_listar_ordenes_compra(self):
        self.client.get(f"{ABASTECIMIENTO_HOST}/purchase-orders", name="PR09 GET /purchase-orders")

    @task(1)
    def pr10_crear_orden_compra(self):
        self.client.post(
            f"{ABASTECIMIENTO_HOST}/purchase-orders",
            json={
                "id_proveedor": random.choice([1, 2, 3]),
                "id_usuario": 1,
                "items": [{"id_producto": random.randint(1, 10), "cantidad_pedida": 5, "costo_unitario": 25000}],
            },
            name="PR10 POST /purchase-orders",
        )

    # --- VENTAS (PR-11 a PR-12) ---
    @task(4)
    def pr11_consultar_historial_ventas(self):
        self.client.get(f"{VENTAS_HOST}/sales", name="PR11 GET /sales")

    @task(2)
    def pr12_confirmar_venta_con_descuento_stock(self):
        with self.client.post(
            f"{VENTAS_HOST}/sales",
            json={
                "id_bodega": 1,
                "id_usuario": 3,
                "metodo_pago": random.choice(["EFECTIVO", "TRANSFERENCIA", "TARJETA"]),
                "clave_idempotencia": f"LT-VTA-{uuid.uuid4().hex[:12]}",
                "items": [{"id_producto": random.randint(1, 10), "cantidad": 1, "precio_unitario": 35000}],
            },
            name="PR12 POST /sales (Ventas -> Inventario)",
            catch_response=True,
        ) as resp:
            if resp.status_code in (201, 409):
                resp.success()

    # --- REPORTES Y ALERTAS (PR-13 a PR-15) ---
    @task(5)
    def pr13_consultar_dashboard_kpis(self):
        self.client.get(f"{REPORTES_HOST}/reports/dashboard", name="PR13 GET /reports/dashboard")

    @task(4)
    def pr14_consultar_alertas_stock(self):
        self.client.get(f"{REPORTES_HOST}/alerts", name="PR14 GET /alerts")

    @task(4)
    def pr15_consultar_reporte_inventario(self):
        self.client.get(f"{REPORTES_HOST}/reports/inventory", name="PR15 GET /reports/inventory")
