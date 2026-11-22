"""Genera RESULTADOS_JUAN.md a partir de los CSV de Locust (solo librería estándar).

Uso: python3 performance-tests/resumen_juan.py
"""
import csv
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
RESULTS = BASE / "resultados_juan"
OUTPUT = BASE / "RESULTADOS_JUAN.md"
SCENARIOS = [
    ("normal", "Carga normal — 30 usuarios, ramp-up 5 u/s, 60 s"),
    ("pico", "Carga pico — 100 usuarios, ramp-up 15 u/s, 60 s"),
    ("estres", "Estrés — 200 usuarios, ramp-up 30 u/s, 60 s"),
]
P95_LIMIT_MS = 2000
ERROR_LIMIT = 1.0


def load(scenario):
    path = RESULTS / f"{scenario}_stats.csv"
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def num(row, key):
    value = row.get(key, "") or "0"
    return float(value) if value != "N/A" else 0.0


def fmt_row(row):
    reqs = int(num(row, "Request Count"))
    fails = int(num(row, "Failure Count"))
    err = 100 * fails / reqs if reqs else 0
    p95 = num(row, "95%")
    ok = "✅" if p95 < P95_LIMIT_MS and err < ERROR_LIMIT else "⚠️"
    return (
        f"| {row['Name']} | {reqs} | {fails} ({err:.2f} %) | {num(row, 'Average Response Time'):.0f} | "
        f"{num(row, '50%'):.0f} | {p95:.0f} | {num(row, '99%'):.0f} | {num(row, 'Max Response Time'):.0f} | "
        f"{num(row, 'Requests/s'):.2f} | {ok} |"
    )


def main():
    lines = [
        "# Resultados de las 15 pruebas de rendimiento — Juan Sebastián Rivera",
        "",
        f"_Generado con `resumen_juan.py` el {datetime.now():%Y-%m-%d %H:%M}. Todas las peticiones pasaron por el API Gateway (`http://localhost:8000/api`)._",
        "",
        f"Criterio: ✅ si P95 < {P95_LIMIT_MS} ms y error < {ERROR_LIMIT:g} % (RNF06). Tiempos en ms.",
        "",
        "## Resumen por escenario",
        "",
        "| Escenario | Peticiones | Errores | Media | P50 | P95 | P99 | Máx | req/s |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    detail = []
    for scenario, title in SCENARIOS:
        rows = load(scenario)
        if rows is None:
            continue
        agg = next(r for r in rows if r["Name"] == "Aggregated")
        reqs = int(num(agg, "Request Count"))
        fails = int(num(agg, "Failure Count"))
        lines.append(
            f"| {title} | {reqs} | {fails} ({100 * fails / reqs if reqs else 0:.2f} %) | "
            f"{num(agg, 'Average Response Time'):.0f} | {num(agg, '50%'):.0f} | {num(agg, '95%'):.0f} | "
            f"{num(agg, '99%'):.0f} | {num(agg, 'Max Response Time'):.0f} | {num(agg, 'Requests/s'):.2f} |"
        )
        detail += [
            "",
            f"## {title}",
            "",
            f"Reporte interactivo: [`resultados_juan/{scenario}.html`](resultados_juan/{scenario}.html)",
            "",
            "| Prueba | Peticiones | Errores | Media | P50 | P95 | P99 | Máx | req/s | RNF06 |",
            "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |",
        ]
        detail += [fmt_row(r) for r in rows if r["Name"].startswith("PR")]

        failures = RESULTS / f"{scenario}_failures.csv"
        if failures.exists():
            with failures.open(newline="", encoding="utf-8") as fh:
                frows = list(csv.DictReader(fh))
            if frows:
                detail += ["", "**Errores registrados:**", "", "| Prueba | Error | Ocurrencias |", "| :--- | :--- | ---: |"]
                detail += [f"| {f['Name']} | {f['Error'][:120]} | {f['Occurrences']} |" for f in frows]

    OUTPUT.write_text("\n".join(lines + detail) + "\n", encoding="utf-8")
    print(f"Escrito {OUTPUT.relative_to(BASE.parent)}")


if __name__ == "__main__":
    main()
