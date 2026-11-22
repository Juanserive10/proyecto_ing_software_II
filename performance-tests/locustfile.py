"""
Suite de 15 pruebas de rendimiento en Locust para Distribuidora Andina S.A.S. (RNF11).
Integrante: Juan Sebastián Rivera Valencia
Microservicios cubiertos: Inventario y Almacenes, Abastecimiento, Ventas y Reportes/Alertas.

TODAS las peticiones pasan por el API Gateway Laravel (RNF09):
  http://localhost:8000/api/{inventario|abastecimiento|ventas|reportes}/...

Escenarios (variable SCENARIO):
  normal   30 usuarios concurrentes, ramp-up 5 u/s, 60 s
  pico    100 usuarios concurrentes, ramp-up 15 u/s, 60 s
  estres  200 usuarios concurrentes, ramp-up 30 u/s, 60 s

Ejecución:
  ./performance-tests/run_juan.sh
  # o individualmente:
  SCENARIO=normal locust -f performance-tests/locustfile.py --headless --host http://localhost:8000 --csv=performance-tests/resultados_juan/normal --html=performance-tests/resultados_juan/normal.html
"""
import os
import random
import uuid
from locust import HttpUser, LoadTestShape, between, task

GATEWAY = "/api"


class InventarioVentasPerformanceUser(HttpUser):
    wait_time = between(0.3, 1.2)
    host = os.getenv("GATEWAY_URL", "http://localhost:8000")

    def on_start(self):
        self.token = None
        with self.client.post(
            f"{GATEWAY}/usuarios/auth/login",
            json={"correo": "admin@andina.com", "contrasena": "Admin123*"},
            name="SETUP login inicial",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                self.token = resp.json().get("access_token")
                resp.success()
            else:
                resp.failure(f"Login inicial falló: {resp.status_code}")

    def _auth(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _expect(self, resp, expected_statuses, check=None):
        if isinstance(expected_statuses, int):
            expected_statuses = (expected_statuses,)
        if resp.status_code not in expected_statuses:
            resp.failure(f"esperado {expected_statuses}, recibido {resp.status_code}")
            return
        if check is not None:
            try:
                ok = check(resp.json())
            except ValueError:
                ok = False
            if not ok:
                resp.failure("cuerpo de respuesta inválido")
                return
        resp.success()

    # --- INVENTARIO Y ALMACENES (PR-01 a PR-07) ---
    @task(6)
    def pr01_consultar_stock_general(self):
        with self.client.get(
            f"{GATEWAY}/inventario/inventory/stock",
            headers=self._auth(),
            name="PR01 GET /inventario/inventory/stock",
            catch_response=True,
        ) as resp:
            self._expect(resp, 200, lambda d: isinstance(d, list))

    @task(5)
    def pr02_consultar_stock_por_bodega(self):
        bodega = random.choice([1, 2])
        with self.client.get(
            f"{GATEWAY}/inventario/inventory/stock",
            params={"id_bodega": bodega},
            headers=self._auth(),
            name="PR02 GET /inventario/inventory/stock?id_bodega",
            catch_response=True,
        ) as resp:
            self._expect(resp, 200, lambda d: isinstance(d, list))

    @task(5)
    def pr03_consultar_stock_por_producto(self):
        prod = random.randint(1, 10)
        with self.client.get(
            f"{GATEWAY}/inventario/inventory/stock",
            params={"id_producto": prod},
            headers=self._auth(),
            name="PR03 GET /inventario/inventory/stock?id_producto",
            catch_response=True,
        ) as resp:
            self._expect(resp, 200, lambda d: isinstance(d, list))

    @task(4)
    def pr04_consultar_kardex(self):
        with self.client.get(
            f"{GATEWAY}/inventario/inventory/movements",
            params={"limit": 50},
            headers=self._auth(),
            name="PR04 GET /inventario/inventory/movements",
            catch_response=True,
        ) as resp:
            self._expect(resp, 200, lambda d: isinstance(d, list))

    @task(3)
    def pr05_listar_bodegas(self):
        with self.client.get(
            f"{GATEWAY}/inventario/warehouses",
            headers=self._auth(),
            name="PR05 GET /inventario/warehouses",
            catch_response=True,
        ) as resp:
            self._expect(resp, 200, lambda d: isinstance(d, list) and len(d) >= 2)

    @task(2)
    def pr06_registrar_entrada_stock(self):
        with self.client.post(
            f"{GATEWAY}/inventario/inventory/movements",
            json={
                "tipo": "ENTRADA",
                "id_producto": random.randint(1, 10),
                "cantidad": 5,
                "id_bodega_destino": random.choice([1, 2]),
                "id_usuario": 1,
                "tipo_referencia": "LOAD_TEST",
                "clave_idempotencia": f"LT-ENT-{uuid.uuid4().hex[:12]}",
            },
            headers=self._auth(),
            name="PR06 POST /inventario/inventory/movements (ENTRADA)",
            catch_response=True,
        ) as resp:
            self._expect(resp, 201, lambda d: "movimiento" in d)

    @task(1)
    def pr07_registrar_traslado_bodegas(self):
        with self.client.post(
            f"{GATEWAY}/inventario/inventory/transfers",
            json={
                "id_bodega_origen": 1,
                "id_bodega_destino": 2,
                "id_producto": random.randint(1, 10),
                "cantidad": 1,
                "id_usuario": 1,
                "clave_idempotencia": f"LT-TR-{uuid.uuid4().hex[:12]}",
            },
            headers=self._auth(),
            name="PR07 POST /inventario/inventory/transfers",
            catch_response=True,
        ) as resp:
            self._expect(resp, (201, 409))

    # --- ABASTECIMIENTO (PR-08 a PR-10) ---
    @task(3)
    def pr08_listar_proveedores(self):
        with self.client.get(
            f"{GATEWAY}/abastecimiento/suppliers",
            headers=self._auth(),
            name="PR08 GET /abastecimiento/suppliers",
            catch_response=True,
        ) as resp:
            self._expect(resp, 200, lambda d: isinstance(d, list))

    @task(3)
    def pr09_listar_ordenes_compra(self):
        with self.client.get(
            f"{GATEWAY}/abastecimiento/purchase-orders",
            headers=self._auth(),
            name="PR09 GET /abastecimiento/purchase-orders",
            catch_response=True,
        ) as resp:
            self._expect(resp, 200, lambda d: isinstance(d, list))

    @task(1)
    def pr10_crear_orden_compra(self):
        with self.client.post(
            f"{GATEWAY}/abastecimiento/purchase-orders",
            json={
                "id_proveedor": random.choice([1, 2, 3]),
                "id_usuario": 1,
                "items": [{"id_producto": random.randint(1, 10), "cantidad_pedida": 5, "costo_unitario": 25000}],
            },
            headers=self._auth(),
            name="PR10 POST /abastecimiento/purchase-orders",
            catch_response=True,
        ) as resp:
            self._expect(resp, 201, lambda d: "id_orden" in d)

    # --- VENTAS (PR-11 a PR-12) ---
    @task(4)
    def pr11_consultar_historial_ventas(self):
        with self.client.get(
            f"{GATEWAY}/ventas/sales",
            headers=self._auth(),
            name="PR11 GET /ventas/sales",
            catch_response=True,
        ) as resp:
            self._expect(resp, 200, lambda d: isinstance(d, list))

    @task(2)
    def pr12_confirmar_venta_con_descuento_stock(self):
        with self.client.post(
            f"{GATEWAY}/ventas/sales",
            json={
                "id_bodega": 1,
                "id_usuario": 3,
                "metodo_pago": random.choice(["EFECTIVO", "TRANSFERENCIA", "TARJETA"]),
                "clave_idempotencia": f"LT-VTA-{uuid.uuid4().hex[:12]}",
                "items": [{"id_producto": random.randint(1, 10), "cantidad": 1, "precio_unitario": 35000}],
            },
            headers=self._auth(),
            name="PR12 POST /ventas/sales (Ventas -> Inventario)",
            catch_response=True,
        ) as resp:
            self._expect(resp, (201, 409))

    # --- REPORTES Y ALERTAS (PR-13 a PR-15) ---
    @task(5)
    def pr13_consultar_dashboard_kpis(self):
        with self.client.get(
            f"{GATEWAY}/reportes/reports/dashboard",
            headers=self._auth(),
            name="PR13 GET /reportes/reports/dashboard",
            catch_response=True,
        ) as resp:
            self._expect(resp, 200, lambda d: "valor_total_inventario" in d)

    @task(4)
    def pr14_consultar_alertas_stock(self):
        with self.client.get(
            f"{GATEWAY}/reportes/alerts",
            headers=self._auth(),
            name="PR14 GET /reportes/alerts",
            catch_response=True,
        ) as resp:
            self._expect(resp, 200, lambda d: isinstance(d, list))

    @task(4)
    def pr15_consultar_reporte_inventario(self):
        with self.client.get(
            f"{GATEWAY}/reportes/reports/inventory",
            headers=self._auth(),
            name="PR15 GET /reportes/reports/inventory",
            catch_response=True,
        ) as resp:
            self._expect(resp, 200, lambda d: isinstance(d, list))


SCENARIOS = {
    "normal": [(60, 30, 5)],
    "pico": [(60, 100, 15)],
    "estres": [(60, 200, 30)],
}

_scenario = os.getenv("SCENARIO", "").lower()

if _scenario:
    if _scenario not in SCENARIOS:
        raise ValueError(f"SCENARIO debe ser uno de {list(SCENARIOS)}")

    class EscenarioJuanShape(LoadTestShape):
        stages = SCENARIOS[_scenario]

        def tick(self):
            run_time = self.get_run_time()
            for end, users, rate in self.stages:
                if run_time < end:
                    return users, rate
            return None
