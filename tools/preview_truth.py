"""Draw the expert annotations on one image (blue = WBC, red = parasite).

Usage: python tools/preview_truth.py data/nlm_thick/<patient>/<image>.jpg [out.png]
"""
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from annotations import load_image, read_truth  # noqa: E402

BLUE, RED = (235, 99, 37), (38, 38, 220)  # BGR of #2563EB and #DC2626


def main(path, out=None):
    truth = read_truth(path)
    img = load_image(path)
    for x, y in truth.wbc:
        cv2.circle(img, (round(x), round(y)), 22, BLUE, 2)
    for x, y, r in truth.parasites:
        cv2.circle(img, (round(x), round(y)), max(6, round(r) + 3), RED, 2)
    out = out or Path(path).with_suffix(".truth.png").name
    cv2.imwrite(str(out), img)
    print(f"{out}: {len(truth.wbc)} WBC, {len(truth.parasites)} parasites, size {img.shape[1]}x{img.shape[0]}")


if __name__ == "__main__":
    main(*sys.argv[1:])
