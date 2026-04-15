"""
generate_icon.py – Create icon.ico matching the mobile app launcher icon.

Renders the same gold spade on dark-purple background used by the Android
launcher (see wizard_flutter/.../ic_launcher_foreground.xml) into a multi-size
Windows .ico file.  Can be run standalone:

    python generate_icon.py

Called automatically from build.sh before PyInstaller is invoked.
"""
from __future__ import annotations

import os
import sys


def _draw_icon(size: int):
    from PIL import Image, ImageDraw

    bg = (13, 13, 26, 255)       # #0D0D1A – dark purple background
    fg = (201, 168, 76, 255)     # #C9A84C – gold accent

    img = Image.new("RGBA", (size, size), bg)
    draw = ImageDraw.Draw(img)

    # Viewport: 108x108 (from the SVG).  Pre-computed spade polygon that
    # approximates the curved svg path – uniform-scale to the target size.
    def s(x, y):
        return (x / 108.0 * size, y / 108.0 * size)

    # Spade-ish silhouette plus a little stem at the bottom.
    spade = [
        s(54, 22),
        s(44, 32), s(36, 42), s(30, 52), s(30, 58),
        s(32, 66), s(38, 70), s(45, 70),
        s(43, 74), s(40, 78), s(35, 81), s(32, 82),
        s(76, 82),
        s(73, 81), s(68, 78), s(65, 74), s(63, 70),
        s(70, 70), s(76, 66), s(78, 58),
        s(78, 52), s(72, 42), s(64, 32),
    ]
    draw.polygon(spade, fill=fg)
    return img


def build(out_path: str) -> None:
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print("[!] Pillow is required to generate icon.ico (pip install Pillow)",
              file=sys.stderr)
        sys.exit(1)

    sizes = (16, 24, 32, 48, 64, 128, 256)
    images = [_draw_icon(s) for s in sizes]
    images[0].save(out_path, format="ICO",
                   sizes=[(im.width, im.height) for im in images])
    print(f"[+] Wrote {out_path}")


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    build(os.path.join(here, "icon.ico"))
