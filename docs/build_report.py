"""Render diagrams and build PDFs from the markdown docs (uses headless Chrome).

    python docs/build_report.py diagrams              # docs/architecture.md -> docs/diagrams/*.png
    python docs/build_report.py pdf docs/milestone2_report.md docs/M2_report.pdf

Mermaid is loaded from the jsDelivr CDN inside a local HTML page, so the first
command needs internet access. Set CHROME=/path/to/chrome if it is not found.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown
from PIL import Image, ImageChops

DOCS = Path(__file__).resolve().parent
MERMAID_JS = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"
DIAGRAM_NAMES = ["01_system_architecture", "02_prompt_workflow", "03_task_decomposition",
                 "04_input_output_flow", "05_self_correction_loop", "06_evaluation_flow"]


def chrome() -> str:
    for c in [os.getenv("CHROME"), "google-chrome", "chromium", "chromium-browser"]:
        if c and shutil.which(c):
            return shutil.which(c)
    sys.exit("Chrome/Chromium not found; set CHROME=/path/to/chrome")


def _run_chrome(args: list[str]) -> None:
    subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--hide-scrollbars", "--virtual-time-budget=15000", *args],
                   check=True, capture_output=True)


def render_diagrams() -> None:
    blocks = re.findall(r"```mermaid\n(.*?)```", (DOCS / "architecture.md").read_text(), re.S)
    out_dir = DOCS / "diagrams"
    out_dir.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name, code in zip(DIAGRAM_NAMES, blocks):
            html = Path(tmp) / f"{name}.html"
            html.write_text(f"""<!doctype html><html><head><meta charset="utf-8">
<style>body{{margin:0;padding:24px;background:#fff;font-family:Arial,sans-serif}}</style>
<script src="{MERMAID_JS}"></script></head><body>
<pre class="mermaid">{code}</pre>
<script>mermaid.initialize({{startOnLoad:true, theme:'default',
  flowchart:{{useMaxWidth:false}}, sequence:{{useMaxWidth:false}}}});</script>
</body></html>""")
            png = out_dir / f"{name}.png"
            _run_chrome([f"--screenshot={png}", "--window-size=2600,3000",
                         "--force-device-scale-factor=2", html.as_uri()])
            img = Image.open(png).convert("RGB")
            bbox = ImageChops.difference(img, Image.new("RGB", img.size, "white")).getbbox()
            if bbox and (bbox[2] >= img.width - 2 or bbox[3] >= img.height - 2):
                print(f"WARNING: {name} touches the window edge and may be clipped")
            if bbox:
                pad = 20
                img = img.crop((max(0, bbox[0] - pad), max(0, bbox[1] - pad),
                                min(img.width, bbox[2] + pad), min(img.height, bbox[3] + pad)))
            img.save(png)
            print(f"wrote {png.relative_to(DOCS.parent)} {img.size}")


CSS = """
@page { size: A4; margin: 16mm 14mm; }
body { font-family: Arial, Helvetica, sans-serif; font-size: 10.5pt; line-height: 1.4; color:#111; }
h1 { font-size: 20pt; margin: 0 0 8pt; } h2 { font-size: 15pt; margin-top: 18pt;
  border-bottom: 1px solid #ccc; padding-bottom: 3pt; } h3 { font-size: 12pt; margin-top: 12pt; }
h2 { page-break-before: always; } h2.first { page-break-before: avoid; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; font-size: 8.8pt; page-break-inside: auto; }
th, td { border: 1px solid #bbb; padding: 3pt 4pt; vertical-align: top; text-align: left; }
th { background: #f0f0ee; } tr { page-break-inside: avoid; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 8.6pt; background:#f4f4f2; }
pre { background: #f4f4f2; padding: 6pt; white-space: pre-wrap; word-break: break-word;
  font-size: 8.2pt; border: 1px solid #ddd; }
pre code { background: none; }
img { max-width: 100%; max-height: 210mm; display: block; margin: 6pt auto; }
blockquote { border-left: 3px solid #eb6834; margin: 6pt 0; padding: 2pt 8pt; background:#fff6f1; }
.pagebreak { page-break-after: always; }
"""


ROOT = DOCS.parent
_INCLUDE = re.compile(r"^<!-- include-(code|md): (\S+?)(?:#(.+?))? -->$", re.M)


def expand_includes(text: str) -> str:
    """<!-- include-code: path -->        file pasted as a text block (prompts stay text)
    <!-- include-md: path -->            markdown file inlined
    <!-- include-md: path#Heading -->    only the '## Heading' section (without the heading)
    Paths are relative to the repository root."""
    def repl(m):
        kind, rel, section = m.group(1), m.group(2), m.group(3)
        path = ROOT / rel
        if not path.exists():
            return f"> **MISSING INCLUDE:** `{rel}`"
        content = path.read_text().rstrip()
        if kind == "code":
            return f"```text\n{content}\n```"
        if section:
            parts = re.split(r"^## ", content, flags=re.M)
            match = [x for x in parts if x.startswith(section)]
            if not match:
                return f"> **MISSING SECTION:** `{rel}#{section}`"
            content = match[0].split("\n", 1)[1].strip()
        return expand_includes(content)   # nested includes
    return _INCLUDE.sub(repl, text)


def build_pdf(md_path: Path, pdf_path: Path) -> None:
    md_text = expand_includes(md_path.read_text())
    body = markdown.markdown(md_text, extensions=["tables", "fenced_code", "sane_lists"])
    body = body.replace("<h2>", '<h2 class="first">', 1)
    html_path = md_path.with_suffix(".html")
    html_path.write_text(f"<!doctype html><html><head><meta charset='utf-8'>"
                         f"<style>{CSS}</style></head><body>{body}</body></html>")
    _run_chrome([f"--print-to-pdf={pdf_path.resolve()}", "--no-pdf-header-footer",
                 html_path.resolve().as_uri()])
    html_path.unlink()
    print(f"wrote {pdf_path} ({pdf_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "diagrams":
        render_diagrams()
    elif len(sys.argv) == 4 and sys.argv[1] == "pdf":
        build_pdf(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        sys.exit(__doc__)
