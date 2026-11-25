"""
make_vectors.py - Creates the test vectors ("golden" data) for the Verilog testbenches.

Files written to results/vectors/ (one hex value per line):
  input_pixels.hex     : noisy cameraman (10% S&P), 128x128, raster order
  expected_median.hex  : Python median output, 126x126
  expected_mag.hex     : Python Sobel magnitude of the median output, 124x124
  expected_edges.hex   : Python edge bits (magnitude >= 200), 124x124
  input_pixels_f2.hex, expected_median_f2.hex, expected_edges_f2.hex :
                         a second frame (noisy coins, 10%) for the back-to-back test
  median_windows.hex   : 9 pixels per line + expected median (unit test)
  sobel_windows.hex    : 9 pixels per line + expected magnitude (unit test)

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
    mag = dip.sobel_mag(med)
    edges = dip.threshold(mag)
    write_hex(os.path.join(OUT, "input_pixels.hex"), noisy)
    write_hex(os.path.join(OUT, "expected_median.hex"), med)
    write_hex(os.path.join(OUT, "expected_mag.hex"), mag, width=3)
    write_hex(os.path.join(OUT, "expected_edges.hex"), edges, width=1)

    # ---- Second frame (coins) for the back-to-back frame test ----------
    clean2 = cv2.resize(data.coins(), (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    noisy2 = dip.add_salt_pepper(clean2, NOISE, seed=dip.SEED + 1)
    med2, edges2 = dip.pipeline_median_sobel(noisy2)
    write_hex(os.path.join(OUT, "input_pixels_f2.hex"), noisy2)
    write_hex(os.path.join(OUT, "expected_median_f2.hex"), med2)
    write_hex(os.path.join(OUT, "expected_edges_f2.hex"), edges2, width=1)

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

    # ---- Sobel unit-test windows ---------------------------------------
    sw = rng.integers(0, 256, (n, 9))
    sw[:100] = rng.choice([0, 255], (100, 9))          # extreme gradients
    sw[100] = [0, 0, 255, 0, 0, 255, 0, 0, 255]        # max +Gx
    sw[101] = [255, 0, 0, 255, 0, 0, 255, 0, 0]        # max -Gx
    sw[102] = [255, 255, 255, 0, 0, 0, 0, 0, 0]        # max -Gy
    sw[103] = [0, 0, 0, 0, 0, 0, 255, 255, 255]        # max +Gy
    sw[104] = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    sw[105] = [0, 0, 255, 0, 0, 255, 255, 255, 255]    # |Gx|+|Gy| = 1530 (largest possible)
    with open(os.path.join(OUT, "sobel_windows.hex"), "w") as f:
        for w in sw:
            k = w.reshape(3, 3).astype(np.int64)
            m = abs(int((k * dip.GX).sum())) + abs(int((k * dip.GY).sum()))
            f.write(" ".join(f"{v:02x}" for v in w) + f" {m:03x}\n")

    print(f"edge pixels in frame 1: {int(edges.sum())}, frame 2: {int(edges2.sum())}")
    print(f"vectors written to {OUT}: {noisy.size} input pixels, "
          f"{med.size} expected median pixels, {n} unit-test windows")


if __name__ == "__main__":
    main()
