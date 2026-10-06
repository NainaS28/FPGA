"""
compare_rtl.py - Turns the Verilog simulation output back into an image and
compares it with the Python reference.

Run AFTER sim/run_sim.sh, from the project root:   python python/compare_rtl.py
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = H = 128


def read_hex(name, shape):
    with open(os.path.join(ROOT, name)) as f:
        vals = [int(x, 16) for x in f.read().split()]
    return np.array(vals, dtype=np.uint8).reshape(shape)


def main():
    noisy = read_hex("results/vectors/input_pixels.hex", (H, W))
    py_med = read_hex("results/vectors/expected_median.hex", (H - 2, W - 2))
    rtl_med = read_hex("results/rtl_median.hex", (H - 2, W - 2))
    diff = np.abs(py_med.astype(int) - rtl_med.astype(int))
    n_diff = int((diff > 0).sum())
    print(f"Denoised image: {n_diff} differing pixels out of {py_med.size}")

    fig, ax = plt.subplots(1, 4, figsize=(14, 3.9))
    items = [(noisy, "Input to hardware (10% noise)"), (py_med, "Python median"),
             (rtl_med, "Verilog median (simulated)"), (diff, f"Difference: {n_diff} pixels")]
    for a, (im, t) in zip(ax, items):
        a.imshow(im, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
        a.set_title(t, fontsize=11); a.axis("off")
    fig.suptitle("Phase 1 check: hardware median filter vs Python reference (cameraman)", fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, "results", "plots", "rtl_vs_python_median.png"), dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    main()
