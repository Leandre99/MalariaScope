"""Copy one held-out patient's fields into public/samples/ for "Try a sample slide".

Images are resized to the analysis size (1600 px long side), saved without
EXIF rotation so they match the expert's coordinate grid, and listed in
manifest.json in capture order. The real analyser runs on them in the app.

Usage: python tools/make_samples.py
"""
import json
import sys
from pathlib import Path

import cv2

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
from annotations import UPLOAD_JPEG_QUALITY, all_images, read_truth  # noqa: E402
from malariascope.analysis import to_work_size  # noqa: E402
from split import HELD_OUT, SAMPLE_PATIENT  # noqa: E402

OUT = ROOT / "public" / "samples"


def main():
    assert SAMPLE_PATIENT in HELD_OUT, "the sample slide must come from a held-out patient"
    paths = all_images([SAMPLE_PATIENT])[SAMPLE_PATIENT]
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.jpg"):
        old.unlink()
    fields, wbc, par = [], 0, 0
    for i, path in enumerate(paths, 1):
        name = f"field-{i:02d}.jpg"
        # Encoded once at the upload quality: the app sends these files untouched,
        # so the analyser sees exactly what the evaluation measured.
        raw = cv2.imread(str(path), cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
        cv2.imwrite(str(OUT / name), to_work_size(raw), [cv2.IMWRITE_JPEG_QUALITY, UPLOAD_JPEG_QUALITY])
        truth = read_truth(path)
        wbc += len(truth.wbc)
        par += len(truth.parasites)
        fields.append(name)
    manifest = {
        "reference": "SAMPLE-" + SAMPLE_PATIENT,
        "source": "NLM Thick Smears 150, patient " + SAMPLE_PATIENT + " (held out from tuning)",
        "expert": {"fields": len(fields), "wbc": wbc, "parasites": par},
        "fields": fields,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    size = sum(f.stat().st_size for f in OUT.glob("*.jpg")) / 1e6
    print(f"{len(fields)} fields, expert {wbc} WBC / {par} parasites, {size:.1f} MB -> {OUT}")


if __name__ == "__main__":
    main()
