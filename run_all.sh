#!/usr/bin/env bash
# run_all.sh - runs the whole Phase 1 flow end to end.
set -e
cd "$(dirname "$0")"
python3 python/run_experiments.py     # software experiment + figures
python3 python/make_vectors.py        # golden test vectors for Verilog
bash sim/run_sim.sh                   # RTL simulation (Icarus Verilog)
python3 python/compare_rtl.py         # hardware vs Python image
python3 python/draw_architecture.py   # block diagram
echo "Done. See results/ and images/."
