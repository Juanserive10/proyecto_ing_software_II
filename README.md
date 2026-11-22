# Sistema de Gestión de Inventarios — Distribuidora Andina S.A.S.

Arquitectura de **6 microservicios independientes** con persistencia aislada por servicio (MySQL 8), mensajería asíncrona (RabbitMQ), **API Gateway propio en Laravel 13**, control de acceso JWT/RBAC, contenerización con Docker Compose, pruebas end-to-end, pruebas de rendimiento en Locust y frontend web en React.

> **Alcance Entrega 3:** Despliegue completo contenerizado mediante Docker Compose y acceso centralizado por API Gateway. La orquestación con Kubernetes (`RNF04` / `RNF05`) queda fuera de esta entrega.

## 1. Arquitectura de Microservicios

| Componente | Tecnología | Puerto | Base de Datos | Swagger / OpenAPI | Responsable (Reparto) |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `api-gateway` | Laravel 13 (nginx + php-fpm) | `8000` | — | `/api/health` | Cristian |
| `usuarios-service` | Flask + SQLAlchemy + JWT | `5001` *(interno)* | `db_usuarios` | `/apidocs` | Cristian |
| `catalogo-service` | Flask + SQLAlchemy + OpenPyXL | `5002` *(interno)* | `db_catalogo` | `/apidocs` | Cristian |
| `inventario-service` | FastAPI + SQLAlchemy + Pika | `5003` *(interno)* | `db_inventario` | `/docs` | Juan |
| `abastecimiento-service` | Flask + SQLAlchemy + Requests | `5004` *(interno)* | `db_abastecimiento` | `/apidocs` | Juan |
| `ventas-service` | FastAPI + SQLAlchemy + HTTPX + Pika | `5005` *(interno)* | `db_ventas` | `/docs` | Juan |
| `reportes-service` | FastAPI + SQLAlchemy + Pika Consumer | `5006` *(interno)* | `db_reportes` | `/docs` | Juan |
| `frontend` | React + Vite + Nginx | `5173` | — | — | Equipo |
| `rabbitmq` | RabbitMQ 3.13 Management | `5672` / `15672` | — | UI `:15672` | Juan |

### Flujos integrados entre microservicios
1. **Venta POS (`Gateway → Ventas → Catálogo + Inventario → RabbitMQ → Reportes`):**
   - `ventas-service` consulta el precio en `catalogo-service`, registra la venta `PENDIENTE`, solicita la `SALIDA` en `inventario-service` (con bloqueo transaccional por fila y **compensación Saga** si algún ítem no tiene stock suficiente) y, al confirmarla, publica `sales.confirmed` en RabbitMQ.
2. **Recepción de Orden de Compra (`Gateway → Abastecimiento → Inventario → RabbitMQ → Reportes`):**
   - `abastecimiento-service` crea la recepción `PENDIENTE`, solicita la `ENTRADA` en `inventario-service` y solo marca `CONFIRMADA` cuando el stock y el Kardex se actualizan.
3. **Alertas y Reportes (`Inventario / Ventas → RabbitMQ → Reportes`):**
   - `reportes-service` consume `inventory.stock.updated`, `inventory.movement.created` y `sales.confirmed` para mantener sus resúmenes propios y disparar alertas (`ALERTA`) cuando el saldo cae por debajo del `UMBRAL` configurado.

## 2. Ejecución rápida con Docker Compose

```bash
docker compose up --build
```
- **Frontend Web:** `http://localhost:5173` (todas sus peticiones van al API Gateway)
- **API Gateway:** `http://localhost:8000/api/{usuarios|catalogo|inventario|abastecimiento|ventas|reportes}/...`
- Los puertos `5001`–`5006` **no** se publican en el host: el único punto de entrada HTTP es el API Gateway (`RNF09`).
- **Depuración directa y acceso a Swagger (`/docs` y `/apidocs`):**
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.debug.yml up --build
  ```
- **Credenciales demo (RBAC `RF07`):**
  - `admin@andina.com` / `Admin123*` (`ADMINISTRADOR`: acceso completo)
  - `bodega@andina.com` / `Bodega123*` (`OPERADOR_BODEGA`: inventario, kardex, devoluciones, bodegas, recepción de OC, alertas)
  - `ventas@andina.com` / `Ventas123*` (`VENDEDOR`: punto de venta POS e historial, consulta de catálogo/stock/reportes)
- **RabbitMQ Management:** `http://localhost:15672` (`andina` / `andina_rabbit_2026`)

## 3. API Gateway propio (Laravel 13, `RNF09`)

Código en [`api-gateway/`](api-gateway). Toda petición externa entra por `http://localhost:8000/api/{servicio}/{ruta}` y se reenvía a `http://{servicio}-service:{puerto}/{ruta}` dentro de la red interna de Docker.

| Prefijo | Servicio interno |
| :--- | :--- |
| `/api/usuarios/*` | `usuarios-service:5001` |
| `/api/catalogo/*` | `catalogo-service:5002` |
| `/api/inventario/*` | `inventario-service:5003` |
| `/api/abastecimiento/*` | `abastecimiento-service:5004` |
| `/api/ventas/*` | `ventas-service:5005` |
| `/api/reportes/*` | `reportes-service:5006` |

- **JWT y RBAC:** todas las rutas exigen `Authorization: Bearer <token>`, salvo `*/health` y las rutas públicas de autenticación (`usuarios/auth/login`, `register`, `verify`, `forgot-password`, `password/recovery`, `reset-password`). El middleware `ValidateJwt` valida firma HS256/expiración (`JWT_VERIFY_MODE=local` o `remote`), verifica tokens revocados en caché y aplica reglas RBAC por rol en operaciones de escritura.
- **CORS:** gestionado por el Gateway (`CORS_ALLOWED_ORIGINS`, por defecto `http://localhost:5173,http://127.0.0.1:5173`).
- **Observabilidad (`RNF10`):** el Gateway genera un log JSON por petición (`docker logs andina-api-gateway`) con `X-Request-Id`, `X-Upstream-Service` y `X-Gateway-Time-Ms`, y propaga `X-Request-Id` hacia los microservicios Python.
- **Pruebas del Gateway:**
  ```bash
  docker run --rm -v "$PWD/api-gateway:/app" -w /app composer:2 sh -c "composer install -q && php artisan test"
  ```

## 4. Pruebas End-to-End y Pruebas de Rendimiento (Locust)

- **Validación funcional E2E de los 6 microservicios (vía API Gateway):**
  ```bash
  python3 scripts/test_e2e_flows.py
  ```
- **15 pruebas de rendimiento de Juan (Inventario, Abastecimiento, Ventas y Reportes vía Gateway, `RNF11`):** ver [performance-tests/PLAN_PRUEBAS_RENDIMIENTO.md](performance-tests/PLAN_PRUEBAS_RENDIMIENTO.md) y [performance-tests/RESULTADOS_JUAN.md](performance-tests/RESULTADOS_JUAN.md)
  ```bash
  ./performance-tests/run_juan.sh            # normal, pico, estres
  python3 performance-tests/resumen_juan.py  # regenera RESULTADOS_JUAN.md
  ```
- **15 pruebas de rendimiento de Cristian (Usuarios y Catálogo vía Gateway, `RNF11`):** ver [performance-tests/PLAN_PRUEBAS_RENDIMIENTO_CRISTIAN.md](performance-tests/PLAN_PRUEBAS_RENDIMIENTO_CRISTIAN.md) y [performance-tests/RESULTADOS_CRISTIAN.md](performance-tests/RESULTADOS_CRISTIAN.md)
  ```bash
  ./performance-tests/run_cristian.sh            # normal, pico, estres, spike, resistencia
  python3 performance-tests/resumen_cristian.py  # regenera RESULTADOS_CRISTIAN.md
  ```
