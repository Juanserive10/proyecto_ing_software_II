# Resultados de las 15 pruebas de rendimiento — Cristian Bermúdez

_Generado con `resumen_cristian.py` el 2026-11-21 17:56. Todas las peticiones pasaron por el API Gateway (`http://localhost:8000/api`)._

Criterio: ✅ si P95 < 2000 ms y error < 1 % (RNF06). Tiempos en ms.

## Resumen por escenario

| Escenario | Peticiones | Errores | Media | P50 | P95 | P99 | Máx | req/s |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Carga normal — 30 usuarios, 60 s | 1903 | 0 (0.00 %) | 28 | 16 | 110 | 200 | 450 | 31.66 |
| Carga pico — 100 usuarios, 60 s | 6184 | 0 (0.00 %) | 49 | 15 | 190 | 620 | 950 | 102.77 |
| Estrés por escalones — 50→100→200→300 usuarios, 120 s | 13242 | 0 (0.00 %) | 572 | 300 | 1700 | 3000 | 3897 | 109.94 |
| Spike — 20→250→20 usuarios, 75 s | 4228 | 0 (0.00 %) | 972 | 550 | 4900 | 7300 | 8616 | 56.19 |
| Resistencia — 40 usuarios, 180 s | 7472 | 0 (0.00 %) | 28 | 16 | 110 | 140 | 294 | 41.41 |

## Carga normal — 30 usuarios, 60 s

Reporte interactivo: [`resultados_cristian/normal.html`](resultados_cristian/normal.html)

| Prueba | Peticiones | Errores | Media | P50 | P95 | P99 | Máx | req/s | RNF06 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| PC01 POST /usuarios/auth/login | 87 | 0 (0.00 %) | 109 | 110 | 130 | 280 | 276 | 1.45 | ✅ |
| PC02 POST /usuarios/auth/login (inválido -> 401) | 63 | 0 (0.00 %) | 101 | 98 | 110 | 230 | 230 | 1.05 | ✅ |
| PC03 POST /usuarios/auth/register | 39 | 0 (0.00 %) | 109 | 110 | 120 | 130 | 127 | 0.65 | ✅ |
| PC04 POST /usuarios/auth/verify | 142 | 0 (0.00 %) | 15 | 13 | 18 | 120 | 169 | 2.36 | ✅ |
| PC05 GET /usuarios/users | 133 | 0 (0.00 %) | 19 | 19 | 26 | 75 | 93 | 2.21 | ✅ |
| PC06 GET /usuarios/auth/me | 112 | 0 (0.00 %) | 19 | 17 | 22 | 61 | 200 | 1.86 | ✅ |
| PC07 GET /usuarios/roles | 88 | 0 (0.00 %) | 16 | 15 | 20 | 88 | 88 | 1.46 | ✅ |
| PC08 GET /usuarios/users sin JWT (-> 401) | 65 | 0 (0.00 %) | 8 | 8 | 11 | 12 | 12 | 1.08 | ✅ |
| PC09 GET /catalogo/products | 196 | 0 (0.00 %) | 19 | 20 | 26 | 31 | 34 | 3.26 | ✅ |
| PC10 GET /catalogo/products?q= | 186 | 0 (0.00 %) | 16 | 16 | 24 | 26 | 27 | 3.09 | ✅ |
| PC11 GET /catalogo/products?id_categoria= | 134 | 0 (0.00 %) | 16 | 16 | 22 | 26 | 28 | 2.23 | ✅ |
| PC12 GET /catalogo/products?q=&id_categoria=&activo= | 110 | 0 (0.00 %) | 16 | 16 | 22 | 27 | 28 | 1.83 | ✅ |
| PC13 GET /catalogo/categories | 135 | 0 (0.00 %) | 15 | 15 | 21 | 25 | 25 | 2.25 | ✅ |
| PC14 GET /catalogo/products/{id} | 143 | 0 (0.00 %) | 16 | 15 | 22 | 33 | 34 | 2.38 | ✅ |
| PC15 Flujo POS categorías->filtro->detalle | 180 | 0 (0.00 %) | 14 | 14 | 20 | 27 | 29 | 2.99 | ✅ |

## Carga pico — 100 usuarios, 60 s

Reporte interactivo: [`resultados_cristian/pico.html`](resultados_cristian/pico.html)

| Prueba | Peticiones | Errores | Media | P50 | P95 | P99 | Máx | req/s | RNF06 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| PC01 POST /usuarios/auth/login | 340 | 0 (0.00 %) | 157 | 110 | 390 | 780 | 807 | 5.65 | ✅ |
| PC02 POST /usuarios/auth/login (inválido -> 401) | 234 | 0 (0.00 %) | 152 | 110 | 440 | 710 | 802 | 3.89 | ✅ |
| PC03 POST /usuarios/auth/register | 117 | 0 (0.00 %) | 148 | 110 | 310 | 710 | 804 | 1.94 | ✅ |
| PC04 POST /usuarios/auth/verify | 486 | 0 (0.00 %) | 70 | 16 | 310 | 640 | 878 | 8.08 | ✅ |
| PC05 GET /usuarios/users | 458 | 0 (0.00 %) | 65 | 26 | 260 | 650 | 706 | 7.61 | ✅ |
| PC06 GET /usuarios/auth/me | 334 | 0 (0.00 %) | 68 | 19 | 340 | 690 | 829 | 5.55 | ✅ |
| PC07 GET /usuarios/roles | 224 | 0 (0.00 %) | 57 | 17 | 170 | 530 | 737 | 3.72 | ✅ |
| PC08 GET /usuarios/users sin JWT (-> 401) | 249 | 0 (0.00 %) | 6 | 6 | 10 | 20 | 24 | 4.14 | ✅ |
| PC09 GET /catalogo/products | 667 | 0 (0.00 %) | 17 | 16 | 26 | 35 | 65 | 11.09 | ✅ |
| PC10 GET /catalogo/products?q= | 507 | 0 (0.00 %) | 14 | 13 | 23 | 30 | 72 | 8.43 | ✅ |
| PC11 GET /catalogo/products?id_categoria= | 432 | 0 (0.00 %) | 14 | 13 | 21 | 26 | 61 | 7.18 | ✅ |
| PC12 GET /catalogo/products?q=&id_categoria=&activo= | 339 | 0 (0.00 %) | 13 | 13 | 20 | 24 | 38 | 5.63 | ✅ |
| PC13 GET /catalogo/categories | 464 | 0 (0.00 %) | 13 | 12 | 20 | 23 | 64 | 7.71 | ✅ |
| PC14 GET /catalogo/products/{id} | 448 | 0 (0.00 %) | 14 | 13 | 21 | 26 | 32 | 7.45 | ✅ |
| PC15 Flujo POS categorías->filtro->detalle | 585 | 0 (0.00 %) | 13 | 12 | 21 | 26 | 27 | 9.72 | ✅ |

## Estrés por escalones — 50→100→200→300 usuarios, 120 s

Reporte interactivo: [`resultados_cristian/estres.html`](resultados_cristian/estres.html)

| Prueba | Peticiones | Errores | Media | P50 | P95 | P99 | Máx | req/s | RNF06 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| PC01 POST /usuarios/auth/login | 722 | 0 (0.00 %) | 863 | 730 | 1800 | 3500 | 3858 | 5.99 | ✅ |
| PC02 POST /usuarios/auth/login (inválido -> 401) | 478 | 0 (0.00 %) | 838 | 760 | 1800 | 3200 | 3680 | 3.97 | ✅ |
| PC03 POST /usuarios/auth/register | 247 | 0 (0.00 %) | 791 | 690 | 1800 | 3200 | 3847 | 2.05 | ✅ |
| PC04 POST /usuarios/auth/verify | 919 | 0 (0.00 %) | 796 | 670 | 1800 | 3400 | 3810 | 7.63 | ✅ |
| PC05 GET /usuarios/users | 905 | 0 (0.00 %) | 759 | 660 | 1800 | 3400 | 3777 | 7.51 | ✅ |
| PC06 GET /usuarios/auth/me | 694 | 0 (0.00 %) | 743 | 660 | 1700 | 3300 | 3734 | 5.76 | ✅ |
| PC07 GET /usuarios/roles | 483 | 0 (0.00 %) | 774 | 620 | 1800 | 3300 | 3692 | 4.01 | ✅ |
| PC08 GET /usuarios/users sin JWT (-> 401) | 459 | 0 (0.00 %) | 448 | 150 | 1300 | 2900 | 2968 | 3.81 | ✅ |
| PC09 GET /catalogo/products | 1441 | 0 (0.00 %) | 402 | 120 | 1200 | 2600 | 2990 | 11.96 | ✅ |
| PC10 GET /catalogo/products?q= | 1149 | 0 (0.00 %) | 378 | 100 | 1200 | 2500 | 2948 | 9.54 | ✅ |
| PC11 GET /catalogo/products?id_categoria= | 936 | 0 (0.00 %) | 380 | 99 | 1200 | 2300 | 2975 | 7.77 | ✅ |
| PC12 GET /catalogo/products?q=&id_categoria=&activo= | 700 | 0 (0.00 %) | 415 | 130 | 1200 | 2300 | 2984 | 5.81 | ✅ |
| PC13 GET /catalogo/categories | 921 | 0 (0.00 %) | 382 | 110 | 1200 | 2400 | 2982 | 7.65 | ✅ |
| PC14 GET /catalogo/products/{id} | 914 | 0 (0.00 %) | 424 | 190 | 1300 | 2700 | 2965 | 7.59 | ✅ |
| PC15 Flujo POS categorías->filtro->detalle | 1374 | 0 (0.00 %) | 401 | 140 | 1200 | 2400 | 2880 | 11.41 | ✅ |

## Spike — 20→250→20 usuarios, 75 s

Reporte interactivo: [`resultados_cristian/spike.html`](resultados_cristian/spike.html)

| Prueba | Peticiones | Errores | Media | P50 | P95 | P99 | Máx | req/s | RNF06 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| PC01 POST /usuarios/auth/login | 185 | 0 (0.00 %) | 883 | 940 | 1700 | 4700 | 6627 | 2.46 | ✅ |
| PC02 POST /usuarios/auth/login (inválido -> 401) | 157 | 0 (0.00 %) | 889 | 960 | 1700 | 3900 | 5842 | 2.09 | ✅ |
| PC03 POST /usuarios/auth/register | 66 | 0 (0.00 %) | 891 | 1000 | 1600 | 1800 | 1799 | 0.88 | ✅ |
| PC04 POST /usuarios/auth/verify | 219 | 0 (0.00 %) | 738 | 840 | 1600 | 1700 | 2056 | 2.91 | ✅ |
| PC05 GET /usuarios/users | 240 | 0 (0.00 %) | 841 | 890 | 1600 | 5300 | 8473 | 3.19 | ✅ |
| PC06 GET /usuarios/auth/me | 193 | 0 (0.00 %) | 786 | 890 | 1600 | 3800 | 3936 | 2.56 | ✅ |
| PC07 GET /usuarios/roles | 134 | 0 (0.00 %) | 848 | 920 | 1500 | 4000 | 5887 | 1.78 | ✅ |
| PC08 GET /usuarios/users sin JWT (-> 401) | 128 | 0 (0.00 %) | 387 | 380 | 930 | 1300 | 1267 | 1.70 | ✅ |
| PC09 GET /catalogo/products | 411 | 0 (0.00 %) | 412 | 380 | 970 | 1300 | 4866 | 5.46 | ✅ |
| PC10 GET /catalogo/products?q= | 330 | 0 (0.00 %) | 419 | 390 | 920 | 2800 | 6104 | 4.39 | ✅ |
| PC11 GET /catalogo/products?id_categoria= | 263 | 0 (0.00 %) | 416 | 380 | 1100 | 1300 | 5211 | 3.49 | ✅ |
| PC12 GET /catalogo/products?q=&id_categoria=&activo= | 229 | 0 (0.00 %) | 411 | 420 | 920 | 1200 | 6543 | 3.04 | ✅ |
| PC13 GET /catalogo/categories | 250 | 0 (0.00 %) | 407 | 370 | 980 | 2800 | 4191 | 3.32 | ✅ |
| PC14 GET /catalogo/products/{id} | 245 | 0 (0.00 %) | 415 | 380 | 1100 | 3900 | 4991 | 3.26 | ✅ |
| PC15 Flujo POS categorías->filtro->detalle | 428 | 0 (0.00 %) | 381 | 430 | 830 | 1200 | 1274 | 5.69 | ✅ |

## Resistencia — 40 usuarios, 180 s

Reporte interactivo: [`resultados_cristian/resistencia.html`](resultados_cristian/resistencia.html)

| Prueba | Peticiones | Errores | Media | P50 | P95 | P99 | Máx | req/s | RNF06 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| PC01 POST /usuarios/auth/login | 419 | 0 (0.00 %) | 109 | 100 | 150 | 180 | 231 | 2.32 | ✅ |
| PC02 POST /usuarios/auth/login (inválido -> 401) | 274 | 0 (0.00 %) | 102 | 99 | 120 | 190 | 233 | 1.52 | ✅ |
| PC03 POST /usuarios/auth/register | 138 | 0 (0.00 %) | 112 | 110 | 160 | 190 | 204 | 0.76 | ✅ |
| PC04 POST /usuarios/auth/verify | 582 | 0 (0.00 %) | 15 | 12 | 37 | 75 | 169 | 3.23 | ✅ |
| PC05 GET /usuarios/users | 561 | 0 (0.00 %) | 38 | 35 | 65 | 99 | 179 | 3.11 | ✅ |
| PC06 GET /usuarios/auth/me | 387 | 0 (0.00 %) | 19 | 16 | 46 | 110 | 179 | 2.14 | ✅ |
| PC07 GET /usuarios/roles | 281 | 0 (0.00 %) | 18 | 14 | 38 | 110 | 201 | 1.56 | ✅ |
| PC08 GET /usuarios/users sin JWT (-> 401) | 267 | 0 (0.00 %) | 7 | 7 | 10 | 12 | 12 | 1.48 | ✅ |
| PC09 GET /catalogo/products | 829 | 0 (0.00 %) | 19 | 19 | 26 | 32 | 39 | 4.59 | ✅ |
| PC10 GET /catalogo/products?q= | 758 | 0 (0.00 %) | 15 | 15 | 22 | 25 | 31 | 4.20 | ✅ |
| PC11 GET /catalogo/products?id_categoria= | 558 | 0 (0.00 %) | 15 | 15 | 21 | 25 | 29 | 3.09 | ✅ |
| PC12 GET /catalogo/products?q=&id_categoria=&activo= | 422 | 0 (0.00 %) | 15 | 15 | 20 | 24 | 33 | 2.34 | ✅ |
| PC13 GET /catalogo/categories | 550 | 0 (0.00 %) | 14 | 14 | 19 | 22 | 28 | 3.05 | ✅ |
| PC14 GET /catalogo/products/{id} | 588 | 0 (0.00 %) | 15 | 15 | 21 | 23 | 31 | 3.26 | ✅ |
| PC15 Flujo POS categorías->filtro->detalle | 738 | 0 (0.00 %) | 13 | 13 | 19 | 22 | 24 | 4.09 | ✅ |
