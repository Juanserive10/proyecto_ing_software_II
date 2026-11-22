# Resultados de las 15 pruebas de rendimiento — Juan Sebastián Rivera

_Generado con `resumen_juan.py` el 2026-11-22 18:03. Todas las peticiones pasaron por el API Gateway (`http://localhost:8000/api`)._

Criterio: ✅ si P95 < 2000 ms y error < 1 % (RNF06). Tiempos en ms.

## Resumen por escenario

| Escenario | Peticiones | Errores | Media | P50 | P95 | P99 | Máx | req/s |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Carga normal — 30 usuarios, ramp-up 5 u/s, 60 s | 2277 | 0 (0.00 %) | 21 | 15 | 66 | 120 | 241 | 37.90 |
| Carga pico — 100 usuarios, ramp-up 15 u/s, 60 s | 7459 | 0 (0.00 %) | 37 | 21 | 110 | 340 | 733 | 124.10 |
| Estrés — 200 usuarios, ramp-up 30 u/s, 60 s | 9761 | 0 (0.00 %) | 446 | 410 | 970 | 1300 | 1895 | 162.31 |

## Carga normal — 30 usuarios, ramp-up 5 u/s, 60 s

Reporte interactivo: [`resultados_juan/normal.html`](resultados_juan/normal.html)

| Prueba | Peticiones | Errores | Media | P50 | P95 | P99 | Máx | req/s | RNF06 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| PR01 GET /inventario/inventory/stock | 255 | 0 (0.00 %) | 14 | 14 | 18 | 25 | 31 | 4.24 | ✅ |
| PR02 GET /inventario/inventory/stock?id_bodega | 231 | 0 (0.00 %) | 14 | 13 | 18 | 26 | 60 | 3.84 | ✅ |
| PR03 GET /inventario/inventory/stock?id_producto | 192 | 0 (0.00 %) | 14 | 13 | 17 | 21 | 24 | 3.20 | ✅ |
| PR04 GET /inventario/inventory/movements | 173 | 0 (0.00 %) | 16 | 15 | 19 | 22 | 24 | 2.88 | ✅ |
| PR05 GET /inventario/warehouses | 138 | 0 (0.00 %) | 12 | 12 | 15 | 21 | 31 | 2.30 | ✅ |
| PR06 POST /inventario/inventory/movements (ENTRADA) | 76 | 0 (0.00 %) | 41 | 39 | 57 | 62 | 62 | 1.26 | ✅ |
| PR07 POST /inventario/inventory/transfers | 43 | 0 (0.00 %) | 68 | 64 | 93 | 100 | 101 | 0.72 | ✅ |
| PR08 GET /abastecimiento/suppliers | 116 | 0 (0.00 %) | 11 | 11 | 13 | 14 | 23 | 1.93 | ✅ |
| PR09 GET /abastecimiento/purchase-orders | 126 | 0 (0.00 %) | 17 | 17 | 21 | 23 | 25 | 2.10 | ✅ |
| PR10 POST /abastecimiento/purchase-orders | 33 | 0 (0.00 %) | 23 | 22 | 26 | 52 | 52 | 0.55 | ✅ |
| PR11 GET /ventas/sales | 161 | 0 (0.00 %) | 20 | 19 | 26 | 51 | 53 | 2.68 | ✅ |
| PR12 POST /ventas/sales (Ventas -> Inventario) | 92 | 0 (0.00 %) | 74 | 70 | 99 | 140 | 142 | 1.53 | ✅ |
| PR13 GET /reportes/reports/dashboard | 234 | 0 (0.00 %) | 16 | 16 | 19 | 28 | 47 | 3.89 | ✅ |
| PR14 GET /reportes/alerts | 192 | 0 (0.00 %) | 16 | 16 | 20 | 29 | 36 | 3.20 | ✅ |
| PR15 GET /reportes/reports/inventory | 185 | 0 (0.00 %) | 13 | 13 | 16 | 26 | 38 | 3.08 | ✅ |

## Carga pico — 100 usuarios, ramp-up 15 u/s, 60 s

Reporte interactivo: [`resultados_juan/pico.html`](resultados_juan/pico.html)

| Prueba | Peticiones | Errores | Media | P50 | P95 | P99 | Máx | req/s | RNF06 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| PR01 GET /inventario/inventory/stock | 840 | 0 (0.00 %) | 26 | 20 | 65 | 110 | 185 | 13.98 | ✅ |
| PR02 GET /inventario/inventory/stock?id_bodega | 697 | 0 (0.00 %) | 23 | 19 | 51 | 89 | 185 | 11.60 | ✅ |
| PR03 GET /inventario/inventory/stock?id_producto | 696 | 0 (0.00 %) | 24 | 18 | 60 | 97 | 179 | 11.58 | ✅ |
| PR04 GET /inventario/inventory/movements | 543 | 0 (0.00 %) | 26 | 21 | 57 | 86 | 139 | 9.03 | ✅ |
| PR05 GET /inventario/warehouses | 447 | 0 (0.00 %) | 21 | 16 | 47 | 97 | 124 | 7.44 | ✅ |
| PR06 POST /inventario/inventory/movements (ENTRADA) | 305 | 0 (0.00 %) | 88 | 69 | 210 | 350 | 396 | 5.07 | ✅ |
| PR07 POST /inventario/inventory/transfers | 155 | 0 (0.00 %) | 162 | 120 | 510 | 710 | 733 | 2.58 | ✅ |
| PR08 GET /abastecimiento/suppliers | 417 | 0 (0.00 %) | 13 | 12 | 17 | 20 | 30 | 6.94 | ✅ |
| PR09 GET /abastecimiento/purchase-orders | 454 | 0 (0.00 %) | 28 | 26 | 38 | 79 | 100 | 7.55 | ✅ |
| PR10 POST /abastecimiento/purchase-orders | 132 | 0 (0.00 %) | 27 | 25 | 42 | 52 | 131 | 2.20 | ✅ |
| PR11 GET /ventas/sales | 574 | 0 (0.00 %) | 31 | 29 | 48 | 87 | 114 | 9.55 | ✅ |
| PR12 POST /ventas/sales (Ventas -> Inventario) | 271 | 0 (0.00 %) | 127 | 100 | 300 | 400 | 466 | 4.51 | ✅ |
| PR13 GET /reportes/reports/dashboard | 692 | 0 (0.00 %) | 22 | 20 | 38 | 50 | 97 | 11.51 | ✅ |
| PR14 GET /reportes/alerts | 565 | 0 (0.00 %) | 23 | 20 | 41 | 58 | 122 | 9.40 | ✅ |
| PR15 GET /reportes/reports/inventory | 571 | 0 (0.00 %) | 17 | 15 | 30 | 50 | 67 | 9.50 | ✅ |

## Estrés — 200 usuarios, ramp-up 30 u/s, 60 s

Reporte interactivo: [`resultados_juan/estres.html`](resultados_juan/estres.html)

| Prueba | Peticiones | Errores | Media | P50 | P95 | P99 | Máx | req/s | RNF06 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| PR01 GET /inventario/inventory/stock | 1157 | 0 (0.00 %) | 489 | 490 | 700 | 840 | 1125 | 19.24 | ✅ |
| PR02 GET /inventario/inventory/stock?id_bodega | 934 | 0 (0.00 %) | 483 | 490 | 720 | 890 | 930 | 15.53 | ✅ |
| PR03 GET /inventario/inventory/stock?id_producto | 899 | 0 (0.00 %) | 480 | 480 | 710 | 870 | 954 | 14.95 | ✅ |
| PR04 GET /inventario/inventory/movements | 719 | 0 (0.00 %) | 477 | 480 | 660 | 810 | 1073 | 11.96 | ✅ |
| PR05 GET /inventario/warehouses | 564 | 0 (0.00 %) | 478 | 470 | 680 | 800 | 882 | 9.38 | ✅ |
| PR06 POST /inventario/inventory/movements (ENTRADA) | 372 | 0 (0.00 %) | 884 | 900 | 1200 | 1300 | 1316 | 6.19 | ✅ |
| PR07 POST /inventario/inventory/transfers | 212 | 0 (0.00 %) | 1217 | 1200 | 1500 | 1700 | 1895 | 3.53 | ✅ |
| PR08 GET /abastecimiento/suppliers | 549 | 0 (0.00 %) | 282 | 280 | 540 | 600 | 697 | 9.13 | ✅ |
| PR09 GET /abastecimiento/purchase-orders | 541 | 0 (0.00 %) | 285 | 270 | 490 | 620 | 695 | 9.00 | ✅ |
| PR10 POST /abastecimiento/purchase-orders | 193 | 0 (0.00 %) | 290 | 290 | 490 | 690 | 700 | 3.21 | ✅ |
| PR11 GET /ventas/sales | 694 | 0 (0.00 %) | 292 | 280 | 510 | 700 | 728 | 11.54 | ✅ |
| PR12 POST /ventas/sales (Ventas -> Inventario) | 357 | 0 (0.00 %) | 905 | 920 | 1200 | 1300 | 1396 | 5.94 | ✅ |
| PR13 GET /reportes/reports/dashboard | 892 | 0 (0.00 %) | 277 | 280 | 490 | 620 | 738 | 14.83 | ✅ |
| PR14 GET /reportes/alerts | 737 | 0 (0.00 %) | 287 | 280 | 490 | 670 | 751 | 12.26 | ✅ |
| PR15 GET /reportes/reports/inventory | 741 | 0 (0.00 %) | 268 | 260 | 490 | 660 | 721 | 12.32 | ✅ |
