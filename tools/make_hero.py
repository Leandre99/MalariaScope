"""Render the start-screen picture: a real held-out sample field with
MalariaScope's own detections drawn on it (not hand-placed decoration).

Usage: python tools/make_hero.py   -> public/img/hero.jpg
"""
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from malariascope.analysis import analyze, field_of_view, load_params  # noqa: E402

SOURCE = ROOT / "public" / "samples" / "field-03.jpg"
OUT = ROOT / "public" / "img" / "hero.jpg"
SIZE = 960
BLUE, RED = (235, 99, 37), (38, 38, 220)  # BGR of #2563EB / #DC2626


def main():
    img = cv2.imread(str(SOURCE), cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
    res = analyze(img)
    # Draw at 2x then downsample for smooth rings.
    big = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    for m in res["wbc"]:
        cv2.circle(big, (round(m["x"] * 2), round(m["y"] * 2)), round(m["r"] * 2), BLUE, 5, cv2.LINE_AA)
    for m in res["parasites"]:
        cv2.circle(big, (round(m["x"] * 2), round(m["y"] * 2)), max(14, round(m["r"] * 2)), RED, 4, cv2.LINE_AA)
    # Crop to the microscope disc so the picture is the field itself.
    mask = field_of_view(img, load_params())
    ys, xs = np.nonzero(mask)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    half = max(xs.max() - xs.min(), ys.max() - ys.min()) / 2 + 20
    x0, y0 = int(max(0, (cx - half) * 2)), int(max(0, (cy - half) * 2))
    x1, y1 = int(min(big.shape[1], (cx + half) * 2)), int(min(big.shape[0], (cy + half) * 2))
    crop = cv2.resize(big[y0:y1, x0:x1], (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT), crop, [cv2.IMWRITE_JPEG_QUALITY, 86])
    print(f"{OUT}: {len(res['wbc'])} WBC, {len(res['parasites'])} parasites marked")


if __name__ == "__main__":
    main()
