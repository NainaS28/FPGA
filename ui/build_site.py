"""
build_site.py - builds the project website from the latest results.

Packs ui/index.html, its CSS, JavaScript, every figure and the latest
simulation logs into one self-contained page:

    website/FPGA_Median_Sobel_Edge_Detection.html

The page opens in any browser, with or without internet.
"""
import base64
import datetime
import html
import os
import platform
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "website", "FPGA_Median_Sobel_Edge_Detection.html")


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def build():
    s = read("ui", "index.html")
    s = s.replace('<link rel="stylesheet" href="style.css">', "<style>\n" + read("ui", "style.css") + "\n</style>")
    for js in ("images.js", "app.js"):
        s = s.replace(f'<script src="{js}"></script>',
                      "<script>\n" + read("ui", js).replace("</script", "<\\/script") + "\n</script>")

    # figures -> embedded images
    def inline(m):
        path = os.path.normpath(os.path.join(ROOT, "ui", m.group(1)))
        with open(path, "rb") as f:
            return 'src="data:image/png;base64,' + base64.b64encode(f.read()).decode() + '"'
    s = re.sub(r'src="(\.\./[^"]+\.png)"', inline, s)

    # latest simulation logs
    def log(m):
        path = os.path.join(ROOT, "results", m.group(1))
        return html.escape(read("results", m.group(1)).strip()) if os.path.exists(path) else "(not run yet)"
    s = re.sub(r"<!--LOG:([\w.]+)-->", log, s)

    # when and how the results were produced
    sim_file = os.path.join(ROOT, "results", "simulator.txt")
    simulator = read("results", "simulator.txt").strip() if os.path.exists(sim_file) else "Icarus Verilog"
    logs = [f for f in os.listdir(os.path.join(ROOT, "results")) if f.startswith("sim_log_")]
    passed = sum(1 for f in logs if re.search(r"^PASS", read("results", f), re.M))
    stamp = datetime.datetime.now().strftime("%d %b %Y, %H:%M")
    info = (f"Results from the run on <b>{stamp}</b>: simulator <b>{html.escape(simulator)}</b>, "
            f"Python {platform.python_version()}, <b>{passed} of {len(logs)}</b> testbench runs passed.")
    s = s.replace("<!--RUNINFO-->", info)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(s)
    return OUT


if __name__ == "__main__":
    print("wrote", os.path.relpath(build(), ROOT))
