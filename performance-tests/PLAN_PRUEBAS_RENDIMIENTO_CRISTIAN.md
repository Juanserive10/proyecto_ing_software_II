# Plan de 15 Pruebas de Rendimiento — Cristian Bermúdez (RNF11)

- **Herramienta:** Locust 2.37 (imagen oficial `locustio/locust`), archivo [`locustfile_cristian.py`](locustfile_cristian.py).
- **Punto de entrada:** **todas** las peticiones van al API Gateway Laravel (`http://localhost:8000/api/...`). Ninguna prueba llama directo a `:5001`/`:5002`; además, esos puertos ya no se publican en el host.
- **Microservicios bajo prueba:** `usuarios-service` (PC01–PC08) y `catalogo-service` (PC09–PC15).
- **Criterio de aceptación (RNF06):** P95 `< 2000 ms` en consultas y tasa de error `< 1 %` en carga normal y pico.
- **Métricas:** tiempo de respuesta (media, mediana, P95, P99, máx.), throughput (req/s) y tasa de error (%). Cada prueba valida el código HTTP esperado y, cuando aplica, el contenido de la respuesta (`catch_response`).

## Escenarios de carga

| Escenario | Tipo de prueba | Perfil (`SCENARIO=`) | Objetivo |
| :--- | :--- | :--- | :--- |
| `normal` | Carga | 30 usuarios, 5 u/s, 60 s | Línea base de operación diaria |
| `pico` | Carga pico | 100 usuarios, 15 u/s, 60 s | Hora punta de ventas |
| `estres` | Estrés por escalones | 50 → 100 → 200 → 300 usuarios, 120 s | Encontrar el punto de saturación |
| `spike` | Picos repentinos | 20 → 250 → 20 usuarios, 75 s | Reacción y recuperación ante un pico brusco |
| `resistencia` | Resistencia (soak corto) | 40 usuarios sostenidos, 180 s | Estabilidad: sin degradación ni fugas |

Cada escenario ejecuta las 15 pruebas a la vez, con pesos (`@task(n)`) que reproducen el uso real: más consultas al catálogo que registros.

## Las 15 pruebas

| ID | Servicio | Endpoint (vía Gateway) | Método | Qué valida | Objetivo P95 |
| :--- | :--- | :--- | :---: | :--- | :--- |
| PC01 | Usuarios | `/api/usuarios/auth/login` | POST | Login válido, devuelve `access_token` | < 1000 ms |
| PC02 | Usuarios | `/api/usuarios/auth/login` (clave errónea) | POST | Responde **401** de forma estable bajo carga | < 1000 ms |
| PC03 | Usuarios | `/api/usuarios/auth/register` | POST | Alta de usuario con correo único (**201**) | < 1500 ms |
| PC04 | Usuarios | `/api/usuarios/auth/verify` | POST | Token válido (`valid: true`) | < 300 ms |
| PC05 | Usuarios | `/api/usuarios/users` | GET | Listado de usuarios no vacío | < 500 ms |
| PC06 | Usuarios | `/api/usuarios/auth/me` | GET | Perfil del usuario autenticado | < 300 ms |
| PC07 | Usuarios | `/api/usuarios/roles` | GET | Los 3 roles del sistema | < 300 ms |
| PC08 | Gateway / Usuarios | `/api/usuarios/users` **sin JWT** | GET | El Gateway corta con **401** sin llegar al servicio | < 100 ms |
| PC09 | Catálogo | `/api/catalogo/products` | GET | Listado completo de productos | < 500 ms |
| PC10 | Catálogo | `/api/catalogo/products?q=` | GET | Búsqueda por texto (nombre/código/descr.) | < 500 ms |
| PC11 | Catálogo | `/api/catalogo/products?id_categoria=` | GET | Filtro por categoría | < 500 ms |
| PC12 | Catálogo | `/api/catalogo/products?q=&id_categoria=&activo=` | GET | Filtro combinado | < 500 ms |
| PC13 | Catálogo | `/api/catalogo/categories` | GET | Listado de categorías | < 300 ms |
| PC14 | Catálogo | `/api/catalogo/products/{id}` | GET | Detalle coincide con el id pedido | < 300 ms |
| PC15 | Catálogo | Flujo POS: categorías → filtro → detalle | GET ×3 | Recorrido completo del vendedor | < 500 ms por paso |

Las filas `SETUP ...` del reporte (login inicial y carga de ids de cada usuario virtual) son preparación y no forman parte de las 15 pruebas.

## Ejecución

```bash
docker compose up -d --build                      # stack completo con el Gateway
./performance-tests/run_cristian.sh               # los 5 escenarios
./performance-tests/run_cristian.sh normal pico   # o solo algunos
python3 performance-tests/resumen_cristian.py     # regenera RESULTADOS_CRISTIAN.md
```

La evidencia de cada escenario queda en `performance-tests/resultados_cristian/`: `<escenario>_stats.csv`, `_stats_history.csv`, `_failures.csv`, `_exceptions.csv`, el reporte `.html` interactivo y el log `.log` de consola.

## Análisis de resultados preliminares (21-nov-2026)

Tablas completas en [`RESULTADOS_CRISTIAN.md`](RESULTADOS_CRISTIAN.md). Entorno: Docker Compose en un portátil de 16 hilos, con Locust en la misma máquina.

| Escenario | Peticiones | Errores | P50 | P95 | req/s | ¿Cumple RNF06? |
| :--- | ---: | ---: | ---: | ---: | ---: | :---: |
| Carga normal (30 u) | 1 903 | 0 % | 16 ms | 110 ms | 31.7 | ✅ |
| Carga pico (100 u) | 6 184 | 0 % | 15 ms | 190 ms | 102.8 | ✅ |
| Estrés (hasta 300 u) | 13 242 | 0 % | 300 ms | 1 700 ms | 109.9 | ✅ (en el límite) |
| Spike (20→250→20 u) | 4 228 | 0 % | 550 ms | 4 900 ms* | 56.2 | ⚠️ durante el pico |
| Resistencia (40 u, 3 min) | 7 472 | 0 % | 16 ms | 110 ms | 41.4 | ✅ |

\* El P95 agregado del spike incluye las filas `SETUP login inicial` de los 230 usuarios que entran casi a la vez. Por prueba, el P95 se mantiene entre 830 y 1 700 ms.

**Hallazgos**

1. **Ninguna petición falló** en los 5 escenarios (≈33 000 peticiones). El Gateway nunca devolvió 5xx y siempre rechazó con 401 las peticiones sin JWT (PC08).
2. **El costo del Gateway es bajo.** Con carga normal, PC08 (que el Gateway responde sin llamar al microservicio) tarda unos 8 ms. Las consultas de catálogo que sí pasan al servicio están entre 15 y 20 ms, así que el salto adicional que añade el Gateway es de pocos milisegundos.
3. **El cuello de botella es `usuarios-service` en login y registro.** PC01–PC03 tienen una mediana de unos 110 ms incluso sin carga, porque el hash de contraseñas es costoso por diseño (RNF07). El servicio corre con solo 2 workers síncronos de gunicorn. En estrés, las pruebas de usuarios llegan a un P95 de unos 1 800 ms, frente a unos 1 200 ms en las de catálogo.
4. **Punto de saturación cerca de 150 req/s** (unos 200 usuarios concurrentes). A partir de ahí el throughput deja de crecer y lo que aumenta es la latencia, sin errores. La cola se forma en los workers de php-fpm del Gateway (32) que esperan a usuarios-service: por eso hasta PC08 sube a una mediana de 150 ms en estrés.
5. **Recuperación tras el pico.** Cuando el spike baja de 250 a 20 usuarios, el throughput vuelve a unos 20 req/s y la latencia instantánea se normaliza. El P95 acumulado del CSV solo baja despacio porque arrastra los valores del pico.
6. **Resistencia estable.** Durante 3 minutos el P95 se mantuvo en unos 110 ms y el throughput en unos 41 req/s, sin tendencia al alza: no se observa degradación ni fugas.

**Optimizaciones propuestas (para validar en la Entrega 4)**

- Subir los workers de gunicorn de `usuarios-service` (por ejemplo `--workers 4 --threads 4`) o escalarlo con el HPA de Kubernetes, ya que es el servicio que más carga recibe en login y registro.
- En modo `JWT_VERIFY_MODE=local` el Gateway valida el JWT sin llamar a `/auth/verify`, así que no le añade carga a usuarios-service. Conviene mantener ese modo en producción.
- Servir el Gateway con un runtime persistente (Laravel Octane / FrankenPHP) o aumentar `pm.max_children` para que más peticiones se atiendan en paralelo mientras esperan a los servicios.
