"""
draw_architecture.py - Draws the hardware block diagram (results/plots/architecture.png).
Solid blocks are built and tested (Phase 1). Dashed blocks are planned (Phase 2).
Run from the project root:   python python/draw_architecture.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DONE, PLANNED = "#d7e6dc", "#ffffff"

blocks = [
    ("Pixel stream\nin", "8-bit, 1 px/clk\n+ valid", "#e9ece8", True),
    ("window_buffer", "2 line buffers\n+ 3x3 registers\n1 clk", DONE, True),
    ("median_filter", "row sort, column\ncombine, median of 3\n3 clk", DONE, True),
    ("window_buffer", "second window\non clean pixels\n1 clk", PLANNED, False),
    ("sobel_filter", "Gx, Gy, |Gx|+|Gy|\n2 clk", PLANNED, False),
    ("threshold", "edge if >= T\n1 clk", PLANNED, False),
    ("Edge stream\nout", "1-bit, 1 px/clk", "#ffffff", False),
]

fig, ax = plt.subplots(figsize=(15, 3.4))
bw, gap, y = 1.75, 0.45, 0.4
for i, (name, sub, col, done) in enumerate(blocks):
    x = i * (bw + gap)
    ax.add_patch(FancyBboxPatch((x, y), bw, 1.5, boxstyle="round,pad=0.03,rounding_size=0.08",
                                fc=col, ec="#1e6b47" if done else "#7a857e", lw=1.4,
                                ls="-" if done else (0, (4, 3))))
    ax.text(x + bw / 2, y + 1.15, name, ha="center", va="center", fontsize=10.5, weight="bold",
            color="#14231b" if done else "#55605a")
    ax.text(x + bw / 2, y + 0.52, sub, ha="center", va="center", fontsize=8.3,
            color="#14231b" if done else "#55605a")
    if i < len(blocks) - 1:
        ax.annotate("", xy=(x + bw + gap - 0.03, y + 0.75), xytext=(x + bw + 0.03, y + 0.75),
                    arrowprops=dict(arrowstyle="-|>", lw=1.5, color="#333"))
mx = 2 * (bw + gap) + bw / 2
ax.annotate("denoised pixel out", xy=(mx, y), xytext=(mx, -0.45), ha="center", fontsize=9,
            arrowprops=dict(arrowstyle="<|-", lw=1.2, color="#1e6b47"), color="#1e6b47")
ax.text(0, 2.25, "Solid: built and tested in Phase 1 (median_stream.v).   Dashed: planned for Phase 2.",
        fontsize=10.5, color="#14231b")
ax.set_xlim(-0.2, len(blocks) * (bw + gap)); ax.set_ylim(-0.8, 2.5); ax.axis("off")
fig.tight_layout()
fig.savefig(os.path.join(ROOT, "results", "plots", "architecture.png"), dpi=140)
print("saved results/plots/architecture.png")
