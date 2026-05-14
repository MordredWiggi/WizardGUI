"""
generate_icon.py – Build icon.ico from the shared trimmed AppIcon source.

Reads images/AppIcon_trimmed.png (the pre-cleaned, transparent-background
PNG produced by images/_trim_appicon.py) and writes a multi-size Windows
.ico for the PyInstaller build.  Can be run standalone:

    python generate_icon.py

Called automatically from build.sh before PyInstaller is invoked.
"""

from __future__ import annotations

import os
import sys


def build(out_path: str, src_path: str) -> None:
    try:
        from PIL import Image
    except ImportError:
        print(
            "[!] Pillow is required to generate icon.ico (pip install Pillow)",
            file=sys.stderr,
        )
        sys.exit(1)

    if not os.path.isfile(src_path):
        print(
            f"[!] {src_path} not found. Run images/_trim_appicon.py first to "
            "regenerate the trimmed source.",
            file=sys.stderr,
        )
        sys.exit(1)

    img = Image.open(src_path).convert("RGBA")
    # Ensure square so Pillow's downscaling produces square ICO entries.
    if img.size[0] != img.size[1]:
        side = max(img.size)
        square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        square.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
        img = square

    base = img.resize((256, 256), Image.LANCZOS)
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    base.save(out_path, format="ICO", sizes=sizes)
    print(f"[+] Wrote {out_path}")


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(here, ".."))
    default_src = os.path.join(repo_root, "images", "AppIcon_trimmed.png")
    src = sys.argv[1] if len(sys.argv) > 1 else default_src
    build(os.path.join(here, "icon.ico"), src)
