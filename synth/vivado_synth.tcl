# ============================================================================
# vivado_synth.tcl - synthesis + place and route of top_pipeline for Artix-7
#
# Run from the project root, in the "Vivado Tcl Shell":
#     cd C:/path/to/FPGA
#     source synth/vivado_synth.tcl
# or from a terminal:
#     vivado -mode batch -source synth/vivado_synth.tcl
#
# Writes to results/synthesis/vivado/:
#   utilization_synth.txt, utilization_impl.txt  (LUTs, flip-flops, BRAM, DSP)
#   timing_impl.txt                               (worst slack -> Fmax)
#   power_impl.txt                                (estimated power)
#   summary.txt                                   (the key numbers on one page)
#   top_pipeline_routed.dcp                       (open in Vivado to view)
# ============================================================================
set part     xc7a35tcpg236-1          ;# Artix-7 on the Basys3 board
set top      top_pipeline
set period   10.0                     ;# ns, 100 MHz target
set outdir   results/synthesis/vivado
file mkdir $outdir

read_verilog [list rtl/window_buffer.v rtl/median_filter.v rtl/median_stream.v \
                   rtl/sobel_filter.v rtl/threshold.v rtl/top_pipeline.v]
read_xdc synth/constraints.xdc

# ---- Synthesis (out of context: no pin assignment, no board) ----
synth_design -top $top -part $part -mode out_of_context
report_utilization    -file $outdir/utilization_synth.txt
report_utilization -hierarchical -file $outdir/utilization_hier.txt

# ---- Implementation ----
opt_design
place_design
phys_opt_design
route_design

report_utilization -file $outdir/utilization_impl.txt
report_timing_summary -max_paths 10 -file $outdir/timing_impl.txt
report_timing -max_paths 1 -path_type full -file $outdir/critical_path.txt
report_power -file $outdir/power_impl.txt
write_checkpoint -force $outdir/${top}_routed.dcp

# ---- One-page summary ----
proc count {filter} {
    if {[catch {llength [get_cells -quiet -hier -filter $filter]} n]} { return "?" }
    return $n
}
set wns     [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
set fmax    [expr {1000.0 / ($period - $wns)}]
set luts    [count {PRIMITIVE_GROUP == LUT}]
set lutram  [count {REF_NAME =~ RAM* && REF_NAME !~ RAMB*}]
set srls    [count {REF_NAME =~ SRL*}]
set ffs     [count {PRIMITIVE_GROUP == FLOP_LATCH}]
set brams   [count {REF_NAME =~ RAMB*}]
set dsps    [count {REF_NAME =~ DSP48*}]
set carry   [count {REF_NAME == CARRY4}]
set ptotal "?"; set pdyn "?"
set prep [report_power -return_string]
regexp {Total On-Chip Power \(W\)\s*\|\s*([0-9.]+)} $prep -> ptotal
regexp {Dynamic \(W\)\s*\|\s*([0-9.]+)} $prep -> pdyn

set f [open $outdir/summary.txt w]
puts $f "Vivado [version -short]  part $part  top $top"
puts $f "Clock target          : $period ns ([expr {1000.0/$period}] MHz)"
puts $f "Worst negative slack  : $wns ns"
puts $f [format "Maximum clock (Fmax)  : %.1f MHz" $fmax]
puts $f [format "Throughput at Fmax    : %.1f Mpixel/s, %.0f frames/s at 128x128" $fmax [expr {$fmax*1e6/16384.0}]]
puts $f "LUT cells (logic)     : $luts"
puts $f "LUTRAM / SRL cells    : $lutram / $srls"
puts $f "Flip-flops            : $ffs"
puts $f "CARRY4                : $carry"
puts $f "Block RAM             : $brams"
puts $f "DSP slices            : $dsps"
puts $f "Total on-chip power   : $ptotal W  (dynamic $pdyn W)"
puts $f "See utilization_impl.txt and power_impl.txt for the official tables."
close $f
puts [read [open $outdir/summary.txt]]
puts "Reports written to $outdir"
