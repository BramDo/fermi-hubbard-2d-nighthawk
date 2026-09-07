#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT_DIR/scripts/python.sh"
if [[ -x /home/bram/.venvs/qiskit/bin/python ]]; then
  PYTHON=/home/bram/.venvs/qiskit/bin/python
fi

"$PYTHON" "$ROOT_DIR/cuprate_2d_hubbard_pipeline.py" \
  --lx 6 --ly 6 \
  --holes 4 \
  --U-over-t 8 \
  --t-prime-over-t -0.25 \
  --steps 4 \
  --dt 0.1 \
  --initial-state stripe_neel \
  --outdir "$ROOT_DIR/results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111"
