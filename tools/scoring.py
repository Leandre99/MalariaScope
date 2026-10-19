"""Compare engine detections with expert annotations (shared by tune/evaluate)."""
import math

import numpy as np

MATCH_RADIUS_WBC = 25    # px at WORK_SIZE
MATCH_RADIUS_PAR = 10


def match(found, truth_pts, radius):
    """Greedy one-to-one matching by distance. Returns true positives."""
    if not found or not truth_pts:
        return 0
    pairs = []
    for i, f in enumerate(found):
        for j, t in enumerate(truth_pts):
            d = math.dist((f["x"], f["y"]), t[:2])
            if d <= radius:
                pairs.append((d, i, j))
    pairs.sort()
    used_f, used_t, tp = set(), set(), 0
    for _, i, j in pairs:
        if i in used_f or j in used_t:
            continue
        used_f.add(i)
        used_t.add(j)
        tp += 1
    return tp


def score_image(result, truth):
    tp_w = match(result["wbc"], truth.wbc, MATCH_RADIUS_WBC)
    tp_p = match(result["parasites"], truth.parasites, MATCH_RADIUS_PAR)
    return {
        "expert": {"wbc": len(truth.wbc), "parasites": len(truth.parasites)},
        "ours": {"wbc": len(result["wbc"]), "parasites": len(result["parasites"])},
        "tp": {"wbc": tp_w, "parasites": tp_p},
    }


def summarize(rows):
    """Aggregate precision/recall and count errors over scored images."""
    out = {}
    for kind in ("wbc", "parasites"):
        tp = sum(r["tp"][kind] for r in rows)
        ours = sum(r["ours"][kind] for r in rows)
        expert = sum(r["expert"][kind] for r in rows)
        abs_err = [abs(r["ours"][kind] - r["expert"][kind]) for r in rows]
        out[kind] = {
            "expertTotal": expert,
            "oursTotal": ours,
            "precision": round(tp / ours, 3) if ours else 0.0,
            "recall": round(tp / expert, 3) if expert else 0.0,
            "meanAbsCountError": round(float(np.mean(abs_err)), 1) if rows else 0.0,
            "totalCountError": round((ours - expert) / expert, 3) if expert else 0.0,
        }
    return out
