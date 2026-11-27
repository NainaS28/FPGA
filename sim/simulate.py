"""
simulate.py - compiles and runs every Verilog testbench of the project.

Works on Windows, Linux and macOS with either simulator:
  * Icarus Verilog (iverilog + vvp), if it is installed, or
  * the Vivado simulator (xvlog / xelab / xsim) that comes with AMD Vivado.

Each run's testbench report is saved to results/sim_log_<name>.txt and a
summary is printed. Exit code 0 means every testbench printed PASS.

    python sim/simulate.py                 # pick a simulator automatically
    python sim/simulate.py --sim vivado    # force the Vivado simulator
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RTL = ["rtl/window_buffer.v", "rtl/median_filter.v", "rtl/median_stream.v",
       "rtl/sobel_filter.v", "rtl/threshold.v", "rtl/top_pipeline.v"]

# (log name, testbench top, source files, parameter overrides, description)
RUNS = [
    ("median_unit",  "tb_median",        ["rtl/median_filter.v", "tb/tb_median.v"], {},
     "Median filter unit test (2,000 windows)"),
    ("sobel_unit",   "tb_sobel",         ["rtl/sobel_filter.v", "tb/tb_sobel.v"], {},
     "Sobel filter unit test (2,000 windows)"),
    ("stream_gaps",  "tb_median_stream", RTL + ["tb/tb_median_stream.v"], {"GAPS": 1},
     "Median stage, full image, random input pauses"),
    ("stream",       "tb_median_stream", RTL + ["tb/tb_median_stream.v"], {},
     "Median stage, full image, one pixel per clock"),
    ("top_2frames",  "tb_top_pipeline",  RTL + ["tb/tb_top_pipeline.v"], {"FRAMES": 2},
     "Full pipeline, two different frames back to back"),
    ("top_gaps",     "tb_top_pipeline",  RTL + ["tb/tb_top_pipeline.v"], {"GAPS": 1},
     "Full pipeline, random input pauses"),
    ("top",          "tb_top_pipeline",  RTL + ["tb/tb_top_pipeline.v"], {},
     "Full pipeline, one pixel per clock"),
]


def find_icarus():
    exe = shutil.which("iverilog")
    if exe:
        return exe, shutil.which("vvp") or os.path.join(os.path.dirname(exe), "vvp")
    for d in [r"C:\iverilog\bin", r"C:\Program Files\iverilog\bin", r"C:\Program Files (x86)\iverilog\bin"]:
        if os.path.exists(os.path.join(d, "iverilog.exe")):
            return os.path.join(d, "iverilog.exe"), os.path.join(d, "vvp.exe")
    return None


def find_vivado():
    ext = ".bat" if os.name == "nt" else ""
    exe = shutil.which("xvlog")
    if exe:
        return os.path.dirname(exe), ext
    patterns = [r"C:\AMDDesignTools\*\Vivado\bin", r"C:\Xilinx\Vivado\*\bin", r"C:\Xilinx\*\Vivado\bin",
                r"D:\AMDDesignTools\*\Vivado\bin", r"D:\Xilinx\Vivado\*\bin",
                "/tools/Xilinx/Vivado/*/bin", "/opt/Xilinx/Vivado/*/bin", "/tools/Xilinx/*/Vivado/bin"]
    for pat in patterns:
        for d in sorted(glob.glob(pat), reverse=True):  # newest version first
            if os.path.exists(os.path.join(d, "xvlog" + ext)):
                return d, ext
    return None


def report_lines(text):
    """Keep only the testbench's own report (between its dashed lines)."""
    lines = [l.rstrip() for l in text.splitlines()
             if "$finish" not in l and "VCD info" not in l and "VCD warning" not in l]
    dash = [i for i, l in enumerate(lines) if l.strip().startswith("-----")]
    if len(dash) >= 2:
        keep = lines[dash[0]:dash[-1] + 1]
        before = [l for l in lines[:dash[0]] if "mismatch" in l]
        return before + keep
    return [l for l in lines if l.strip()]


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, **kw)


def sim_icarus(tools, name, top, files, params):
    iverilog, vvp = tools
    os.makedirs(os.path.join(ROOT, "sim", "build"), exist_ok=True)
    out = os.path.join("sim", "build", name)
    cmd = [iverilog, "-g2012", "-s", top, "-o", out]
    for k, v in params.items():
        cmd += ["-P", f"{top}.{k}={v}"]
    r = run(cmd + files)
    if r.returncode:
        return False, r.stdout + r.stderr
    r = run([vvp, "-n", out])
    return True, r.stdout + r.stderr


_vivado_compiled = set()


def sim_vivado(tools, name, top, files, params):
    bindir, ext = tools
    tool = lambda t: os.path.join(bindir, t + ext)
    shell = os.name == "nt"           # .bat files need the Windows shell
    key = tuple(files)
    if key not in _vivado_compiled:   # compile each set of sources once
        r = run([tool("xvlog")] + files, shell=shell)
        if r.returncode:
            return False, r.stdout + r.stderr
        _vivado_compiled.clear()
        _vivado_compiled.add(key)
    snap = f"snap_{name}"
    cmd = [tool("xelab"), top, "-s", snap]
    for k, v in params.items():
        cmd += ["-generic_top", f"{k}={v}"]
    r = run(cmd, shell=shell)
    if r.returncode:
        return False, r.stdout + r.stderr
    r = run([tool("xsim"), snap, "-R"], shell=shell)
    return True, r.stdout + r.stderr


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sim", choices=["auto", "icarus", "vivado"], default="auto")
    args = ap.parse_args()

    icarus = find_icarus() if args.sim in ("auto", "icarus") else None
    vivado = find_vivado() if args.sim in ("auto", "vivado") and not icarus else None
    if icarus:
        simulator, fn, tools = "Icarus Verilog", sim_icarus, icarus
    elif vivado:
        simulator, fn, tools = "Vivado simulator (xsim)", sim_vivado, vivado
    else:
        print("No Verilog simulator found. Install Icarus Verilog (iverilog) or AMD Vivado.")
        return 2

    print(f"Simulator: {simulator}")
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "simulator.txt"), "w") as f:
        f.write(simulator + "\n")

    all_pass = True
    for name, top, files, params, desc in RUNS:
        ok, text = fn(tools, name, top, files, params)
        lines = report_lines(text) if ok else text.splitlines()
        passed = ok and any(l.strip().startswith("PASS") for l in lines)
        all_pass &= passed
        with open(os.path.join(ROOT, "results", f"sim_log_{name}.txt"), "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"  {'PASS' if passed else 'FAIL'}  {desc}")
        if not passed:
            print("\n".join("        " + l for l in lines[-25:]))
        else:
            info = [l.strip() for l in lines if "mismatch" in l or "Latency" in l or "Edge pixels" in l]
            for l in info or [l.strip() for l in lines if l.strip().startswith("PASS")]:
                print("        " + l)
    print("All testbenches passed." if all_pass else "Some testbenches FAILED.")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
