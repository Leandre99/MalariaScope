"""Measure MalariaScope against the expert on HELD-OUT patients only.

Writes public/evaluation/evaluation.json and failure example images used by
the "How accurate is it?" screen. Explanations for failure examples are written
by a person after looking at the images, in tools/failure_notes.json.

Usage: python tools/evaluate.py
"""
import json
import sys
from pathlib import Path

import cv2

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
from annotations import all_images, load_image, read_truth  # noqa: E402
from malariascope.analysis import analyze, load_params  # noqa: E402
from scoring import MATCH_RADIUS_PAR, MATCH_RADIUS_WBC, score_image, summarize  # noqa: E402
from split import HELD_OUT, TUNING  # noqa: E402

OUT_DIR = ROOT / "public" / "evaluation"
NOTES = HERE / "failure_notes.json"
WBC_PER_UL = 8000
N_FAILURES = 3


def density(parasites, wbc):
    return round(parasites * WBC_PER_UL / wbc) if wbc else None


def draw_comparison(img, res, truth, path):
    """Ours = circles (blue WBC, red parasites); expert = small yellow crosses."""
    out = img.copy()
    for m in res["wbc"]:
        cv2.circle(out, (round(m["x"]), round(m["y"])), round(m["r"]), (235, 99, 37), 2)
    for m in res["parasites"]:
        cv2.circle(out, (round(m["x"]), round(m["y"])), max(7, round(m["r"])), (38, 38, 220), 2)
    for x, y in truth.wbc:
        cv2.drawMarker(out, (round(x), round(y)), (0, 220, 255), cv2.MARKER_CROSS, 18, 2)
    for x, y, _ in truth.parasites:
        cv2.drawMarker(out, (round(x), round(y)), (0, 220, 255), cv2.MARKER_CROSS, 10, 2)
    out = cv2.resize(out, (out.shape[1] // 2, out.shape[0] // 2), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(path), out, [cv2.IMWRITE_JPEG_QUALITY, 82])


def main():
    params = load_params()
    notes = json.loads(NOTES.read_text()) if NOTES.exists() else {}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows, patients, cache = [], [], {}
    for patient, paths in all_images(HELD_OUT).items():
        p_rows = []
        for path in paths:
            img = load_image(path)
            truth = read_truth(path)
            res = analyze(img, params)
            row = score_image(res, truth)
            row["id"] = f"{patient}/{path.stem}"
            p_rows.append(row)
            cache[row["id"]] = (img, res, truth)
        rows += p_rows
        e_wbc = sum(r["expert"]["wbc"] for r in p_rows)
        e_par = sum(r["expert"]["parasites"] for r in p_rows)
        o_wbc = sum(r["ours"]["wbc"] for r in p_rows)
        o_par = sum(r["ours"]["parasites"] for r in p_rows)
        patients.append({
            "patient": patient, "fields": len(p_rows),
            "expert": {"wbc": e_wbc, "parasites": e_par, "density": density(e_par, e_wbc)},
            "ours": {"wbc": o_wbc, "parasites": o_par, "density": density(o_par, o_wbc)},
        })
        print(f"{patient}: expert {density(e_par, e_wbc)}/µL vs ours {density(o_par, o_wbc)}/µL")

    # Failure examples: the worst under-counts and the worst over-count, so both
    # kinds of mistake (missed parasites, debris marked as parasites) are shown.
    by_error = sorted(rows, key=lambda r: r["ours"]["parasites"] - r["expert"]["parasites"])
    worst = by_error[:N_FAILURES - 1] + by_error[-1:]
    failures = []
    for i, r in enumerate(worst, 1):
        img, res, truth = cache[r["id"]]
        name = f"failure-{i}.jpg"
        draw_comparison(img, res, truth, OUT_DIR / name)
        failures.append({"id": r["id"], "image": f"evaluation/{name}", "expert": r["expert"],
                         "ours": r["ours"], "note": notes.get(r["id"], "")})

    for r in rows:
        r["precision"] = {k: round(r["tp"][k] / r["ours"][k], 3) if r["ours"][k] else None for k in ("wbc", "parasites")}
        r["recall"] = {k: round(r["tp"][k] / r["expert"][k], 3) if r["expert"][k] else None for k in ("wbc", "parasites")}

    result = {
        "dataset": "NLM Thick Smears 150 (P. falciparum), smartphone microscopy, Chittagong Bangladesh",
        "citation": "Yang F. et al., Deep Learning for Smartphone-Based Malaria Parasite Detection in Thick Blood Smears, IEEE J Biomed Health Inform, 2020",
        "tuningPatients": TUNING,
        "heldOutPatients": HELD_OUT,
        "matchRadiusPx": {"wbc": MATCH_RADIUS_WBC, "parasites": MATCH_RADIUS_PAR, "imageLongSide": 1600},
        "summary": summarize(rows),
        "patients": patients,
        "images": rows,
        "failures": failures,
    }
    (OUT_DIR / "evaluation.json").write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result["summary"], indent=1))
    for f in failures:
        print("failure:", f["id"], f["expert"], f["ours"])


if __name__ == "__main__":
    main()
