#!/usr/bin/env bash
# Ejecuta los 3 escenarios de las 15 pruebas de Juan contra el API Gateway.
# Uso: ./performance-tests/run_juan.sh [normal pico estres]
set -euo pipefail

cd "$(dirname "$0")"
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
if [ "$#" -gt 0 ]; then
  SCENARIOS=("$@")
else
  SCENARIOS=(normal pico estres)
fi
mkdir -p resultados_juan

for s in "${SCENARIOS[@]}"; do
  echo "=== Escenario Juan: $s ==="
  SCENARIO="$s" GATEWAY_URL="$GATEWAY_URL" locust \
    -f locustfile.py --headless --host "$GATEWAY_URL" \
    --csv "resultados_juan/$s" --html "resultados_juan/$s.html" \
    --only-summary 2>&1 | tee "resultados_juan/$s.log"
done
