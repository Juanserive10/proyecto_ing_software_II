# Plan de 15 Pruebas de Rendimiento — Distribuidora Andina S.A.S.

- **Responsable:** Juan Sebastián Rivera Valencia
- **Herramienta:** Locust (trabajada en clase), archivo [`locustfile.py`](locustfile.py)
- **Punto de entrada:** Todas las peticiones se enrutan a través del API Gateway Laravel (`http://localhost:8000/api/...`) con token JWT (`RNF09`).
- **Criterio de aceptación (RNF06):** Tiempo de respuesta P95 `< 2000 ms` en operaciones de consulta bajo carga concurrente y tasa de error `< 1%`.
- **Escenarios:**
  - **Carga normal:** 30 usuarios concurrentes, ramp-up 5 u/s, duración 60s.
  - **Carga pico:** 100 usuarios concurrentes, ramp-up 15 u/s, duración 60s.
  - **Estrés:** 200 usuarios concurrentes, ramp-up 30 u/s, duración 60s.

| ID | Microservicio | Endpoint (vía Gateway) | Método | Escenario | Métricas objetivo |
| :--- | :--- | :--- | :---: | :--- | :--- |
| PR01 | Inventario | `/api/inventario/inventory/stock` | GET | Normal / Pico / Estrés | P95 < 500ms, RPS, % error |
| PR02 | Inventario | `/api/inventario/inventory/stock?id_bodega=1` | GET | Normal / Pico / Estrés | P95 < 400ms, RPS, % error |
| PR03 | Inventario | `/api/inventario/inventory/stock?id_producto=1` | GET | Normal / Pico / Estrés | P95 < 400ms, RPS, % error |
| PR04 | Inventario | `/api/inventario/inventory/movements?limit=50` | GET | Normal / Pico / Estrés | P95 < 800ms, RPS, % error |
| PR05 | Inventario | `/api/inventario/warehouses` | GET | Normal / Pico / Estrés | P95 < 300ms, RPS, % error |
| PR06 | Inventario | `/api/inventario/inventory/movements` (ENTRADA) | POST | Normal / Pico / Estrés | P95 < 1000ms, consistencia stock |
| PR07 | Inventario | `/api/inventario/inventory/transfers` | POST | Normal / Pico / Estrés | Atomicidad origen/destino, P95 < 1200ms |
| PR08 | Abastecimiento | `/api/abastecimiento/suppliers` | GET | Normal / Pico / Estrés | P95 < 500ms, RPS |
| PR09 | Abastecimiento | `/api/abastecimiento/purchase-orders` | GET | Normal / Pico / Estrés | P95 < 700ms, RPS |
| PR10 | Abastecimiento | `/api/abastecimiento/purchase-orders` | POST | Normal / Pico / Estrés | P95 < 1000ms, % error |
| PR11 | Ventas | `/api/ventas/sales` | GET | Normal / Pico / Estrés | P95 < 700ms, RPS |
| PR12 | Ventas | `/api/ventas/sales` (flujo `Ventas → Inventario`) | POST | Normal / Pico / Estrés | P95 < 1800ms, 0 ventas con stock negativo |
| PR13 | Reportes | `/api/reportes/reports/dashboard` | GET | Normal / Pico / Estrés | P95 < 600ms, RPS |
| PR14 | Reportes | `/api/reportes/alerts` | GET | Normal / Pico / Estrés | P95 < 500ms, RPS |
| PR15 | Reportes | `/api/reportes/reports/inventory` | GET | Normal / Pico / Estrés | P95 < 600ms, RPS |

## Ejecución y resultados

```bash
./performance-tests/run_juan.sh
python3 performance-tests/resumen_juan.py
```

Resultados documentados en [`RESULTADOS_JUAN.md`](RESULTADOS_JUAN.md) y evidencias CSV/HTML en `performance-tests/resultados_juan/`.

## Análisis de resultados (22-nov-2026)

| Escenario | Peticiones | Errores | P50 | P95 | req/s | ¿Cumple RNF06? |
| :--- | ---: | ---: | ---: | ---: | ---: | :---: |
| Carga normal (30 u) | 2 277 | 0 % | 15 ms | 66 ms | 37.90 | ✅ |
| Carga pico (100 u) | 7 459 | 0 % | 21 ms | 110 ms | 124.10 | ✅ |
| Estrés (200 u) | 9 761 | 0 % | 410 ms | 970 ms | 162.31 | ✅ |

**Hallazgos**

1. **Cero errores en las 19 497 peticiones totales** ejecutadas a través del API Gateway (`normal`, `pico` y `estres`), cumpliendo `RNF06` (`P95 < 2000 ms` y error `< 1%`) en las **15 pruebas (`PR01`–`PR15`)** de todos los escenarios.
2. **Detección y resolución de cuello de botella N+1:** en la primera corrida bajo carga, `GET /ventas/sales` (`PR11`) y `GET /abastecimiento/purchase-orders` (`PR09`) hacían carga perezosa (*lazy loading*) por cada detalle sin límite de paginación, saturando los workers del Gateway. Al agregar `selectinload`, `limit=100` por defecto, pool HTTP persistente y 2 workers en `ventas-service`, el P95 en carga pico bajó de **2 100 ms a 110 ms** y en estrés de **8 500 ms a 970 ms**.
3. **Integridad transaccional bajo concurrencia:** los bloqueos de fila (`SELECT ... FOR UPDATE`) en `inventario-service` y la compensación Saga en `ventas-service` mantuvieron consistencia total de existencias (`0` ventas con stock negativo).
