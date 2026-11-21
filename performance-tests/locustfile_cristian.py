"""
Suite de 15 pruebas de rendimiento (RNF11) — Distribuidora Andina S.A.S.
Integrante: Cristian Bermúdez
Microservicios cubiertos: usuarios-service y catalogo-service.

TODAS las peticiones pasan por el API Gateway Laravel (RNF09):
    http://localhost:8000/api/usuarios/...   http://localhost:8000/api/catalogo/...
Nunca se llama directamente a los puertos :5001 / :5002.

Escenarios (seleccionados con la variable SCENARIO, ver EscenarioShape):
    normal       Carga normal    30 usuarios, ramp-up 5 u/s, 60 s
    pico         Carga pico     100 usuarios, ramp-up 15 u/s, 60 s
    estres       Estrés por escalones 50 -> 100 -> 200 -> 300 usuarios, 120 s
    spike        Picos repentinos 20 -> 250 -> 20 usuarios, 75 s
    resistencia  Resistencia (soak corto) 40 usuarios sostenidos, 180 s

Ejecución (Locust en Docker, sin instalar nada en el host):
    docker run --rm --network host -e SCENARIO=normal \
        -v "$PWD/performance-tests:/mnt/locust" -w /mnt/locust locustio/locust:2.37.10 \
        -f locustfile_cristian.py --headless --host http://localhost:8000 \
        --csv resultados_cristian/normal --html resultados_cristian/normal.html
O bien: ./performance-tests/run_cristian.sh
"""
import os
import random
import uuid

from locust import HttpUser, LoadTestShape, between, task

GATEWAY = "/api"
DEMO_USERS = [
    ("admin@andina.com", "Admin123*"),
    ("bodega@andina.com", "Bodega123*"),
    ("ventas@andina.com", "Ventas123*"),
]
SEARCH_TERMS = ["arroz", "aceite", "café", "azúcar", "leche", "ARR", "PROD", "gaseosa", "pan", "a"]


class UsuariosCatalogoUser(HttpUser):
    """Usuario autenticado que navega identidad y catálogo a través del Gateway."""

    wait_time = between(0.5, 1.5)
    host = os.getenv("GATEWAY_URL", "http://localhost:8000")

    def on_start(self):
        self.token = None
        self.product_ids = [1]
        self.category_ids = [1]
        correo, clave = random.choice(DEMO_USERS)
        with self.client.post(
            f"{GATEWAY}/usuarios/auth/login",
            json={"correo": correo, "contrasena": clave},
            name="SETUP login inicial",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                self.token = resp.json()["access_token"]
            else:
                resp.failure(f"login inicial falló: {resp.status_code}")
        self._load_catalog_ids()

    def _auth(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _load_catalog_ids(self):
        resp = self.client.get(f"{GATEWAY}/catalogo/products", headers=self._auth(), name="SETUP carga ids catálogo")
        if resp.ok and resp.json():
            self.product_ids = [p["id_producto"] for p in resp.json()]
        resp = self.client.get(f"{GATEWAY}/catalogo/categories", headers=self._auth(), name="SETUP carga ids catálogo")
        if resp.ok and resp.json():
            self.category_ids = [c["id_categoria"] for c in resp.json()]

    def _expect(self, resp, status, check=None):
        """Marca éxito/fallo según el código esperado y una validación opcional del cuerpo."""
        if resp.status_code != status:
            resp.failure(f"esperado {status}, recibido {resp.status_code}")
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

    # ======================= USUARIOS-SERVICE (PC01 - PC08) =======================

    @task(3)
    def pc01_login_valido(self):
        correo, clave = random.choice(DEMO_USERS)
        with self.client.post(
            f"{GATEWAY}/usuarios/auth/login",
            json={"correo": correo, "contrasena": clave},
            name="PC01 POST /usuarios/auth/login",
            catch_response=True,
        ) as resp:
            self._expect(resp, 200, lambda d: bool(d.get("access_token")))
            if resp.status_code == 200:
                self.token = resp.json()["access_token"]

    @task(2)
    def pc02_login_credenciales_invalidas(self):
        with self.client.post(
            f"{GATEWAY}/usuarios/auth/login",
            json={"correo": "admin@andina.com", "contrasena": "clave-incorrecta"},
            name="PC02 POST /usuarios/auth/login (inválido -> 401)",
            catch_response=True,
        ) as resp:
            self._expect(resp, 401)

    @task(1)
    def pc03_registro_usuario(self):
        sufijo = uuid.uuid4().hex[:12]
        with self.client.post(
            f"{GATEWAY}/usuarios/auth/register",
            json={"correo": f"lt_{sufijo}@andina.com", "nombre": f"Load Test {sufijo}", "contrasena": "LoadTest123*"},
            name="PC03 POST /usuarios/auth/register",
            catch_response=True,
        ) as resp:
            self._expect(resp, 201, lambda d: bool(d.get("usuario", {}).get("id_usuario")))

    @task(4)
    def pc04_verificar_token(self):
        with self.client.post(
            f"{GATEWAY}/usuarios/auth/verify",
            headers=self._auth(),
            name="PC04 POST /usuarios/auth/verify",
            catch_response=True,
        ) as resp:
            self._expect(resp, 200, lambda d: d.get("valid") is True)

    @task(4)
    def pc05_listar_usuarios(self):
        with self.client.get(
            f"{GATEWAY}/usuarios/users", headers=self._auth(), name="PC05 GET /usuarios/users", catch_response=True
        ) as resp:
            self._expect(resp, 200, lambda d: isinstance(d, list) and len(d) > 0)

    @task(3)
    def pc06_perfil_autenticado(self):
        with self.client.get(
            f"{GATEWAY}/usuarios/auth/me", headers=self._auth(), name="PC06 GET /usuarios/auth/me", catch_response=True
        ) as resp:
            self._expect(resp, 200, lambda d: "correo" in d)

    @task(2)
    def pc07_listar_roles(self):
        with self.client.get(
            f"{GATEWAY}/usuarios/roles", headers=self._auth(), name="PC07 GET /usuarios/roles", catch_response=True
        ) as resp:
            self._expect(resp, 200, lambda d: len(d) >= 3)

    @task(2)
    def pc08_rechazo_sin_token(self):
        """El Gateway debe rechazar con 401 rutas protegidas sin JWT, sin tocar el microservicio."""
        with self.client.get(
            f"{GATEWAY}/usuarios/users", name="PC08 GET /usuarios/users sin JWT (-> 401)", catch_response=True
        ) as resp:
            self._expect(resp, 401)

    # ======================= CATALOGO-SERVICE (PC09 - PC15) =======================

    @task(6)
    def pc09_listar_productos(self):
        with self.client.get(
            f"{GATEWAY}/catalogo/products", headers=self._auth(), name="PC09 GET /catalogo/products", catch_response=True
        ) as resp:
            self._expect(resp, 200, lambda d: isinstance(d, list))

    @task(5)
    def pc10_buscar_productos_texto(self):
        with self.client.get(
            f"{GATEWAY}/catalogo/products",
            params={"q": random.choice(SEARCH_TERMS)},
            headers=self._auth(),
            name="PC10 GET /catalogo/products?q=",
            catch_response=True,
        ) as resp:
            self._expect(resp, 200, lambda d: isinstance(d, list))

    @task(4)
    def pc11_filtrar_por_categoria(self):
        with self.client.get(
            f"{GATEWAY}/catalogo/products",
            params={"id_categoria": random.choice(self.category_ids)},
            headers=self._auth(),
            name="PC11 GET /catalogo/products?id_categoria=",
            catch_response=True,
        ) as resp:
            self._expect(resp, 200, lambda d: isinstance(d, list))

    @task(3)
    def pc12_filtro_combinado(self):
        with self.client.get(
            f"{GATEWAY}/catalogo/products",
            params={
                "q": random.choice(SEARCH_TERMS),
                "id_categoria": random.choice(self.category_ids),
                "activo": "true",
            },
            headers=self._auth(),
            name="PC12 GET /catalogo/products?q=&id_categoria=&activo=",
            catch_response=True,
        ) as resp:
            self._expect(resp, 200, lambda d: isinstance(d, list))

    @task(4)
    def pc13_listar_categorias(self):
        with self.client.get(
            f"{GATEWAY}/catalogo/categories", headers=self._auth(), name="PC13 GET /catalogo/categories", catch_response=True
        ) as resp:
            self._expect(resp, 200, lambda d: isinstance(d, list) and len(d) > 0)

    @task(4)
    def pc14_detalle_producto(self):
        pid = random.choice(self.product_ids)
        with self.client.get(
            f"{GATEWAY}/catalogo/products/{pid}",
            headers=self._auth(),
            name="PC14 GET /catalogo/products/{id}",
            catch_response=True,
        ) as resp:
            self._expect(resp, 200, lambda d: d.get("id_producto") == pid)

    @task(2)
    def pc15_flujo_busqueda_pos(self):
        """Flujo de un vendedor en POS: categorías -> productos de la categoría -> detalle."""
        name = "PC15 Flujo POS categorías->filtro->detalle"
        with self.client.get(f"{GATEWAY}/catalogo/categories", headers=self._auth(), name=name, catch_response=True) as r1:
            self._expect(r1, 200)
            if r1.status_code != 200:
                return
        cat = random.choice([c["id_categoria"] for c in r1.json()] or self.category_ids)
        with self.client.get(
            f"{GATEWAY}/catalogo/products", params={"id_categoria": cat}, headers=self._auth(), name=name, catch_response=True
        ) as r2:
            self._expect(r2, 200)
            if r2.status_code != 200:
                return
        productos = r2.json() or [{"id_producto": random.choice(self.product_ids)}]
        pid = random.choice(productos)["id_producto"]
        with self.client.get(f"{GATEWAY}/catalogo/products/{pid}", headers=self._auth(), name=name, catch_response=True) as r3:
            self._expect(r3, 200)


# ============================ ESCENARIOS DE CARGA ============================
# Cada etapa: (segundo en que termina, usuarios, tasa de spawn por segundo)
SCENARIOS = {
    "normal": [(60, 30, 5)],
    "pico": [(60, 100, 15)],
    "estres": [(30, 50, 10), (60, 100, 10), (90, 200, 20), (120, 300, 30)],
    "spike": [(20, 20, 5), (45, 250, 100), (75, 20, 100)],
    "resistencia": [(180, 40, 5)],
}

_scenario = os.getenv("SCENARIO", "").lower()

if _scenario:
    if _scenario not in SCENARIOS:
        raise ValueError(f"SCENARIO debe ser uno de {list(SCENARIOS)}")

    class EscenarioShape(LoadTestShape):
        stages = SCENARIOS[_scenario]

        def tick(self):
            run_time = self.get_run_time()
            for end, users, rate in self.stages:
                if run_time < end:
                    return users, rate
            return None
