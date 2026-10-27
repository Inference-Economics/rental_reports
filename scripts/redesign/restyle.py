"""Rewrite generator reports in the Inference Economics page design.

The cloud pipeline still produces the original HTML. This reads the figures and
Plotly charts out of that file and writes the redesigned page in its place.

    python scripts/redesign/restyle.py reports/toronto/2026-10/index.html ...
    python scripts/redesign/restyle.py --month 2026-10           # both cities
    python scripts/redesign/restyle.py --month 2026-10 --preview out/ --plotly plotly.min.js

Pages that are already redesigned are skipped, so running it twice is safe.
--preview writes self-contained copies (Plotly and images embedded) to a folder
instead of changing the reports.
"""
import argparse
import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract import extract_html  # noqa: E402
from render import ASSETS, MARKER, PATTERN, SKY, render  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CITIES = ("toronto", "vancouver")


def embed_images(page):
    """Swap asset URLs for data URIs so a preview opens with no network."""
    names = ["logo-symbol", "logo-wordmark", PATTERN] + [f for f, _ in SKY.values()]
    for name in names:
        data = (ROOT / "assets" / name).read_bytes()
        uri = "data:image/png;base64," + base64.b64encode(data).decode()
        page = page.replace(f"{ASSETS}/{name}?raw=1", uri).replace(f"{ASSETS}/{name}", uri)
    return page


def restyle(path, preview_dir=None, plotly_js=None):
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        print(f"{path}: already redesigned, skipped")
        return
    page = render(extract_html(text), plotly_js)
    if preview_dir:
        city, month = path.parts[-3], path.parts[-2]
        out = Path(preview_dir) / f"{city}-{month}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(embed_images(page), encoding="utf-8")
        print(f"{path}: preview written to {out}")
    else:
        path.write_text(page, encoding="utf-8")
        print(f"{path}: redesigned")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("paths", nargs="*", type=Path, help="report index.html files")
    p.add_argument("--month", help="YYYY-MM; restyles reports/<city>/<month>/index.html for both cities")
    p.add_argument("--preview", metavar="DIR", help="write self-contained copies here instead of in place")
    p.add_argument("--plotly", metavar="FILE", help="plotly.min.js to embed (previews only)")
    args = p.parse_args()

    paths = list(args.paths)
    if args.month:
        paths += [ROOT / "reports" / c / args.month / "index.html" for c in CITIES]
    if not paths:
        p.error("give report paths or --month")
    if args.plotly and not args.preview:
        p.error("--plotly only applies to --preview copies")
    plotly_js = Path(args.plotly).read_text() if args.plotly else None
    for path in paths:
        restyle(path, args.preview, plotly_js)


if __name__ == "__main__":
    main()
