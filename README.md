# Sistema de Gestión de Inventarios — Distribuidora Andina S.A.S.

Arquitectura de **6 microservicios independientes** con persistencia aislada por servicio (MySQL 8), mensajería asíncrona (RabbitMQ), contenerización Docker, orquestación Kubernetes, pruebas de rendimiento en Locust y frontend React con visualizador 3D de flujos.

## 1. Arquitectura de Microservicios

| Microservicio | Tecnología | Puerto | Base de Datos | Swagger / OpenAPI | Responsable (Reparto) |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `usuarios-service` | Flask + SQLAlchemy + JWT | `5001` | `db_usuarios` | `/apidocs` | Cristian |
| `catalogo-service` | Flask + SQLAlchemy + OpenPyXL | `5002` | `db_catalogo` | `/apidocs` | Cristian |
| `inventario-service` | FastAPI + SQLAlchemy + Pika | `5003` | `db_inventario` | `/docs` | Juan |
| `abastecimiento-service` | Flask + SQLAlchemy + Requests | `5004` | `db_abastecimiento` | `/apidocs` | Juan |
| `ventas-service` | FastAPI + SQLAlchemy + HTTPX + Pika | `5005` | `db_ventas` | `/docs` | Juan |
| `reportes-service` | FastAPI + SQLAlchemy + Pika Consumer | `5006` | `db_reportes` | `/docs` | Juan |
| `frontend` | React + Vite + Mapa 3D | `5173` | — | — | Equipo |
| `rabbitmq` | RabbitMQ 3.13 Management | `5672` / `15672` | — | UI `:15672` | Juan |

### Flujos integrados entre microservicios
1. **Venta POS (`Ventas → Catálogo + Inventario → RabbitMQ → Reportes`):**
   - `ventas-service` consulta el precio en `catalogo-service`, registra la venta `PENDIENTE`, solicita la `SALIDA` en `inventario-service` (con **compensación Saga** si algún ítem no tiene stock suficiente) y, al confirmarla, publica `sales.confirmed` en RabbitMQ.
2. **Recepción de Orden de Compra (`Abastecimiento → Inventario → RabbitMQ → Reportes`):**
   - `abastecimiento-service` crea la recepción `PENDIENTE`, solicita la `ENTRADA` en `inventario-service` y solo marca `CONFIRMADA` cuando el stock y el Kardex se actualizan.
3. **Alertas y Reportes (`Inventario / Ventas → RabbitMQ → Reportes`):**
   - `reportes-service` consume `inventory.stock.updated`, `inventory.movement.created` y `sales.confirmed` para mantener sus resúmenes propios y disparar alertas (`ALERTA`) cuando el saldo cae por debajo del `UMBRAL` configurado.

## 2. Ejecución rápida con Docker Compose (desarrollo local)

```bash
docker compose up --build
```
- **Frontend 3D:** `http://localhost:5173`
- **Credenciales demo:** `admin@andina.com` / `Admin123*` (también `bodega@andina.com` / `Bodega123*` y `ventas@andina.com` / `Ventas123*`)
- **RabbitMQ Management:** `http://localhost:15672` (`andina` / `andina_rabbit_2026`)

## 3. Despliegue en Kubernetes (`RNF04` y `RNF05`)

1. Construir imágenes locales (en Docker Desktop K8s o Minikube):
```bash
docker build -t andina/usuarios-service:1.0 ./services/usuarios-service
docker build -t andina/catalogo-service:1.0 ./services/catalogo-service
docker build -t andina/inventario-service:1.0 ./services/inventario-service
docker build -t andina/abastecimiento-service:1.0 ./services/abastecimiento-service
docker build -t andina/ventas-service:1.0 ./services/ventas-service
docker build -t andina/reportes-service:1.0 ./services/reportes-service
docker build -t andina/frontend:1.0 ./frontend
```
2. Aplicar manifiestos:
```bash
kubectl apply -f k8s/
kubectl get pods,svc,hpa -n andina-inventory
```

## 4. Pruebas End-to-End y Pruebas de Rendimiento (Locust)

- **Validación funcional E2E de los 6 microservicios:**
```bash
python scripts/test_e2e_flows.py
```
- **15 pruebas de rendimiento (`RNF11`):** ver [performance-tests/PLAN_PRUEBAS_RENDIMIENTO.md](performance-tests/PLAN_PRUEBAS_RENDIMIENTO.md)
```bash
locust -f performance-tests/locustfile.py --headless -u 30 -r 5 -t 60s --csv=performance-tests/normal
locust -f performance-tests/locustfile.py --headless -u 100 -r 15 -t 60s --csv=performance-tests/pico
locust -f performance-tests/locustfile.py --headless -u 200 -r 30 -t 60s --csv=performance-tests/estres
```

## 5. Integración con el API Gateway de Cristian
Cuando el API Gateway en Laravel esté listo:
1. Enrutar `/api/usuarios/*`, `/api/catalogo/*`, `/api/inventario/*`, `/api/abastecimiento/*`, `/api/ventas/*` y `/api/reportes/*` hacia los servicios internos (`ClusterIP` en Kubernetes).
2. Validar JWT con `JWT_SECRET=andina-jwt-super-secret-2026` o mediante `POST http://usuarios-service:5001/auth/verify`.
3. En `frontend/.env`, definir `VITE_GATEWAY_URL=http://localhost:8000` (o la URL del Ingress) para que todo el tráfico del frontend pase exclusivamente por el Gateway.
