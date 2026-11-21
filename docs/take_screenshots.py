"""Screenshot real app runs via deep links (Playwright + installed Chrome; dev-only: pip install playwright).

    python docs/take_screenshots.py T08 T12 T11     # test ids from test-data/test_inputs.yaml

Starts the Streamlit app, opens <app>/?q=<test input>&config=<config>, waits for the run
to finish and saves docs/screenshots/<id>.png. Run eval/run_tests.py first with the
same model/config so the answers are already cached (the screenshot then shows that
exact saved run).
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PORT = 8599


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--config", default="v5+sc")
    ap.add_argument("--model", default="")
    ap.add_argument("--wait", type=int, default=20, help="seconds to let each run render")
    args = ap.parse_args()

    tests = {t["id"]: t for t in yaml.safe_load(
        (ROOT / "test-data/test_inputs.yaml").read_text())["tests"]}
    chrome = os.getenv("CHROME") or shutil.which("google-chrome") or shutil.which("chromium")
    # needs: pip install playwright  (uses the installed Chrome, no browser download)
    if not chrome:
        sys.exit("Chrome not found; set CHROME=")
    out = ROOT / "docs/screenshots"
    out.mkdir(exist_ok=True)

    server = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app/streamlit_app.py",
         f"--server.port={PORT}", "--server.headless=true",
         "--browser.gatherUsageStats=false", "--theme.base=light"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://localhost:{PORT}/_stcore/health", timeout=1)
                break
            except Exception:  # noqa: BLE001
                time.sleep(1)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=chrome, headless=True)
            page = browser.new_page(viewport={"width": 1400, "height": 1100},
                                    device_scale_factor=1.5)
            for tid in args.ids:
                params = {"q": tests[tid]["input"], "config": args.config}
                if args.model:
                    params["model"] = args.model
                page.goto(f"http://localhost:{PORT}/?{urllib.parse.urlencode(params)}")
                # the run is finished when the human-review note (or an error) appears
                page.wait_for_selector("text=Human review", timeout=args.wait * 1000 * 30)
                page.wait_for_timeout(1500)
                png = out / f"{tid}.png"
                page.screenshot(path=str(png), full_page=True)
                print(f"wrote {png.relative_to(ROOT)}")
            browser.close()
    finally:
        server.terminate()


if __name__ == "__main__":
    main()
