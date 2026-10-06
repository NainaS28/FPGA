"""
draw_synopsis_figures.py - Figures for the project synopsis (docs/figures/).
  methodology_flow.png  : end-to-end flow of the work done
  median_datapath.png   : 3-stage pipelined median filter datapath
  waveform_median.png   : simulation waveform of median_stream (needs the VCD from sim/run_sim.sh)
Run from the project root:   python python/draw_synopsis_figures.py
"""
import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "figures")
os.makedirs(OUT, exist_ok=True)
INK, GREEN, TINT, GREY, GOLD = "#14231b", "#1e6b47", "#d7e6dc", "#eef1ec", "#b77f00"


def box(ax, x, y, w, h, title, sub="", fc=TINT, ec=GREEN, fs=10.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                fc=fc, ec=ec, lw=1.3))
    ax.text(x + w / 2, y + h * (0.64 if sub else 0.5), title, ha="center", va="center",
            fontsize=fs, weight="bold", color=INK)
    if sub:
        ax.text(x + w / 2, y + h * 0.3, sub, ha="center", va="center", fontsize=8.6, color=INK)


def arrow(ax, x1, y1, x2, y2, color="#333"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", lw=1.4, color=color))


def methodology():
    fig, ax = plt.subplots(figsize=(12, 6.2))
    w, h = 2.3, 1.05
    # software row
    sw = [("1. Input image", "cameraman, coins, shapes\nresized to 128x128, 8-bit gray"),
          ("2. Add noise", "salt and pepper\n5%, 10%, 20%, seed 2026"),
          ("3. Median filter", "3x3 window\ninteger exact"),
          ("4. Sobel + threshold", "|Gx|+|Gy|, T = 200\nwith and without filter"),
          ("5. Evaluate", "PSNR, SSIM, false edges,\nF1 vs clean-image edges")]
    y1 = 4.3
    for i, (t, s) in enumerate(sw):
        x = 0.2 + i * (w + 0.12)
        box(ax, x, y1, w, h, t, s)
        if i: arrow(ax, x - 0.12, y1 + h / 2, x, y1 + h / 2)
    ax.text(0.2, y1 + h + 0.25, "Software reference model (Python, NumPy, OpenCV, scikit-image)", fontsize=11, weight="bold", color=INK)
    # hardware row
    hw = [("6. Test vectors", "noisy image + expected\nmedian as .hex files"),
          ("7. Verilog RTL", "window_buffer\nmedian_filter, median_stream"),
          ("8. Simulation", "Icarus Verilog testbenches\none pixel per clock"),
          ("9. Compare", "RTL output vs Python\npixel by pixel"),
          ("10. Results", "denoised image, waveform,\nlatency, throughput")]
    y2 = 1.6
    for i, (t, s) in enumerate(hw):
        x = 0.2 + i * (w + 0.12)
        box(ax, x, y2, w, h, t, s, fc=GREY)
        if i: arrow(ax, x - 0.12, y2 + h / 2, x, y2 + h / 2)
    ax.text(0.2, y2 - 0.35, "Hardware design and verification (Verilog HDL, Icarus Verilog, GTKWave)", fontsize=11, weight="bold", color=INK)
    # links between rows
    x3 = 0.2 + 2 * (w + 0.12) + w / 2
    ax.annotate("", xy=(0.2 + w / 2, y2 + h), xytext=(x3, y1),
                arrowprops=dict(arrowstyle="-|>", lw=1.3, color=GOLD, connectionstyle="arc3,rad=0.25"))
    ax.text(2.6, 3.55, "golden reference", fontsize=9, color=GOLD)
    x9 = 0.2 + 3 * (w + 0.12) + w / 2
    ax.annotate("", xy=(x9, y2 + h), xytext=(x3 + 0.3, y1),
                arrowprops=dict(arrowstyle="-|>", lw=1.3, color=GOLD, connectionstyle="arc3,rad=-0.15"))
    ax.text(0.2, 0.6, "11. Interactive interface (HTML, JavaScript): live demo of the same arithmetic, pixel inspector, and a clock-by-clock view of the hardware",
            fontsize=10, color=INK)
    ax.set_xlim(0, 12.5); ax.set_ylim(0.3, 6.1); ax.axis("off")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "methodology_flow.png"), dpi=140); plt.close(fig)


def datapath():
    fig, ax = plt.subplots(figsize=(12.5, 5.2))
    # inputs
    rows = ["row 0: w0 w1 w2", "row 1: w3 w4 w5", "row 2: w6 w7 w8"]
    for i, r in enumerate(rows):
        y = 3.6 - i * 1.4
        box(ax, 0.1, y, 2.0, 0.8, r, fc="#ffffff", ec="#777", fs=9.5)
        box(ax, 2.9, y, 2.4, 0.8, "sort 3", "min3, med3, max3", fs=10)
        arrow(ax, 2.1, y + 0.4, 2.9, y + 0.4)
        for j, lab in enumerate(["lo", "mid", "hi"]):
            yy = y + 0.65 - j * 0.25
            ax.text(5.45, yy, f"{lab}{i}", fontsize=8.5, va="center", color=INK)
    # stage 2
    s2 = [("A = max3(lo0, lo1, lo2)", 3.6), ("B = med3(mid0, mid1, mid2)", 2.2), ("C = min3(hi0, hi1, hi2)", 0.8)]
    for t, y in s2:
        box(ax, 6.4, y, 3.0, 0.8, t, fs=9.5)
        arrow(ax, 6.0, y + 0.4, 6.4, y + 0.4)
    # stage 3
    box(ax, 10.2, 2.2, 2.0, 0.8, "med3(A, B, C)", "= median of 9", fc="#f6e6b8", ec=GOLD, fs=10)
    for _, y in s2:
        arrow(ax, 9.4, y + 0.4, 10.2, 2.6)
    # pipeline registers
    for x, lab in [(2.5, "R"), (6.15, "R"), (9.8, "R")]:
        ax.plot([x, x], [0.6, 4.6], ls=(0, (4, 3)), color=GREEN, lw=1.2)
    ax.text(2.5, 4.85, "window regs", ha="center", fontsize=9, color=GREEN)
    ax.text(6.15, 4.85, "stage 1 regs", ha="center", fontsize=9, color=GREEN)
    ax.text(9.8, 4.85, "stage 2 regs", ha="center", fontsize=9, color=GREEN)
    ax.text(11.2, 1.7, "stage 3 reg\nmedian_out", ha="center", fontsize=9, color=GREEN)
    ax.text(0.1, 0.15, "Dashed lines are pipeline registers. Each stage takes 1 clock, so a new window enters every clock (throughput 1/clock, latency 3 clocks).",
            fontsize=9.5, color=INK)
    ax.set_xlim(0, 12.6); ax.set_ylim(0, 5.1); ax.axis("off")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "median_datapath.png"), dpi=140); plt.close(fig)


def waveform():
    sys.path.insert(0, os.path.join(ROOT, "python"))
    vcd = os.path.join(ROOT, "results", "tb_median_stream.vcd")
    if not os.path.exists(vcd):
        print("no VCD, run sim/run_sim.sh first"); return
    # minimal VCD reader for top-level testbench signals
    sigs = ["clk", "valid_in", "pix_in", "median_valid", "median_out"]
    t0, t1 = 2_560_000, 2_780_000
    ids, cur, hist, depth = {}, {}, {n: [] for n in sigs}, 0
    with open(vcd) as f:
        for line in f:
            s = line.split()
            if not s: continue
            if s[0] == "$scope": depth += 1
            elif s[0] == "$upscope": depth -= 1
            elif s[0] == "$var" and depth == 1 and s[4] in sigs and s[3] not in ids: ids[s[3]] = s[4]
            elif s[0].startswith("#"):
                t = int(s[0][1:])
                if t > t1: break
                if t >= t0:
                    for n in sigs: hist[n].append((t, cur.get(n, 0)))
            elif s[0][0] == "b" and len(s) == 2 and s[1] in ids:
                v = s[0][1:]; cur[ids[s[1]]] = int(v, 2) if set(v) <= {"0", "1"} else 0
            elif s[0][0] in "01xz" and s[0][1:] in ids:
                cur[ids[s[0][1:]]] = 1 if s[0][0] == "1" else 0
    fig, ax = plt.subplots(len(sigs), 1, figsize=(12, 4.8), sharex=True)
    for a, n in zip(ax, sigs):
        pts = hist[n]; ts = [(p[0] - t0) / 1000 for p in pts]; vs = [p[1] for p in pts]
        if n in ("pix_in", "median_out"):
            a.step(ts, vs, where="post", color=GREEN); a.set_ylim(-15, 270)
        else:
            a.step(ts, vs, where="post", color=INK if n == "clk" else GREEN); a.set_ylim(-0.3, 1.3); a.set_yticks([])
        a.set_ylabel(n, rotation=0, ha="right", va="center", fontsize=9.5)
        a.spines[["top", "right"]].set_visible(False)
    ax[-1].set_xlabel("time (ns) from 2.56 us; clock period 10 ns (100 MHz in simulation)")
    fig.suptitle("Simulation of median_stream: the first denoised pixels leave the pipeline", fontsize=11)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "waveform_median.png"), dpi=140); plt.close(fig)


def hw_architecture():
    """Implemented hardware: median_stream = window_buffer + median_filter."""
    fig, ax = plt.subplots(figsize=(12, 4.2))
    ax.add_patch(FancyBboxPatch((2.45, 0.35), 7.2, 3.2, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc="none", ec=GREEN, lw=1.2, ls=(0, (5, 3))))
    ax.text(2.6, 3.3, "median_stream.v (top level)", fontsize=10.5, color=GREEN, weight="bold")
    box(ax, 0.1, 1.45, 1.9, 1.1, "Pixel in", "8-bit + valid\n1 pixel / clock", fc="#ffffff", ec="#777")
    # window buffer with line buffers inside
    box(ax, 2.8, 0.7, 3.2, 2.3, "", fc=TINT)
    ax.text(4.4, 2.75, "window_buffer.v", ha="center", fontsize=10.5, weight="bold", color=INK)
    box(ax, 3.0, 1.95, 1.4, 0.55, "line buf 1", fc="#ffffff", ec=GREEN, fs=8.5)
    box(ax, 3.0, 1.2, 1.4, 0.55, "line buf 2", fc="#ffffff", ec=GREEN, fs=8.5)
    box(ax, 4.6, 1.2, 1.2, 1.3, "3x3\nregs", fc="#ffffff", ec=GREEN, fs=9)
    ax.text(4.4, 0.85, "128 px each, row/column counters", ha="center", fontsize=8.3, color=INK)
    box(ax, 6.5, 1.15, 2.8, 1.7, "median_filter.v", "3-stage pipeline\nrow sort, combine, med3", fs=10.5)
    box(ax, 10.1, 1.45, 1.8, 1.1, "Denoised out", "8-bit + valid\n126x126 pixels", fc="#f6e6b8", ec=GOLD)
    arrow(ax, 2.0, 2.0, 2.8, 2.0); arrow(ax, 6.0, 2.0, 6.5, 2.0); arrow(ax, 9.3, 2.0, 10.1, 2.0)
    ax.text(6.25, 2.2, "w0..w8", fontsize=8, ha="center", color=INK)
    ax.text(0.1, 0.05, "Latency 4 register stages (window 1 + median 3). Throughput 1 pixel per clock. Valid signals travel with the data.",
            fontsize=9.5, color=INK)
    ax.set_xlim(0, 12.1); ax.set_ylim(0, 3.8); ax.axis("off")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "hw_architecture.png"), dpi=140); plt.close(fig)


if __name__ == "__main__":
    methodology(); datapath(); waveform(); hw_architecture()
    print("figures written to docs/figures/")
