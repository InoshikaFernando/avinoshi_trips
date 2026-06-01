#!/usr/bin/env python3
"""
Build a single-file print edition (print-edition.html) by combining the
cover, intro, city features, the Prepare page, and all 11 day pages.
Then render it to japan-trip-2025.pdf with headless Chrome/Edge.

Re-run this whenever content changes:
    python build_print_edition.py
"""
import re
import subprocess
import sys
from pathlib import Path
from PIL import Image

HERE = Path(__file__).parent
ORDER = ["prepare.html"] + [f"day_{i:02d}.html" for i in range(1, 12)]
MAX_EDGE = 1400  # downscale long edge for print (keeps PDF light)


def build_print_images():
    """Create downscaled JPEG copies so headless Chrome can render without
    blowing up on ~200 MB of full-res photos. Returns the folder name."""
    src_dir = HERE / "images"
    dst_dir = HERE / "images_print"
    dst_dir.mkdir(exist_ok=True)
    for img in src_dir.glob("*.jpg"):
        dst = dst_dir / img.name
        if dst.exists() and dst.stat().st_mtime >= img.stat().st_mtime:
            continue
        with Image.open(img) as im:
            im = im.convert("RGB")
            im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
            im.save(dst, "JPEG", quality=82, optimize=True)
    print(f"Prepared downscaled images in {dst_dir}")
    return "images_print"


def read(name):
    return (HERE / name).read_text(encoding="utf-8")


def slice_between(text, start_marker, end_marker):
    """Return substring between two markers (exclusive of markers)."""
    s = text.index(start_marker) + len(start_marker)
    e = text.index(end_marker, s)
    return text[s:e]


def container_inner(html):
    """Grab inner HTML of the main .container, minus the nav-row."""
    inner = slice_between(html, '<div class="container">', "</div>\n<footer")
    # remove the trailing nav-row block
    inner = re.sub(r'<div class="nav-row">.*?</div>\s*$', "", inner, flags=re.S)
    return inner.strip()


def section_title(html):
    """Pull the <title> for a running label."""
    m = re.search(r"<title>(.*?)</title>", html, flags=re.S)
    return m.group(1).strip() if m else ""


# ── Front matter from index.html ──────────────────────────────
index = read("index.html")
cover = "<div class=\"cover\">" + slice_between(index, '<div class="cover">', '<div class="topbar">')
# editor's letter + pull quote + cities (up to the Contents section)
front = slice_between(index, '<div class="container">', '<!-- ═══════════ CONTENTS ═══════════ -->')
# food pages (closing section)
food = '<!-- ═══════════ FOOD ═══════════ -->' + slice_between(
    index, '<!-- ═══════════ FOOD ═══════════ -->', "</div>\n\n<footer")

# ── Assemble body sections ────────────────────────────────────
sections = []
sections.append(f'<section class="pe-cover">{cover}</section>')
sections.append(f'<section class="pe-page">{front}</section>')

for name in ORDER:
    html = read(name)
    sections.append(f'<section class="pe-page">{container_inner(html)}</section>')

sections.append(f'<section class="pe-page">{food}</section>')

body = "\n".join(sections)

# Point all image references at the downscaled print copies
print_img_dir = build_print_images()
body = body.replace("images/", f"{print_img_dir}/")

# Replace the cover background-image with a real <img> (data URI) so it
# always paints in headless print — CSS background-images are unreliable there.
import base64
hero = HERE / print_img_dir / "japan-family-hero.jpg"
b64 = base64.b64encode(hero.read_bytes()).decode()
body = re.sub(
    r'<div class="cover-bg"[^>]*></div>',
    f'<div class="cover-bg"><img src="data:image/jpeg;base64,{b64}" '
    f'style="position:absolute;inset:0;width:100%;height:100%;'
    f'object-fit:cover;border-radius:0;"></div>',
    body,
)

# ── Print-edition wrapper with print CSS ──────────────────────
doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Japan Winter Adventure 2025 — Print Edition</title>
<link rel="stylesheet" href="styles.css">
<style>
  @page {{ size: A4; margin: 14mm 12mm; }}
  * {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  body {{ background: var(--parchment); }}
  body::before {{ opacity: 0.5; }}
  /* Each section starts on a fresh page */
  .pe-page {{ break-before: page; padding-top: 4mm; }}
  .pe-cover {{ break-after: page; }}
  /* Cover fills the first printed page */
  .pe-cover .cover {{
    min-height: 262mm; height: 262mm; border-radius: 0;
    margin: -14mm -12mm 0; padding: 24mm 20mm;
  }}
  /* Keep visual blocks intact across page breaks */
  .card, .photo-content, .city-feature, .excursion-item,
  .pull-quote, .photo-slot, .photo-grid {{ break-inside: avoid; }}
  .section-head {{ break-after: avoid; }}
  /* Tidy spacing for print */
  .container {{ max-width: 100%; padding: 0; }}
  .hero {{ padding-top: 0; }}
  /* Hide interactive-only bits */
  .topbar, .nav-row, .cover-scroll {{ display: none !important; }}
  .pe-cover .cover-scroll {{ display: none !important; }}
</style>
</head>
<body>
{body}
<footer>
  <div class="mark">— Japan Winter Adventure, 2025 —</div>
  <div>Munasinghe Family Travel Journal · 28 Jan – 7 Feb 2025</div>
</footer>
</body>
</html>
"""

out_html = HERE / "print-edition.html"
out_html.write_text(doc, encoding="utf-8")
print(f"Wrote {out_html}")

# ── Render to PDF with headless Chrome/Edge ───────────────────
browsers = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]
browser = next((b for b in browsers if Path(b).exists()), None)
if not browser:
    print("No Chrome/Edge found — print-edition.html written, render manually.")
    sys.exit(0)

pdf_path = HERE / "japan-trip-2025.pdf"
if pdf_path.exists():
    pdf_path.unlink()
cmd = [
    browser,
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--no-pdf-header-footer",
    "--user-data-dir=" + str(HERE / ".pdf-profile"),
    f"--print-to-pdf={pdf_path}",
    out_html.as_uri(),
]
print("Rendering PDF with:", Path(browser).name)
subprocess.run(cmd, timeout=180)
if pdf_path.exists():
    print(f"Wrote {pdf_path} ({pdf_path.stat().st_size // 1024} KB)")
else:
    print("ERROR: PDF was not produced.")
    sys.exit(1)
