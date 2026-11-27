# ============================================================================
# vivado_project.tcl - creates a Vivado GUI project for the presentation and viva.
#
# In Vivado: Tools -> Run Tcl Script... -> synth/vivado_project.tcl
# (or in the Tcl console:  cd C:/path/to/FPGA ; source synth/vivado_project.tcl)
#
# It adds all RTL, testbenches and test vectors, sets tb_top_pipeline as the
# simulation top, and runs the behavioural simulation so the waveform opens.
# Then you can show: RTL schematic (Open Elaborated Design), synthesis,
# implementation and the simulation waveform.
# ============================================================================
set root [file normalize [pwd]]
set proj_dir $root/vivado_proj
create_project -force fpga_median_sobel $proj_dir -part xc7a35tcpg236-1

add_files -norecurse [glob $root/rtl/*.v]
set_property top top_pipeline [current_fileset]
add_files -fileset constrs_1 -norecurse $root/synth/constraints.xdc
set_property USED_IN_SYNTHESIS true [get_files constraints.xdc]
set_property -name {STEPS.SYNTH_DESIGN.ARGS.MORE OPTIONS} -value {-mode out_of_context} -objects [get_runs synth_1]

# Testbenches + golden vectors (the testbench reads results/vectors/*.hex)
add_files -fileset sim_1 -norecurse [list $root/tb/tb_top_pipeline.v $root/tb/tb_sobel.v \
                                          $root/tb/tb_median.v $root/tb/tb_median_stream.v]
set_property top tb_top_pipeline [get_filesets sim_1]
set_property -name {xsim.simulate.runtime} -value {all} -objects [get_filesets sim_1]

# xsim runs in vivado_proj/.../sim_1/behav/xsim, so copy the vectors there
# using the same relative path the testbench expects.
set simdir $proj_dir/fpga_median_sobel.sim/sim_1/behav/xsim
file mkdir $simdir/results/vectors
foreach f [glob $root/results/vectors/*.hex] { file copy -force $f $simdir/results/vectors/ }

update_compile_order -fileset sources_1
update_compile_order -fileset sim_1
launch_simulation
puts "Project created in $proj_dir. Waveform is open; simulation result is in the Tcl console."
