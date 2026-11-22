#!/usr/bin/env bash
# Ejecuta los escenarios de las 15 pruebas de Cristian contra el API Gateway.
# Uso: ./performance-tests/run_cristian.sh [normal pico estres spike resistencia]
set -euo pipefail

cd "$(dirname "$0")"
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
LOCUST_IMAGE="${LOCUST_IMAGE:-locustio/locust:2.37.10}"
SCENARIOS=("${@:-normal pico estres spike resistencia}")
mkdir -p resultados_cristian

for s in ${SCENARIOS[@]}; do
  echo "=== Escenario: $s ==="
  docker run --rm --network host -u "$(id -u):$(id -g)" \
    -e SCENARIO="$s" -e GATEWAY_URL="$GATEWAY_URL" \
    -v "$PWD:/mnt/locust" -w /mnt/locust "$LOCUST_IMAGE" \
    -f locustfile_cristian.py --headless --host "$GATEWAY_URL" \
    --csv "resultados_cristian/$s" --html "resultados_cristian/$s.html" \
    --only-summary 2>&1 | tee "resultados_cristian/$s.log" || true
done
