# Resultados de las 15 pruebas de rendimiento — Cristian Bermúdez

_Generado con `resumen_cristian.py` el 2026-11-22 18:12. Todas las peticiones pasaron por el API Gateway (`http://localhost:8000/api`)._

Criterio: ✅ si P95 < 2000 ms y error < 1 % (RNF06). Tiempos en ms.

## Resumen por escenario

| Escenario | Peticiones | Errores | Media | P50 | P95 | P99 | Máx | req/s |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Carga normal — 30 usuarios, 60 s | 1935 | 0 (0.00 %) | 26 | 12 | 120 | 140 | 249 | 32.22 |
| Carga pico — 100 usuarios, 60 s | 6293 | 0 (0.00 %) | 35 | 14 | 130 | 360 | 592 | 104.81 |
| Estrés por escalones — 50→100→200→300 usuarios, 120 s | 16275 | 0 (0.00 %) | 297 | 120 | 1000 | 1800 | 2389 | 135.26 |
| Spike — 20→250→20 usuarios, 75 s | 5699 | 0 (0.00 %) | 489 | 190 | 2600 | 4200 | 5171 | 75.80 |
| Resistencia — 40 usuarios, 180 s | 7519 | 0 (0.00 %) | 26 | 12 | 110 | 140 | 251 | 41.70 |

## Carga normal — 30 usuarios, 60 s

Reporte interactivo: [`resultados_cristian/normal.html`](resultados_cristian/normal.html)

| Prueba | Peticiones | Errores | Media | P50 | P95 | P99 | Máx | req/s | RNF06 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| PC01 POST /usuarios/auth/login | 117 | 0 (0.00 %) | 113 | 110 | 130 | 130 | 136 | 1.95 | ✅ |
| PC02 POST /usuarios/auth/login (inválido -> 401) | 65 | 0 (0.00 %) | 100 | 99 | 110 | 110 | 113 | 1.08 | ✅ |
| PC03 POST /usuarios/auth/register | 36 | 0 (0.00 %) | 118 | 120 | 140 | 140 | 139 | 0.60 | ✅ |
| PC04 POST /usuarios/auth/verify | 130 | 0 (0.00 %) | 9 | 9 | 11 | 13 | 13 | 2.16 | ✅ |
| PC05 GET /usuarios/users | 125 | 0 (0.00 %) | 15 | 14 | 17 | 18 | 20 | 2.08 | ✅ |
| PC06 GET /usuarios/auth/me | 101 | 0 (0.00 %) | 12 | 12 | 15 | 17 | 19 | 1.68 | ✅ |
| PC07 GET /usuarios/roles | 70 | 0 (0.00 %) | 11 | 11 | 13 | 41 | 41 | 1.17 | ✅ |
| PC08 GET /usuarios/users sin JWT (-> 401) | 54 | 0 (0.00 %) | 5 | 5 | 6 | 7 | 7 | 0.90 | ✅ |
| PC09 GET /catalogo/products | 202 | 0 (0.00 %) | 16 | 15 | 18 | 20 | 21 | 3.36 | ✅ |
| PC10 GET /catalogo/products?q= | 197 | 0 (0.00 %) | 13 | 13 | 17 | 19 | 19 | 3.28 | ✅ |
| PC11 GET /catalogo/products?id_categoria= | 139 | 0 (0.00 %) | 12 | 12 | 15 | 16 | 16 | 2.31 | ✅ |
| PC12 GET /catalogo/products?q=&id_categoria=&activo= | 122 | 0 (0.00 %) | 12 | 12 | 14 | 17 | 19 | 2.03 | ✅ |
| PC13 GET /catalogo/categories | 143 | 0 (0.00 %) | 11 | 11 | 13 | 17 | 19 | 2.38 | ✅ |
| PC14 GET /catalogo/products/{id} | 125 | 0 (0.00 %) | 12 | 12 | 15 | 18 | 18 | 2.08 | ✅ |
| PC15 Flujo POS categorías->filtro->detalle | 219 | 0 (0.00 %) | 11 | 11 | 13 | 14 | 28 | 3.65 | ✅ |

## Carga pico — 100 usuarios, 60 s

Reporte interactivo: [`resultados_cristian/pico.html`](resultados_cristian/pico.html)

| Prueba | Peticiones | Errores | Media | P50 | P95 | P99 | Máx | req/s | RNF06 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| PC01 POST /usuarios/auth/login | 347 | 0 (0.00 %) | 134 | 120 | 190 | 380 | 583 | 5.78 | ✅ |
| PC02 POST /usuarios/auth/login (inválido -> 401) | 225 | 0 (0.00 %) | 126 | 110 | 180 | 370 | 539 | 3.75 | ✅ |
| PC03 POST /usuarios/auth/register | 131 | 0 (0.00 %) | 141 | 130 | 200 | 340 | 554 | 2.18 | ✅ |
| PC04 POST /usuarios/auth/verify | 448 | 0 (0.00 %) | 26 | 10 | 93 | 390 | 479 | 7.46 | ✅ |
| PC05 GET /usuarios/users | 465 | 0 (0.00 %) | 30 | 19 | 99 | 260 | 415 | 7.74 | ✅ |
| PC06 GET /usuarios/auth/me | 332 | 0 (0.00 %) | 26 | 13 | 81 | 280 | 480 | 5.53 | ✅ |
| PC07 GET /usuarios/roles | 205 | 0 (0.00 %) | 22 | 12 | 60 | 300 | 383 | 3.41 | ✅ |
| PC08 GET /usuarios/users sin JWT (-> 401) | 242 | 0 (0.00 %) | 6 | 6 | 9 | 11 | 11 | 4.03 | ✅ |
| PC09 GET /catalogo/products | 705 | 0 (0.00 %) | 18 | 17 | 23 | 27 | 42 | 11.74 | ✅ |
| PC10 GET /catalogo/products?q= | 557 | 0 (0.00 %) | 15 | 14 | 21 | 27 | 32 | 9.28 | ✅ |
| PC11 GET /catalogo/products?id_categoria= | 498 | 0 (0.00 %) | 14 | 13 | 19 | 22 | 26 | 8.29 | ✅ |
| PC12 GET /catalogo/products?q=&id_categoria=&activo= | 331 | 0 (0.00 %) | 14 | 13 | 19 | 22 | 38 | 5.51 | ✅ |
| PC13 GET /catalogo/categories | 417 | 0 (0.00 %) | 13 | 12 | 18 | 22 | 28 | 6.95 | ✅ |
| PC14 GET /catalogo/products/{id} | 442 | 0 (0.00 %) | 14 | 13 | 18 | 23 | 43 | 7.36 | ✅ |
| PC15 Flujo POS categorías->filtro->detalle | 648 | 0 (0.00 %) | 13 | 13 | 17 | 21 | 27 | 10.79 | ✅ |

## Estrés por escalones — 50→100→200→300 usuarios, 120 s

Reporte interactivo: [`resultados_cristian/estres.html`](resultados_cristian/estres.html)

| Prueba | Peticiones | Errores | Media | P50 | P95 | P99 | Máx | req/s | RNF06 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| PC01 POST /usuarios/auth/login | 892 | 0 (0.00 %) | 518 | 350 | 1200 | 2100 | 2334 | 7.41 | ✅ |
| PC02 POST /usuarios/auth/login (inválido -> 401) | 552 | 0 (0.00 %) | 503 | 330 | 1200 | 2200 | 2235 | 4.59 | ✅ |
| PC03 POST /usuarios/auth/register | 306 | 0 (0.00 %) | 490 | 350 | 1100 | 1900 | 2340 | 2.54 | ✅ |
| PC04 POST /usuarios/auth/verify | 1221 | 0 (0.00 %) | 374 | 170 | 1100 | 2000 | 2138 | 10.15 | ✅ |
| PC05 GET /usuarios/users | 1163 | 0 (0.00 %) | 401 | 210 | 1100 | 2000 | 2149 | 9.67 | ✅ |
| PC06 GET /usuarios/auth/me | 910 | 0 (0.00 %) | 376 | 200 | 1000 | 1900 | 2196 | 7.56 | ✅ |
| PC07 GET /usuarios/roles | 568 | 0 (0.00 %) | 396 | 220 | 1000 | 2000 | 2088 | 4.72 | ✅ |
| PC08 GET /usuarios/users sin JWT (-> 401) | 601 | 0 (0.00 %) | 197 | 10 | 680 | 1600 | 1819 | 4.99 | ✅ |
| PC09 GET /catalogo/products | 1734 | 0 (0.00 %) | 213 | 29 | 680 | 1500 | 1835 | 14.41 | ✅ |
| PC10 GET /catalogo/products?q= | 1452 | 0 (0.00 %) | 196 | 23 | 660 | 1200 | 1821 | 12.07 | ✅ |
| PC11 GET /catalogo/products?id_categoria= | 1139 | 0 (0.00 %) | 202 | 23 | 680 | 1500 | 1821 | 9.47 | ✅ |
| PC12 GET /catalogo/products?q=&id_categoria=&activo= | 858 | 0 (0.00 %) | 190 | 22 | 670 | 1200 | 1771 | 7.13 | ✅ |
| PC13 GET /catalogo/categories | 1142 | 0 (0.00 %) | 188 | 21 | 650 | 1000 | 1799 | 9.49 | ✅ |
| PC14 GET /catalogo/products/{id} | 1153 | 0 (0.00 %) | 192 | 22 | 660 | 1200 | 1732 | 9.58 | ✅ |
| PC15 Flujo POS categorías->filtro->detalle | 1684 | 0 (0.00 %) | 193 | 21 | 680 | 1500 | 1794 | 14.00 | ✅ |

## Spike — 20→250→20 usuarios, 75 s

Reporte interactivo: [`resultados_cristian/spike.html`](resultados_cristian/spike.html)

| Prueba | Peticiones | Errores | Media | P50 | P95 | P99 | Máx | req/s | RNF06 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| PC01 POST /usuarios/auth/login | 255 | 0 (0.00 %) | 518 | 540 | 970 | 1300 | 3224 | 3.39 | ✅ |
| PC02 POST /usuarios/auth/login (inválido -> 401) | 197 | 0 (0.00 %) | 542 | 560 | 1000 | 2800 | 3125 | 2.62 | ✅ |
| PC03 POST /usuarios/auth/register | 91 | 0 (0.00 %) | 564 | 570 | 900 | 2800 | 2793 | 1.21 | ✅ |
| PC04 POST /usuarios/auth/verify | 370 | 0 (0.00 %) | 391 | 390 | 780 | 1100 | 3639 | 4.92 | ✅ |
| PC05 GET /usuarios/users | 370 | 0 (0.00 %) | 405 | 430 | 840 | 1100 | 4509 | 4.92 | ✅ |
| PC06 GET /usuarios/auth/me | 306 | 0 (0.00 %) | 416 | 420 | 800 | 2400 | 4664 | 4.07 | ✅ |
| PC07 GET /usuarios/roles | 168 | 0 (0.00 %) | 416 | 450 | 720 | 1100 | 3454 | 2.23 | ✅ |
| PC08 GET /usuarios/users sin JWT (-> 401) | 174 | 0 (0.00 %) | 144 | 98 | 510 | 970 | 983 | 2.31 | ✅ |
| PC09 GET /catalogo/products | 578 | 0 (0.00 %) | 170 | 99 | 550 | 1400 | 3510 | 7.69 | ✅ |
| PC10 GET /catalogo/products?q= | 429 | 0 (0.00 %) | 157 | 98 | 510 | 1000 | 2828 | 5.71 | ✅ |
| PC11 GET /catalogo/products?id_categoria= | 380 | 0 (0.00 %) | 164 | 100 | 550 | 1600 | 3387 | 5.05 | ✅ |
| PC12 GET /catalogo/products?q=&id_categoria=&activo= | 295 | 0 (0.00 %) | 169 | 92 | 570 | 2000 | 3580 | 3.92 | ✅ |
| PC13 GET /catalogo/categories | 368 | 0 (0.00 %) | 129 | 92 | 410 | 760 | 1034 | 4.89 | ✅ |
| PC14 GET /catalogo/products/{id} | 359 | 0 (0.00 %) | 145 | 92 | 490 | 630 | 3228 | 4.77 | ✅ |
| PC15 Flujo POS categorías->filtro->detalle | 609 | 0 (0.00 %) | 134 | 86 | 360 | 600 | 3896 | 8.10 | ✅ |

## Resistencia — 40 usuarios, 180 s

Reporte interactivo: [`resultados_cristian/resistencia.html`](resultados_cristian/resistencia.html)

| Prueba | Peticiones | Errores | Media | P50 | P95 | P99 | Máx | req/s | RNF06 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| PC01 POST /usuarios/auth/login | 423 | 0 (0.00 %) | 118 | 120 | 140 | 150 | 222 | 2.35 | ✅ |
| PC02 POST /usuarios/auth/login (inválido -> 401) | 288 | 0 (0.00 %) | 103 | 100 | 110 | 120 | 125 | 1.60 | ✅ |
| PC03 POST /usuarios/auth/register | 129 | 0 (0.00 %) | 124 | 120 | 140 | 150 | 160 | 0.72 | ✅ |
| PC04 POST /usuarios/auth/verify | 587 | 0 (0.00 %) | 9 | 9 | 11 | 13 | 56 | 3.26 | ✅ |
| PC05 GET /usuarios/users | 556 | 0 (0.00 %) | 35 | 32 | 60 | 68 | 132 | 3.08 | ✅ |
| PC06 GET /usuarios/auth/me | 440 | 0 (0.00 %) | 13 | 12 | 15 | 18 | 83 | 2.44 | ✅ |
| PC07 GET /usuarios/roles | 293 | 0 (0.00 %) | 11 | 11 | 14 | 16 | 22 | 1.62 | ✅ |
| PC08 GET /usuarios/users sin JWT (-> 401) | 293 | 0 (0.00 %) | 6 | 5 | 7 | 9 | 10 | 1.62 | ✅ |
| PC09 GET /catalogo/products | 872 | 0 (0.00 %) | 16 | 16 | 19 | 21 | 24 | 4.84 | ✅ |
| PC10 GET /catalogo/products?q= | 715 | 0 (0.00 %) | 13 | 13 | 17 | 20 | 38 | 3.97 | ✅ |
| PC11 GET /catalogo/products?id_categoria= | 560 | 0 (0.00 %) | 12 | 12 | 15 | 17 | 20 | 3.11 | ✅ |
| PC12 GET /catalogo/products?q=&id_categoria=&activo= | 385 | 0 (0.00 %) | 12 | 12 | 15 | 17 | 21 | 2.14 | ✅ |
| PC13 GET /catalogo/categories | 538 | 0 (0.00 %) | 11 | 11 | 14 | 16 | 19 | 2.98 | ✅ |
| PC14 GET /catalogo/products/{id} | 552 | 0 (0.00 %) | 12 | 12 | 14 | 17 | 19 | 3.06 | ✅ |
| PC15 Flujo POS categorías->filtro->detalle | 768 | 0 (0.00 %) | 11 | 11 | 14 | 15 | 18 | 4.26 | ✅ |
