#!/usr/bin/env bash
# run_sim.sh - compile and run all testbenches with Icarus Verilog.
# Run from the project root:   bash sim/run_sim.sh
set -e
cd "$(dirname "$0")/.."
mkdir -p sim/build

echo "== Unit test: median_filter =="
iverilog -g2012 -o sim/build/tb_median rtl/median_filter.v tb/tb_median.v
vvp -n sim/build/tb_median | tee results/sim_log_median_unit.txt

echo "== Unit test: sobel_filter =="
iverilog -g2012 -o sim/build/tb_sobel rtl/sobel_filter.v tb/tb_sobel.v
vvp -n sim/build/tb_sobel | tee results/sim_log_sobel_unit.txt

echo "== Phase 1 streaming median, with random input pauses =="
iverilog -g2012 -s tb_median_stream -P tb_median_stream.GAPS=1 -o sim/build/tb_stream_gaps rtl/*.v tb/tb_median_stream.v
vvp -n sim/build/tb_stream_gaps | tee results/sim_log_stream_gaps.txt

echo "== Phase 1 streaming median, one pixel every clock =="
iverilog -g2012 -s tb_median_stream -o sim/build/tb_stream rtl/*.v tb/tb_median_stream.v
vvp -n sim/build/tb_stream | tee results/sim_log_stream.txt

echo "== Full pipeline: two different frames back to back =="
iverilog -g2012 -s tb_top_pipeline -P tb_top_pipeline.FRAMES=2 -o sim/build/tb_top_2f rtl/*.v tb/tb_top_pipeline.v
vvp -n sim/build/tb_top_2f | tee results/sim_log_top_2frames.txt

echo "== Full pipeline: random input pauses =="
iverilog -g2012 -s tb_top_pipeline -P tb_top_pipeline.GAPS=1 -o sim/build/tb_top_gaps rtl/*.v tb/tb_top_pipeline.v
vvp -n sim/build/tb_top_gaps | tee results/sim_log_top_gaps.txt

# continuous single-frame run last, so its output files and waveform are the ones kept
echo "== Full pipeline: one pixel every clock =="
iverilog -g2012 -s tb_top_pipeline -o sim/build/tb_top rtl/*.v tb/tb_top_pipeline.v
vvp -n sim/build/tb_top | tee results/sim_log_top.txt
