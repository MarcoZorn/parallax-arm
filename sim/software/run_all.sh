#!/usr/bin/env bash
# Rigenera tutta la validazione software (REPORT.md riporta questi numeri).
#   ./run_all.sh            tutto: test del progetto, build, equivalenza (1000 scenari per tipo), fuzz, e2e, UI
#   N=3000 ./run_all.sh     più scenari di equivalenza
# Uscite in build/ (log e JSON). Exit 1 se un passo fallisce.
set -u
cd "$(dirname "$0")"
ROOT=$(cd ../.. && pwd)
PIO=${PIO:-$HOME/.local/bin/pio}
N=${N:-1000}
mkdir -p build
declare -a RES=()

step() { # nome, comando...
  local name=$1; shift
  printf '\n== %s\n' "$name"
  local t0=$SECONDS
  if "$@" > "build/$name.log" 2>&1; then RES+=("OK  $name ($((SECONDS - t0)) s)"); tail -n 4 "build/$name.log"
  else RES+=("KO  $name (vedi build/$name.log)"); tail -n 25 "build/$name.log"; fi
}

step progetto-pio-test   bash -c "cd '$ROOT/firmware' && '$PIO' test -e native"
step progetto-pio-run    bash -c "cd '$ROOT/firmware' && '$PIO' run -e esp32dev"
step progetto-npm-test   bash -c "cd '$ROOT/web' && npm test"
step progetto-npm-build  bash -c "cd '$ROOT/web' && npm run build"

step compila-harness     bash -c "g++ -O2 -std=c++17 -I'$ROOT/firmware/include' -I'$ROOT/firmware/src' fw_sim.cpp '$ROOT/firmware/src/motion.cpp' -o build/fw_sim && \
                                  g++ -O1 -g -std=c++17 -Wall -fsanitize=address,undefined -fno-sanitize-recover=undefined -I'$ROOT/firmware/include' -I'$ROOT/firmware/src' fw_fuzz.cpp '$ROOT/firmware/src/motion.cpp' -o build/fw_fuzz"
step 1-equivalenza       bash -c "node equiv.mjs $N 12345 > build/equiv.json"
step 2-parametri         node params.mjs
step 3-ik-fk             bash -c "node ikfk.mjs > build/ikfk.json"
step 4-fuzz-firmware     ./build/fw_fuzz
step 5-e2e-protocollo    node e2e.mjs
step 4-5-ui-chrome       node ui_fuzz.mjs

printf '\n== ESITO\n'
printf '%s\n' "${RES[@]}"
! printf '%s\n' "${RES[@]}" | grep -q '^KO'
