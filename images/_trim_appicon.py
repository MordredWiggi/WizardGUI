"""Trim AppIcon.png by saturation-based border flood-fill.

Background = white halo + drop-shadow under the icon. Both are near-
grayscale (R≈G≈B). The icon's gold rim is color-saturated (R clearly >
B). We BFS from every border pixel, expanding ONLY across near-grayscale
neighbours. That removes background of any brightness without ever
touching a colored rim pixel, even where anti-aliasing makes the rim very
light at the top.
"""
from __future__ import annotations

import os
from collections import deque

from PIL import Image
import numpy as np


HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "AppIcon.png")
DST = os.path.join(HERE, "AppIcon_trimmed.png")

# A pixel is treated as background-candidate iff max(R,G,B)-min(R,G,B)
# (the "saturation") is at most this value. White has sat 0, gray shadow
# has sat 0–5, gold rim has sat 60+. 25 leaves safe headroom.
SAT_THRESH = 40


def main() -> None:
    img = Image.open(SRC).convert("RGBA")
    w, h = img.size
    arr = np.array(img)  # shape (h, w, 4), uint8

    rgb = arr[:, :, :3].astype(np.int16)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    candidate = sat <= SAT_THRESH  # bool (h, w)

    # BFS from every border pixel that is a candidate.
    visited = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()

    def push(x: int, y: int) -> None:
        if not visited[y, x] and candidate[y, x]:
            visited[y, x] = True
            q.append((x, y))

    for x in range(w):
        push(x, 0)
        push(x, h - 1)
    for y in range(h):
        push(0, y)
        push(w - 1, y)

    while q:
        x, y = q.popleft()
        if x > 0:
            push(x - 1, y)
        if x + 1 < w:
            push(x + 1, y)
        if y > 0:
            push(x, y - 1)
        if y + 1 < h:
            push(x, y + 1)

    # Set alpha=0 on every background pixel.
    arr[visited, 3] = 0

    out = Image.fromarray(arr, mode="RGBA")
    bbox = out.getbbox()
    if bbox is None:
        raise RuntimeError("nothing left after flood-fill")
    cropped = out.crop(bbox)

    side = max(cropped.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(cropped, ((side - cropped.width) // 2, (side - cropped.height) // 2))
    square.save(DST, format="PNG")
    print(f"[+] Wrote {DST} ({square.size[0]}x{square.size[1]})  bbox={bbox}")


if __name__ == "__main__":
    main()
