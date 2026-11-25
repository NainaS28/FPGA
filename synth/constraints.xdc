# constraints.xdc - timing constraint for top_pipeline (out-of-context run)
# Target: 100 MHz system clock (10 ns), the Basys3 board oscillator.
# No pin locations are given: there is no physical board in this project, so
# the design is implemented "out of context" (as a block inside a larger chip)
# to measure resources, maximum clock frequency and power.
create_clock -name clk -period 10.000 [get_ports clk]
