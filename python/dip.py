"""
dip.py - Reference ("golden") image-processing model for the FPGA project.

Every function here uses plain INTEGER arithmetic, exactly like the Verilog
hardware, so the Python output and the RTL output can be compared bit-for-bit.

Pipeline:  noisy image -> 3x3 median -> Sobel (|Gx|+|Gy|) -> threshold -> edge map

Boundary policy ("valid-window" / zero border):
  A 3x3 window only exists for interior pixels. The hardware therefore only
  produces outputs for interior pixels:
     median output : (H-2) x (W-2)
     Sobel output  : (H-4) x (W-4)   (Sobel runs on the median output)
  For display, these are placed back in a full-size image with a zero border.
"""
import numpy as np

# Default parameters (keep identical to the Verilog parameters!)
THRESHOLD = 200          # edge if |Gx| + |Gy| >= THRESHOLD
SEED = 2026              # fixed random seed -> reproducible noise


# --------------------------------------------------------------------------
# Noise
# --------------------------------------------------------------------------
def add_salt_pepper(img, density, seed=SEED):
    """Set a fraction `density` of pixels to 0 (pepper) or 255 (salt)."""
    rng = np.random.default_rng(seed)
    out = img.copy()
    r = rng.random(img.shape)
    out[r < density / 2] = 0                          # pepper
    out[(r >= density / 2) & (r < density)] = 255     # salt
    return out


# --------------------------------------------------------------------------
# 3x3 sliding windows (interior pixels only)
# --------------------------------------------------------------------------
def windows3x3(img):
    """Return array of shape (H-2, W-2, 3, 3) with every interior 3x3 window."""
    img = img.astype(np.int32)
    H, W = img.shape
    win = np.empty((H - 2, W - 2, 3, 3), dtype=np.int32)
    for dy in range(3):
        for dx in range(3):
            win[:, :, dy, dx] = img[dy:dy + H - 2, dx:dx + W - 2]
    return win


# --------------------------------------------------------------------------
# Median filter
# --------------------------------------------------------------------------
def median3x3(img):
    """Exact median of each 3x3 window -> (H-2, W-2) uint8."""
    w = windows3x3(img).reshape(img.shape[0] - 2, img.shape[1] - 2, 9)
    return np.sort(w, axis=2)[:, :, 4].astype(np.uint8)


def median3x3_hw_style(img):
    """
    The SAME median, computed the way the hardware does it
    (sort rows -> combine columns -> median of 3). Used to prove the
    hardware algorithm is mathematically identical to a true median.
    """
    w = windows3x3(img)
    rows = np.sort(w, axis=3)                 # sort each row: [min, med, max]
    max_of_mins = rows[:, :, :, 0].max(axis=2)
    med_of_meds = np.median(rows[:, :, :, 1], axis=2).astype(np.int32)
    min_of_maxs = rows[:, :, :, 2].min(axis=2)
    trio = np.stack([max_of_mins, med_of_meds, min_of_maxs], axis=2)
    return np.median(trio, axis=2).astype(np.uint8)


# --------------------------------------------------------------------------
# Sobel + threshold
# --------------------------------------------------------------------------
GX = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.int32)
GY = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.int32)


def sobel_mag(img):
    """|Gx| + |Gy| for each interior pixel -> (H-2, W-2) int32 (range 0..2040)."""
    w = windows3x3(img)
    gx = (w * GX).sum(axis=(2, 3))
    gy = (w * GY).sum(axis=(2, 3))
    return np.abs(gx) + np.abs(gy)


def threshold(mag, t=THRESHOLD):
    """Binary edge map: 1 where mag >= t."""
    return (mag >= t).astype(np.uint8)


# --------------------------------------------------------------------------
# Full pipelines
# --------------------------------------------------------------------------
def pipeline_median_sobel(img, t=THRESHOLD):
    """Proposed system: median -> Sobel -> threshold. Returns (median, edges)."""
    med = median3x3(img)                     # (H-2, W-2)
    edges = threshold(sobel_mag(med), t)     # (H-4, W-4)
    return med, edges


def pipeline_sobel_only(img, t=THRESHOLD):
    """Baseline: Sobel -> threshold directly on the (noisy) image. (H-2, W-2)."""
    return threshold(sobel_mag(img), t)


def pad_to(arr, H, W):
    """Place a cropped result in the centre of an HxW zero image (for display)."""
    out = np.zeros((H, W), dtype=arr.dtype)
    b = (H - arr.shape[0]) // 2
    out[b:b + arr.shape[0], b:b + arr.shape[1]] = arr
    return out
