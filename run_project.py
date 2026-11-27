"""
run_project.py - runs the complete FPGA Median-Sobel Edge Detection project.

    python run_project.py

1. Checks the Python packages (installs any that are missing).
2. Software experiment: noise, median filter and Sobel on 3 images x 3 noise levels.
3. Exports the golden test vectors for the Verilog testbenches.
4. Simulates the Verilog hardware and checks it against Python, bit for bit.
5. Compares the hardware output images with Python and redraws the figures.
6. Builds the project website from these fresh results and opens it.

Options:  --no-browser   build the website but do not open it
          --sim vivado   use the Vivado simulator even if Icarus Verilog is installed
"""
import argparse
import csv
import importlib
import os
import subprocess
import sys
import time
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
if os.name == "nt":
    os.system("")  # turn on colour codes in the Windows console

GREEN, RED, BOLD, DIM, END = "\033[32m", "\033[31m", "\033[1m", "\033[2m", "\033[0m"
PACKAGES = {"numpy": "numpy", "cv2": "opencv-python", "matplotlib": "matplotlib", "skimage": "scikit-image"}


def step(n, total, title):
    print(f"\n{BOLD}[{n}/{total}] {title}{END}")


def py(script, *args, optional=False):
    """Run one of the project's Python scripts with this same interpreter."""
    r = subprocess.run([sys.executable, script, *args], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        if optional:
            print(f"  {DIM}(skipped {script}: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else 'error'}){END}")
            return r
        print(r.stdout, r.stderr)
        sys.exit(f"{RED}Step failed: {script}{END}")
    return r


def check_packages():
    missing = []
    for mod, pkg in PACKAGES.items():
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"  installing: {', '.join(missing)}")
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", *missing])
        if r.returncode:
            sys.exit(f"{RED}Could not install {missing}. Check the internet connection and run again.{END}")
    print(f"  {GREEN}OK{END}  Python {sys.version.split()[0]}: numpy, opencv-python, matplotlib, scikit-image")


def show_metrics():
    rows = list(csv.DictReader(open(os.path.join(ROOT, "results", "metrics.csv"))))
    print(f"  {DIM}(each column: Sobel only -> median filter + Sobel){END}")
    print(f"  {'image':<10} {'noise':>5}   {'false edge pixels':<21}   {'edge F1':<12}   {'PSNR (dB)':<13}")
    for r in rows:
        print(f"  {r['image']:<10} {float(r['noise']) * 100:>4.0f}%   {int(r['base_fp']):>9,} -> {int(r['prop_fp']):<9,}   "
              f"{float(r['base_f1']):.2f} -> {float(r['prop_f1']):.2f}   "
              f"{float(r['psnr_noisy']):5.1f} -> {float(r['psnr_denoised']):4.1f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--sim", choices=["auto", "icarus", "vivado"], default="auto")
    args = ap.parse_args()
    t0 = time.time()
    total = 6
    print(f"{BOLD}FPGA Median-Sobel Edge Detection{END}  {DIM}(pipelined median filter + Sobel, Verilog, Artix-7){END}")

    step(1, total, "Checking Python packages")
    check_packages()

    step(2, total, "Software experiment: 3 images x 3 noise levels")
    py("python/run_experiments.py")
    show_metrics()

    step(3, total, "Exporting golden test vectors for the Verilog testbenches")
    py("python/make_vectors.py")
    print(f"  {GREEN}OK{END}  results/vectors/*.hex")

    step(4, total, "Simulating the Verilog hardware and checking it against Python")
    r = subprocess.run([sys.executable, "sim/simulate.py", "--sim", args.sim], cwd=ROOT)
    if r.returncode:
        sys.exit(f"{RED}Hardware simulation failed. See results/sim_log_*.txt{END}")

    step(5, total, "Comparing hardware output images with Python and drawing figures")
    out = py("python/compare_rtl.py").stdout
    for line in out.splitlines():
        if "differing" in line:
            print("  " + line.strip())
    for script in ("python/draw_synopsis_figures.py", "python/draw_architecture.py", "python/make_ui_images.py"):
        py(script, optional=True)
    print(f"  {GREEN}OK{END}  results/plots/, docs/figures/")

    step(6, total, "Building the project website")
    sys.path.insert(0, os.path.join(ROOT, "ui"))
    import build_site
    site = build_site.build()
    print(f"  {GREEN}OK{END}  {os.path.relpath(site, ROOT)}")

    print(f"\n{GREEN}{BOLD}Done in {time.time() - t0:.0f} s. All hardware tests passed.{END}")
    if not args.no_browser:
        print("Opening the website in the browser ...")
        webbrowser.open("file:///" + site.replace(os.sep, "/").lstrip("/"))


if __name__ == "__main__":
    main()
