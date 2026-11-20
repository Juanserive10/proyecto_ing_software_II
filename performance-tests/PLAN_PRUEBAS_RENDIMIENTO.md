# Plan de 15 Pruebas de Rendimiento — Distribuidora Andina S.A.S.

- **Responsable:** Juan Sebastián Rivera Valencia
- **Herramienta:** Locust (trabajada en clase)
- **Criterio de aceptación (RNF06):** Tiempo de respuesta P95 `< 2000 ms` en operaciones de consulta bajo carga concurrente y tasa de error `< 1%`.
- **Escenarios:**
  - **Carga normal:** 30 usuarios concurrentes, ramp-up 5 u/s, duración 60s.
  - **Carga pico:** 100 usuarios concurrentes, ramp-up 15 u/s, duración 60s.
  - **Estrés:** 200 usuarios concurrentes, ramp-up 30 u/s, duración 60s.

| ID | Microservicio | Endpoint | Método | Escenario | Métricas objetivo |
| :--- | :--- | :--- | :---: | :--- | :--- |
| PR01 | Inventario | `/inventory/stock` | GET | Normal / Pico / Estrés | P95 < 500ms, RPS, % error |
| PR02 | Inventario | `/inventory/stock?id_bodega=1` | GET | Normal / Pico / Estrés | P95 < 400ms, RPS, % error |
| PR03 | Inventario | `/inventory/stock?id_producto=1` | GET | Normal / Pico / Estrés | P95 < 400ms, RPS, % error |
| PR04 | Inventario | `/inventory/movements?limit=50` | GET | Normal / Pico / Estrés | P95 < 800ms, RPS, % error |
| PR05 | Inventario | `/warehouses` | GET | Normal / Pico | P95 < 300ms, RPS, % error |
| PR06 | Inventario | `/inventory/movements` (ENTRADA) | POST | Normal / Pico / Estrés | P95 < 1000ms, consistencia stock |
| PR07 | Inventario | `/inventory/transfers` | POST | Pico / Estrés | Atomicidad origen/destino, P95 < 1200ms |
| PR08 | Abastecimiento | `/suppliers` | GET | Normal / Pico | P95 < 500ms, RPS |
| PR09 | Abastecimiento | `/purchase-orders` | GET | Normal / Pico | P95 < 700ms, RPS |
| PR10 | Abastecimiento | `/purchase-orders` | POST | Normal / Pico | P95 < 1000ms, % error |
| PR11 | Ventas | `/sales` | GET | Normal / Pico / Estrés | P95 < 700ms, RPS |
| PR12 | Ventas | `/sales` (flujo `Ventas → Inventario`) | POST | Normal / Pico / Estrés | P95 < 1800ms, 0 ventas con stock negativo |
| PR13 | Reportes | `/reports/dashboard` | GET | Normal / Pico / Estrés | P95 < 600ms, RPS |
| PR14 | Reportes | `/alerts` | GET | Normal / Pico | P95 < 500ms, RPS |
| PR15 | Reportes | `/reports/inventory` | GET | Normal / Pico / Estrés | P95 < 600ms, RPS |
