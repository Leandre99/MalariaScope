"""Tune the parasite detector's thresholds on the TUNING patients only.

Strategy: for each black-hat kernel/threshold pair, segment candidate dots once
per image and record their features (area, circularity, saturation). The other
thresholds are then just filters over those features, so the grid search is fast.
Objective: parasite F1 (point matching within MATCH_RADIUS_PAR), which rewards
finding the expert's parasites without flooding the field with false marks.

Usage: python tools/tune.py      -> writes malariascope/params.json
"""
import itertools
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from annotations import all_images, load_image, read_truth  # noqa: E402
from malariascope.analysis import (  # noqa: E402
    DEFAULT_PARAMS, PARAMS_PATH, analyze, detect_wbc, field_of_view, focus_score,
)
from scoring import MATCH_RADIUS_PAR, score_image, summarize  # noqa: E402
from split import TUNING  # noqa: E402

KERNELS = [9, 11, 13]
THRESHOLDS = [36, 48, 64, 80, 100]
AREA_MIN = [3, 5, 8]
AREA_MAX = [25, 40, 70]
SAT_MIN = [50, 70, 90, 110, 130]
CIRC_MIN = [0.45, 0.55, 0.65, 0.75]
DARKEST_MAX = [90, 110, 130, 150, 255]


def candidates(img, hsv, mask, wbc_blob, kernel, thr, p):
    """Every dark dot above `thr`, with its features and whether it matches the expert."""
    g = img[..., 1]
    resp = cv2.morphologyEx(255 - g, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel, kernel)))
    spots = ((resp >= thr) & (mask > 0)).astype(np.uint8) * 255
    e = p["wbc_exclusion"] * 2 + 1
    spots[cv2.dilate(wbc_blob, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (e, e))) > 0] = 0
    n, labels, stats, cents = cv2.connectedComponentsWithStats(spots)
    if n <= 1:
        return np.zeros((0, 6))
    areas = stats[1:, cv2.CC_STAT_AREA].astype(float)
    w, h = stats[1:, cv2.CC_STAT_WIDTH], stats[1:, cv2.CC_STAT_HEIGHT]
    circ = areas / (np.pi * (np.maximum(w, h) / 2) ** 2)
    sat_sum = np.bincount(labels.ravel(), weights=hsv[..., 1].ravel().astype(float), minlength=n)[1:]
    sat = sat_sum / areas
    darkest = np.full(n, 255.0)
    inside = labels > 0
    np.minimum.at(darkest, labels[inside], g[inside].astype(float))
    return np.column_stack([areas, circ, sat, cents[1:, 0], cents[1:, 1], darkest[1:]])


def match_flags(cands, truth_pts):
    """Approximate one-to-one matching: each expert point claims its nearest candidate."""
    flags = np.zeros(len(cands), bool)
    if len(cands) == 0 or not truth_pts:
        return flags
    xy = cands[:, 3:5]
    for tx, ty, _ in truth_pts:
        d = np.hypot(xy[:, 0] - tx, xy[:, 1] - ty)
        j = int(np.argmin(d))
        if d[j] <= MATCH_RADIUS_PAR:
            flags[j] = True
    return flags


def main():
    p0 = dict(DEFAULT_PARAMS)
    images = [img for imgs in all_images(TUNING).values() for img in imgs]
    print(f"tuning on {len(images)} fields from {len(TUNING)} patients")
    prepared = []
    focus = []
    for path in images:
        img = load_image(path)
        mask = field_of_view(img, p0)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        _, wbc_blob = detect_wbc(hsv, mask, p0)
        focus.append(focus_score(img, mask))
        prepared.append((img, hsv, mask, wbc_blob, read_truth(path)))
    print(f"focus score on real fields: min {min(focus):.1f}, median {np.median(focus):.1f}")

    best = None
    for kernel, thr in itertools.product(KERNELS, THRESHOLDS):
        per_image = []
        for img, hsv, mask, wbc_blob, truth in prepared:
            c = candidates(img, hsv, mask, wbc_blob, kernel, thr, p0)
            per_image.append((c, match_flags(c, truth.parasites), len(truth.parasites)))
        expert = sum(n for _, _, n in per_image)
        for amin, amax, smin, cmin, dmax in itertools.product(AREA_MIN, AREA_MAX, SAT_MIN, CIRC_MIN, DARKEST_MAX):
            tp = found = 0
            for c, flags, _ in per_image:
                keep = ((c[:, 0] >= amin) & (c[:, 0] <= amax) & (c[:, 2] >= smin)
                        & (c[:, 1] >= cmin) & (c[:, 5] <= dmax))
                found += int(keep.sum())
                tp += int((keep & flags).sum())
            if not found:
                continue
            precision, recall = tp / found, tp / expert
            f1 = 2 * precision * recall / (precision + recall) if tp else 0
            if not best or f1 > best[0]:
                best = (f1, precision, recall, dict(
                    par_tophat_kernel=kernel, par_tophat_min=thr, par_area_min=amin,
                    par_area_max=amax, par_sat_min=smin, par_circularity_min=cmin,
                    par_darkest_max=dmax))
        print(f"kernel {kernel:2d} thr {thr:2d}: best F1 so far {best[0]:.3f}")

    f1, precision, recall, params = best
    # Flag blur well below the sharpest real fields, so real photos aren't rejected.
    params["focus_min"] = round(min(4.0, 0.5 * min(focus)), 2)
    print(f"best approx F1 {f1:.3f} (precision {precision:.3f}, recall {recall:.3f})")
    print(json.dumps(params, indent=2))
    PARAMS_PATH.write_text(json.dumps(params, indent=2) + "\n")

    # Exact check with the real engine on the tuning set.
    rows = []
    for img, _, _, _, truth in prepared:
        rows.append(score_image(analyze(img), truth))
    print("exact on tuning set:", json.dumps(summarize(rows), indent=1))


if __name__ == "__main__":
    main()
