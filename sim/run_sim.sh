#!/usr/bin/env bash
# run_sim.sh - compile and run the Phase 1 testbenches with Icarus Verilog.
# Run from the project root:   bash sim/run_sim.sh
set -e
cd "$(dirname "$0")/.."
mkdir -p sim/build

echo "== Unit test: median_filter =="
iverilog -g2012 -o sim/build/tb_median rtl/median_filter.v tb/tb_median.v
vvp -n sim/build/tb_median | tee results/sim_log_median_unit.txt

echo "== Streaming test with random input pauses =="
iverilog -g2012 -P tb_median_stream.GAPS=1 -o sim/build/tb_stream_gaps rtl/*.v tb/tb_median_stream.v
vvp -n sim/build/tb_stream_gaps | tee results/sim_log_stream_gaps.txt

# continuous run last, so its output file and waveform are the ones kept
echo "== Streaming test, one pixel every clock =="
iverilog -g2012 -o sim/build/tb_stream rtl/*.v tb/tb_median_stream.v
vvp -n sim/build/tb_stream | tee results/sim_log_stream.txt
