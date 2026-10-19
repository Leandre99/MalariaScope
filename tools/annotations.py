"""Read NLM thick-smear ground truth.

Each image `<patient>/<name>.jpg` has `GT_updated/<patient>/<name>.txt`:

    <n_objects>,<width>,<height>
    <id>,Parasite,<comment>,Circle,2,<cx>,<cy>,<edge_x>,<edge_y>
    <id>,White_Blood_Cell,<comment>,Point,1,<x>,<y>

Coordinates are in the original image pixels. We rescale them to the
analysis resolution (long side = 1600 px) used by the engine.
"""
import math
import sys

import cv2
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "nlm_thick"

sys.path.insert(0, str(ROOT))
from malariascope.analysis import WORK_SIZE, to_work_size  # noqa: E402


UPLOAD_JPEG_QUALITY = 95  # what the page sends after resizing (public/app.js)


def load_image(path):
    """Load the field the way the app receives it: resized to analysis size and
    JPEG-compressed like the page's upload (tiny parasite dots are sensitive to it).
    EXIF rotation is ignored: expert coordinates use the raw (landscape) pixel grid."""
    img = cv2.imread(str(path), cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
    img = to_work_size(img)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, UPLOAD_JPEG_QUALITY])
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


@dataclass
class Truth:
    image: Path
    patient: str
    width: int
    height: int
    wbc: list = field(default_factory=list)        # [(x, y)] at WORK_SIZE scale
    parasites: list = field(default_factory=list)  # [(x, y, r)] at WORK_SIZE scale


def read_truth(image_path):
    image_path = Path(image_path)
    patient = image_path.parent.name
    gt = DATA_DIR / "GT_updated" / patient / (image_path.stem + ".txt")
    lines = gt.read_text().strip().splitlines()
    _, w, h = (int(float(v)) for v in lines[0].split(","))
    scale = WORK_SIZE / max(w, h)
    t = Truth(image_path, patient, w, h)
    for line in lines[1:]:
        cols = line.split(",")
        label = cols[1]
        coords = [float(v) for v in cols[5:]]
        x, y = coords[0] * scale, coords[1] * scale
        if label == "White_Blood_Cell":
            t.wbc.append((x, y))
        elif label == "Parasite":
            r = math.dist(coords[0:2], coords[2:4]) * scale if len(coords) >= 4 else 4.0
            t.parasites.append((x, y, r))
    return t


def all_images(patients=None):
    """Annotated images on disk, grouped by patient: {patient: [Path]}."""
    out = {}
    for img in sorted(DATA_DIR.glob("*/*.jpg")):
        if patients and img.parent.name not in patients:
            continue
        gt = DATA_DIR / "GT_updated" / img.parent.name / (img.stem + ".txt")
        if gt.exists():
            out.setdefault(img.parent.name, []).append(img)
    return out


if __name__ == "__main__":
    for patient, imgs in all_images().items():
        truths = [read_truth(p) for p in imgs]
        wbc = sum(len(t.wbc) for t in truths)
        par = sum(len(t.parasites) for t in truths)
        print(f"{patient:12s} fields={len(imgs):3d} wbc={wbc:4d} parasites={par:5d}")
