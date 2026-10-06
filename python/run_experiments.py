"""
run_experiments.py - Runs the full software experiment.

For each test image and each noise level it computes:
  Case 1 (baseline) : noisy -> Sobel -> threshold
  Case 2 (proposed) : noisy -> median -> Sobel -> threshold
and compares both against the "ground truth" edges of the CLEAN image.

Outputs:
  images/original, noisy, denoised, edges   (PNG files)
  results/plots/*.png                        (comparison figures)
  results/metrics.csv                        (all numbers)

Run from the project root:   python python/run_experiments.py
"""
import os, csv
import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from skimage import data
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import structural_similarity as ssim

import dip

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZE = 128
NOISE_LEVELS = [0.05, 0.10, 0.20]


def p(*parts):
    path = os.path.join(ROOT, *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def shapes_image(n=SIZE):
    """Synthetic image with simple shapes: clear, known boundaries."""
    img = np.full((n, n), 60, np.uint8)
    cv2.rectangle(img, (12, 14), (58, 56), 200, -1)
    cv2.circle(img, (92, 38), 22, 150, -1)
    pts = np.array([[20, 112], [60, 72], [100, 112]], np.int32)
    cv2.fillPoly(img, [pts], 230)
    cv2.rectangle(img, (78, 78), (116, 100), 110, -1)
    return img


def load_images():
    def fit(a):  # resize to SIZE x SIZE grayscale
        return cv2.resize(a, (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    return {
        "cameraman": fit(data.camera()),
        "coins": fit(data.coins()),
        "shapes": shapes_image(),
    }


def edge_scores(pred, gt):
    tp = int(((pred == 1) & (gt == 1)).sum())
    fp = int(((pred == 1) & (gt == 0)).sum())
    fn = int(((pred == 0) & (gt == 1)).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return dict(edges=int(pred.sum()), fp=fp, precision=prec, recall=rec, f1=f1)


def main():
    rows = []
    imgs = load_images()
    for name, clean in imgs.items():
        cv2.imwrite(p("images", "original", f"{name}.png"), clean)
        # Ground truth = Sobel+threshold on the clean image, cropped to the
        # (H-4)x(W-4) region that the proposed pipeline produces.
        gt = dip.pipeline_sobel_only(clean)[1:-1, 1:-1]

        for d in NOISE_LEVELS:
            tag = f"{name}_{int(d*100):02d}"
            noisy = dip.add_salt_pepper(clean, d)
            med, edges_prop = dip.pipeline_median_sobel(noisy)
            edges_base = dip.pipeline_sobel_only(noisy)[1:-1, 1:-1]

            # Image quality (interior region, where the median exists)
            c_in = clean[1:-1, 1:-1]
            q = dict(
                psnr_noisy=psnr(c_in, noisy[1:-1, 1:-1], data_range=255),
                psnr_denoised=psnr(c_in, med, data_range=255),
                ssim_noisy=ssim(c_in, noisy[1:-1, 1:-1], data_range=255),
                ssim_denoised=ssim(c_in, med, data_range=255),
            )
            b = edge_scores(edges_base, gt)
            m = edge_scores(edges_prop, gt)
            row = dict(image=name, noise=d, **q,
                       **{f"base_{k}": v for k, v in b.items()},
                       **{f"prop_{k}": v for k, v in m.items()},
                       gt_edges=int(gt.sum()))
            rows.append(row)

            # Save images (full size for viewing)
            cv2.imwrite(p("images", "noisy", f"{tag}.png"), noisy)
            den_full = noisy.copy(); den_full[1:-1, 1:-1] = med
            cv2.imwrite(p("images", "denoised", f"{tag}.png"), den_full)
            cv2.imwrite(p("images", "edges", f"{tag}_sobel_only.png"),
                        dip.pad_to(edges_base, SIZE, SIZE) * 255)
            cv2.imwrite(p("images", "edges", f"{tag}_median_sobel.png"),
                        dip.pad_to(edges_prop, SIZE, SIZE) * 255)

            # Five-panel comparison figure
            panels = [(clean, "A. Original"), (noisy, f"B. Noisy ({int(d*100)}% S&P)"),
                      (den_full, "C. Denoised (median)"),
                      (dip.pad_to(edges_base, SIZE, SIZE), "D. Sobel on noisy"),
                      (dip.pad_to(edges_prop, SIZE, SIZE), "E. Median -> Sobel")]
            fig, ax = plt.subplots(1, 5, figsize=(15, 3.4))
            for a, (im, t) in zip(ax, panels):
                a.imshow(im, cmap="gray", vmin=0, vmax=im.max() if im.max() <= 1 else 255)
                a.set_title(t, fontsize=11); a.axis("off")
            fig.suptitle(f"{name}: false edges {b['fp']} -> {m['fp']},  "
                         f"edge F1 {b['f1']:.2f} -> {m['f1']:.2f}", fontsize=12)
            fig.tight_layout()
            fig.savefig(p("results", "plots", f"panel_{tag}.png"), dpi=130)
            plt.close(fig)

    # CSV
    with open(p("results", "metrics.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})

    # Summary plots: F1 and false edges vs noise
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    colors = {"cameraman": "#2a6fdb", "coins": "#d9822b", "shapes": "#2e9e5b"}
    for name in imgs:
        rs = [r for r in rows if r["image"] == name]
        x = [int(r["noise"] * 100) for r in rs]
        ax[0].plot(x, [r["base_f1"] for r in rs], "--o", color=colors[name], label=f"{name}: Sobel only")
        ax[0].plot(x, [r["prop_f1"] for r in rs], "-o", color=colors[name], label=f"{name}: Median->Sobel")
        ax[1].plot(x, [r["base_fp"] for r in rs], "--o", color=colors[name])
        ax[1].plot(x, [r["prop_fp"] for r in rs], "-o", color=colors[name])
    ax[0].set(title="Edge F1 score vs ground truth (higher is better)", xlabel="Noise density (%)", ylabel="F1", ylim=(0, 1))
    ax[1].set(title="False edge pixels (lower is better)", xlabel="Noise density (%)", ylabel="Pixels")
    ax[0].legend(fontsize=7.5); ax[0].grid(alpha=.3); ax[1].grid(alpha=.3)
    fig.text(0.5, 0.005, "dashed = Sobel on noisy image,  solid = Median -> Sobel", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(p("results", "plots", "summary_f1_falseedges.png"), dpi=130)
    plt.close(fig)

    for r in rows:
        print(f"{r['image']:10s} {int(r['noise']*100):2d}%  PSNR {r['psnr_noisy']:5.1f}->{r['psnr_denoised']:5.1f} dB  "
              f"SSIM {r['ssim_noisy']:.2f}->{r['ssim_denoised']:.2f}  "
              f"FP {r['base_fp']:5d}->{r['prop_fp']:4d}  F1 {r['base_f1']:.2f}->{r['prop_f1']:.2f}")


if __name__ == "__main__":
    main()
