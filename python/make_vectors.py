"""
make_vectors.py - Creates the test vectors ("golden" data) for the Verilog testbenches.

Phase 1 covers the median-filter hardware, so only median vectors are made.

Files written to results/vectors/ (one hex value per line):
  input_pixels.hex     : noisy cameraman (10% S&P), 128x128, raster order
  expected_median.hex  : Python median output, 126x126
  median_windows.hex   : 9 pixels per line + expected median (unit test)

Run from the project root:   python python/make_vectors.py
"""
import os
import numpy as np
import cv2
from skimage import data
import dip

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "vectors")
SIZE, NOISE = 128, 0.10


def write_hex(path, values, width=2):
    with open(path, "w") as f:
        for v in np.asarray(values).ravel():
            f.write(f"{int(v):0{width}x}\n")


def main():
    os.makedirs(OUT, exist_ok=True)

    # ---- Image vectors (streaming test) --------------------------------
    clean = cv2.resize(data.camera(), (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    noisy = dip.add_salt_pepper(clean, NOISE)
    med = dip.median3x3(noisy)
    write_hex(os.path.join(OUT, "input_pixels.hex"), noisy)
    write_hex(os.path.join(OUT, "expected_median.hex"), med)

    # ---- Unit-test vectors: random 3x3 windows -------------------------
    rng = np.random.default_rng(7)
    n = 2000
    wins = rng.integers(0, 256, (n, 9))
    wins[:200] = rng.choice([0, 255], (200, 9))                  # pure salt & pepper
    wins[200:400] = rng.choice([0, 1, 254, 255, 128], (200, 9))  # extremes / ties
    wins[400] = 255; wins[401] = 0                               # all-white, all-black

    with open(os.path.join(OUT, "median_windows.hex"), "w") as f:
        for w in wins:
            f.write(" ".join(f"{v:02x}" for v in w) + f" {int(np.sort(w)[4]):02x}\n")

    print(f"vectors written to {OUT}: {noisy.size} input pixels, "
          f"{med.size} expected median pixels, {n} unit-test windows")


if __name__ == "__main__":
    main()
