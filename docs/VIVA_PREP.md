# Viva preparation: Pipelined FPGA Median Filter and Sobel Edge Detection

Naina Sehgal (2401180029, A16) · Supervisor: Dr. Mandeep Narula · Minor Project 1, JIIT Noida

## The project in 30 seconds

Salt-and-pepper noise makes Sobel mark thousands of fake edges. A 3×3 median filter before Sobel removes 94–99% of them (edge F1 rises from 0.22–0.69 to 0.76–0.98). I built the whole chain as streaming Verilog hardware: two line-buffered window generators, a 3-stage median, a 2-stage Sobel and a threshold. It takes 1 pixel per clock, has 8 register stages of latency, and matches a Python model bit for bit on every pixel, magnitude and edge bit. On an Artix-7 xc7a35t (Vivado 2025.2) it uses 474 LUTs (2.3%), 303 flip-flops (0.7%), 1 BRAM tile and 0 DSPs. It meets timing at 100 MHz with +1.659 ns slack (Fmax ≈ 120 MHz) and uses 0.089 W.

## Numbers to remember

| What | Value |
|---|---|
| Image, noise | 128×128 8-bit; salt and pepper 5/10/20%, seed 2026 |
| False edges, cameraman 10% | 4,969 → 115 |
| Edge F1, cameraman 10% | 0.42 → 0.81 |
| PSNR, cameraman 10% | 15.2 → 26.3 dB |
| Median hardware | 3 stages, 31 comparators |
| Sobel hardware | 2 stages, adders and shifts only; Gx, Gy 11-bit signed; magnitude ≤ 1530 |
| Pipeline | 8 stages (1 + 3 + 1 + 2 + 1), 1 pixel/clock |
| Output sizes | median 126×126 = 15,876; edges 124×124 = 15,376 |
| First edge bit | 525 clocks after first pixel (first denoised pixel: 263) |
| Edge pixels (cameraman 10%) | 1,528 in hardware = Python |
| Vivado resources | 474 LUTs (442 logic + 32 LUTRAM), 303 FF, 1 BRAM tile (2 × RAMB18), 0 DSP |
| Timing | WNS +1.659 ns at 10 ns → Fmax ≈ 119.9 MHz ≈ 7,300 frames/s at 128×128 |
| Power | 0.089 W total (0.069 static, 0.021 dynamic) |

## Likely questions and short answers

**Concept**

1. **Why a median filter and not a mean (averaging) filter?** A mean spreads a 0 or 255 spike into its neighbours and blurs edges. A median ignores outliers. An isolated spike can never be the middle of 9 values, and a step edge is kept sharp.
2. **Why does Sobel give false edges on noisy images?** Sobel measures local brightness change. A single 0 or 255 pixel in a grey area is a huge local change, so it crosses the threshold.
3. **Why |Gx| + |Gy| instead of √(Gx² + Gy²)?** No square root and no multiplier are needed. It overestimates the true magnitude by up to about 41% at 45°, which only shifts the effective threshold. It is the usual hardware approximation.
4. **Why threshold 200?** It gives clean outlines on the clean test images. In hardware it is an input port (`thr`), so it can be changed without re-synthesis.
5. **Where does the median filter fail?** At high density (20%) some 3×3 windows contain 5 or more noise pixels, so the median itself is noise. False edges rise to 226–468. The fix is an adaptive median filter (larger window when needed).
6. **How did you measure accuracy?** I compared against Sobel on the clean image (ground truth), using false edge pixels, precision, recall, F1, and PSNR/SSIM for the denoised image.

**Hardware design**

7. **How does the median work without sorting 9 values?** Sort each row (low, mid, high). Then A = max of lows, B = median of mids, C = min of highs. median(A, B, C) is the median of all 9. That takes 31 comparators in 3 pipeline stages. It is proven equal to a full sort in Python and on 2,000 random windows in hardware.
8. **What is a line buffer and why two?** It is a memory that stores one image row. A 3×3 window needs the current pixel plus the two rows above, so two line buffers are enough. That is 2 × 128 bytes instead of storing the whole 16 KB frame.
9. **Why a second window buffer?** Sobel needs a 3×3 window of the denoised image, which comes out as a new stream (126 pixels wide), so the same module is reused with WIDTH = 126.
10. **What does "pipelined" mean here?** Each block is split by registers. A new pixel enters every clock while earlier pixels are still being processed further down. Throughput is 1 pixel per clock, and latency is 8 clocks.
11. **Why are there 9 clocks between the last input and the last edge in simulation?** The pipeline has 8 register stages, plus 1 clock for the testbench to capture the output.
12. **Why does the first edge appear only after 525 clocks?** The first window buffer must fill two rows plus three pixels (≈ 2 × 128) before its first valid window. The second must fill two rows of 126 (≈ 2 × 126). That is about 525 clocks in total. After that, outputs come every clock.
13. **What is the valid signal for?** It travels with the data through every stage. When the input pauses (`valid_in = 0`), nothing moves and nothing is output, so results stay correct. Tested with about 25% random pauses.
14. **What about border pixels?** Only pixels with a full 3×3 window are processed, so the median output is 126×126 and the edges 124×124. The Python model uses the same rule, so comparison is exact.
15. **Bit widths in Sobel?** Each weighted sum ≤ 4 × 255 = 1020, so Gx and Gy ∈ [−1020, +1020] need 11 bits signed. The magnitude is at most 1530 (e.g. Gx = 1020, Gy = 510; both cannot be 1020 at once), which fits in 11 bits.
16. **Why no multipliers?** The kernel weights are only ±1 and ±2. ×2 is a 1-bit left shift, so everything is additions and subtractions.
17. **Reset?** Synchronous, active high. Counters and valid flags are cleared, so no garbage is output after reset.
18. **Can it process consecutive frames?** Yes. The row counter wraps at the end of a frame. Tested with cameraman then coins back to back, without reset: 0 errors.

**Verification**

19. **How do you know the hardware is right?** Python writes golden .hex files. The testbenches stream inputs and compare every output automatically: 2,000 median windows, 2,000 Sobel windows (including the worst cases), the full image with and without pauses, and two frames. That is more than 60,000 outputs checked with 0 mismatches.
20. **Why Icarus Verilog and Vivado both?** Icarus is free and quick for repeated simulation. Vivado is the vendor tool needed for real synthesis, place and route, timing and power on the Artix-7.

**Vivado results**

21. **What is WNS and how did you get Fmax?** WNS (worst negative slack) is the required time minus the arrival time on the slowest path. +1.659 ns means the slowest path takes 10 − 1.659 = 8.34 ns, so Fmax ≈ 1/8.34 ns ≈ 120 MHz.
22. **What is the critical path?** From a line-buffer block RAM output in the first window buffer, through the first median stage (row min/med/max), to its register: 6 logic levels, about half logic and half routing delay.
23. **How could you make it faster?** Register the line-buffer output before the median, or split median stage 1 into two stages. That adds one clock of latency, but throughput stays 1 pixel per clock.
24. **Why does it use 1 block RAM when Yosys used none?** Vivado chose to put one line buffer of each window buffer in a small RAMB18 and the other in distributed RAM (LUTs). Yosys kept all four in LUTs. Both are fine; together it is still only 2% of the BRAM.
25. **What is "out of context"?** The design is implemented as a block without pin assignments, because there is no board. Logic, timing and power inside the block are real. I/O timing and I/O power are not included.
26. **Why so little power?** The design is small (2% of the chip) and has no DSPs. Most of the 0.089 W is the device's static power (0.069 W). The design itself uses only 0.021 W dynamic.
27. **How many frames per second?** At 100 MHz, about 6,100 frames/s at 128×128. At Fmax, about 7,300. For 640×480 it would be about 390 frames/s if the line buffers were made longer.

**Your professor's ML suggestion**

28. **Why not machine learning?** For impulse noise, the median filter already removes 94–99% of false edges with only 31 comparators and no multipliers. A neural network denoiser needs thousands of multiply-adds per pixel and many DSP slices. That is far more hardware for a problem a simple circuit already solves. ML would make sense for complex noise, or for recognising objects after edge detection.

**Limitations and future work**

29. **What would you do next?** Run it on a Basys3 with a camera (OV7670) and VGA output. Add an adaptive median for high noise. Add non-maximum suppression for thin edges (towards Canny). Support larger and colour images, and process several pixels per clock.

## Demo plan (about 5 minutes)

1. **Interface:** open `ui/index.html`. Pick cameraman, set noise to 10%, and show Sobel only vs median then Sobel. Click a pixel to show the 3×3 window and the median steps.
2. **Simulation:** run `bash sim/run_sim.sh` (or show `results/sim_log_top.txt`) and point to the PASS lines and 0 mismatches. Show the waveform (`results/tb_top_pipeline.vcd` in GTKWave, or the figure in the report).
3. **Hardware vs Python:** show `results/plots/rtl_vs_python_edges.png` (difference image all black).
4. **Vivado:** open `results/synthesis/vivado/top_pipeline_routed.dcp` (File → Checkpoint → Open). Show the device view, Report Utilization and Report Timing Summary (WNS +1.659 ns). Or run `source synth/vivado_project.tcl` to show the schematic and the behavioural simulation.
