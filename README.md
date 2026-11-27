# Pipelined FPGA Image Processing: Median Filter and Sobel Edge Detection

BTech 3rd-year ECE minor project by Naina Sehgal.

A 3×3 median filter removes salt-and-pepper noise from an image, and a Sobel
operator then finds the edges. The algorithm is modelled in Python (the
"golden" reference) and built as streaming, pipelined Verilog hardware for a
Xilinx Artix-7 FPGA. The hardware is checked bit for bit against Python in simulation.

![Architecture](results/plots/architecture.png)

## Project status

| Phase | Scope | Status |
|---|---|---|
| Phase 1 (mid evaluation) | Python reference model, full software experiment, Verilog line buffer and median filter, streaming median hardware with testbenches, interactive interface | Done |
| Phase 2 (final evaluation) | Verilog Sobel and threshold, full median to Sobel pipeline, end-to-end testbench, Vivado synthesis, latency, throughput and resource analysis | Done |

## Phase 1 results

**Software experiment** (128×128 images, salt-and-pepper noise at 5, 10 and 20 percent):

| Image | Noise | PSNR noisy to denoised | False edges: Sobel only to median then Sobel | Edge F1: Sobel only to median then Sobel |
|---|---|---|---|---|
| cameraman | 10% | 15.2 to 26.3 dB | 4969 to 115 | 0.42 to 0.81 |
| coins | 10% | 15.5 to 27.6 dB | 4684 to 216 | 0.54 to 0.88 |
| shapes | 10% | 15.1 to 33.2 dB | 5231 to 38 | 0.32 to 0.97 |

All 9 cases are in `results/metrics.csv`.

![Comparison](results/plots/panel_cameraman_10.png)

**Hardware** (Icarus Verilog simulation of `rtl/median_stream.v`):

- Median unit test: 2,000 of 2,000 random windows match Python.
- Streaming test on the noisy cameraman image: 15,876 of 15,876 denoised pixels match Python, 0 errors.
- Same test with about 25% random idle clocks in the input: 0 errors.
- Throughput: 1 pixel per clock (16,384 pixels in 16,389 clocks).
- Latency: 4 register stages (window buffer 1, median filter 3).

![Hardware vs Python](results/plots/rtl_vs_python_median.png)

## Phase 2 results: complete hardware pipeline

`rtl/top_pipeline.v` chains window buffer, median filter, a second window buffer,
Sobel and threshold. Icarus Verilog simulation (`python sim/simulate.py`):

| Test | Result |
|---|---|
| Sobel unit test (`tb/tb_sobel.v`) | 2,000 / 2,000 windows match Python, including the largest possible magnitude (1530) |
| Full pipeline, one pixel per clock (`tb/tb_top_pipeline.v`) | 15,876 denoised pixels, 15,376 Sobel magnitudes and 15,376 edge bits: 0 mismatches |
| Full pipeline, about 25% random input pauses | 0 mismatches |
| Two different frames back to back (cameraman, then coins), no reset | 31,752 denoised pixels and 30,752 edge bits: 0 mismatches |
| Edge pixels found by hardware (cameraman, 10% noise) | 1,528, the same as the Python result |

**Timing from simulation:** 1 pixel per clock (16,384 pixels in 16,393 clocks),
8 register stages (window 1, median 3, window 1, Sobel 2, threshold 1), measured
latency 9 clocks from last input to last edge bit, first edge bit 525 clocks after
the first pixel (two image rows fill each line buffer).

![Hardware vs Python edges](results/plots/rtl_vs_python_edges.png)

**Resources, Artix-7 xc7a35t** (see `results/synthesis/`):

| Resource / measure | Vivado 2025.2, after place and route | Yosys estimate |
|---|---|---|
| Slice LUTs | 474 (2.28%): 442 logic + 32 distributed RAM | 721 logic + 80 distributed RAM |
| Flip-flops | 303 (0.73%) | 334 |
| Block RAM | 1 tile (2 x RAMB18, 2%) | 0 |
| DSP slices | 0 | 0 |
| Timing at 100 MHz | met, worst slack +1.659 ns, hold +0.098 ns | not reported |
| Maximum clock (Fmax) | about 119.9 MHz (7,317 frames/s at 128x128) | not reported |
| Total on-chip power | 0.089 W (0.069 static, 0.021 dynamic) | not reported |

Implementation is out of context (no pins, no board), part xc7a35tcpg236-1.
The critical path runs from a line-buffer block RAM through the first median
stage (6 logic levels, 8.29 ns). Full reports are in `results/synthesis/vivado/`.

![Vivado device view](docs/figures/vivado_device.png)

## Project website

`website/FPGA_Median_Sobel_Edge_Detection.html` is the project's website: one
self-contained page that opens in any browser. `run_project.py` rebuilds it from
the latest results each time.

- **Try it:** pick a test image or your own, set the noise level and edge threshold,
  and compare edges with and without the median filter, with live metrics.
- **One pixel:** click any pixel to see the 3×3 window, the hardware median steps and the Sobel arithmetic.
- **Clock by clock:** step the median stage one clock at a time and watch the line
  buffers, window registers, pipeline stages and a timing diagram.
- **Verified:** hardware vs Python edge maps, the test table, the waveform and the
  simulation logs of the latest run.
- **On the FPGA:** Vivado resources, timing, power, schematic and placed design.
- **Code:** the Verilog of the top level, Sobel and threshold modules.

## Design choices

| Item | Choice |
|---|---|
| Image size | 128 × 128, 8-bit grayscale |
| Noise | Salt and pepper, 5, 10 and 20 percent, fixed seed 2026 |
| Median | 3×3, exact median by row sort, column combine, median of 3 |
| Sobel | Standard 3×3 kernels, magnitude = \|Gx\| + \|Gy\| |
| Threshold | 200 (edge if magnitude ≥ 200) |
| Border | Only pixels with a full 3×3 window get an output: median output 126×126, edge output 124×124 |
| Target FPGA | Artix-7 xc7a35tcpg236-1 (the Basys3 board's chip), 100 MHz clock target |

## Folder structure

```
run_project.py  runs everything (see below);  run.bat / run.sh  launchers
python/   dip.py (reference model), run_experiments.py, make_vectors.py,
          compare_rtl.py, draw_architecture.py, draw_synopsis_figures.py, make_ui_images.py
rtl/      window_buffer.v, median_filter.v, median_stream.v,
          sobel_filter.v, threshold.v, top_pipeline.v
tb/       tb_median.v, tb_median_stream.v, tb_sobel.v, tb_top_pipeline.v
sim/      simulate.py (Icarus Verilog or Vivado xsim), run_sim.sh
synth/    vivado_synth.tcl, vivado_project.tcl, constraints.xdc, yosys_synth.ys
ui/       website source: index.html, style.css, app.js, images.js, build_site.py
website/  FPGA_Median_Sobel_Edge_Detection.html (built website)
docs/     synopsis, report, presentations, VIVA_PREP.md, figures
images/   original, noisy, denoised, edges (PNG)
results/  metrics.csv, plots/, vectors/, simulation logs, synthesis/ (Vivado and Yosys reports)
```

## How to run

Needs Python 3 and a Verilog simulator: Icarus Verilog, or the simulator that
comes with AMD Vivado (found automatically). Missing Python packages are
installed on the first run.

**In VS Code:** open this folder, then press **Ctrl+Shift+B** (or Terminal →
Run Build Task). With the Python extension installed, **F5** does the same.
On Windows you can also double-click `run.bat`.

**From a terminal:**

```bash
python run_project.py               # everything, then opens the website
python run_project.py --sim vivado  # use the Vivado simulator
python sim/simulate.py              # Verilog testbenches only
```

The run: (1) checks packages, (2) runs the software experiment on 3 images × 3
noise levels, (3) exports golden test vectors, (4) simulates all Verilog
testbenches and checks them against Python, (5) compares the hardware output
images and redraws the figures, (6) builds the website and opens it.

**Vivado** (free ML Standard edition, Artix-7 device support), from the project
root in the Vivado Tcl Console:

```tcl
source synth/vivado_synth.tcl     # synthesis + place and route, reports in results/synthesis/vivado/
source synth/vivado_project.tcl   # GUI project with schematic and behavioural simulation
```

## Limitations

- No physical FPGA board is used. Results come from simulation and from Vivado
  synthesis and place-and-route (out of context, so no pin assignment and no I/O power).
- Images are read from files, not a live camera.
- Border pixels without a full 3×3 window are not processed.
- One fixed threshold is used for every image.
