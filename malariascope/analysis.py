"""MalariaScope field analysis engine (OpenCV).

Pure functions: no web code. Takes one Giemsa-stained thick-smear field photo
(smartphone through a microscope eyepiece) and returns the white blood cells
(WBC) and parasites found, plus a quality verdict.

Pipeline (see devpost/spec.md > Field analysis engine):
  1. resize to WORK_SIZE        4. WBC: large, saturated purple blobs
  2. field-of-view disc mask    5. parasites: small dark dots (black-hat filter)
  3. focus score (Laplacian)    6. quality verdict
"""
import json
import time
from pathlib import Path

import cv2
import numpy as np

# Analysis resolution: long side in pixels. The page resizes uploads to this too.
WORK_SIZE = 1600

PARAMS_PATH = Path(__file__).with_name("params.json")

DEFAULT_PARAMS = {
    "fov_threshold": 40,        # grey level separating the bright disc from the black surround
    "fov_erode": 12,            # px trimmed off the disc edge (vignetting / lens rim)
    "focus_min": 4.0,           # variance of Laplacian below this = out of focus
    "wbc_sat_min": 150,         # HSV saturation of WBC nuclei (very saturated purple)
    "wbc_val_max": 200,         # ... and not too bright
    "wbc_area_min": 250,        # px^2 at WORK_SIZE (a WBC nucleus is ~25-40 px across)
    "wbc_area_max": 2600,
    "wbc_exclusion": 8,         # px around a WBC where dots are not counted as parasites
    "par_tophat_kernel": 13,    # black-hat structuring element size (px)
    "par_tophat_min": 28,       # minimum black-hat response for a parasite dot
    "par_area_min": 4,
    "par_area_max": 90,
    "par_sat_min": 40,          # parasite chromatin is purple, not grey debris
    "par_circularity_min": 0.35,
    "no_cells_stain_frac": 0.0005,
}


def load_params():
    params = dict(DEFAULT_PARAMS)
    if PARAMS_PATH.exists():
        params.update(json.loads(PARAMS_PATH.read_text()))
    return params


def to_work_size(img):
    """Resize so the long side is WORK_SIZE (never upscale)."""
    h, w = img.shape[:2]
    scale = WORK_SIZE / max(h, w)
    if scale >= 1:
        return img
    return cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)


def decode_image(data: bytes):
    """Bytes (JPEG/PNG) -> BGR image, or None if unreadable."""
    arr = np.frombuffer(data, dtype=np.uint8)
    if arr.size == 0:
        return None
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def field_of_view(img, p):
    """Mask of the bright microscope disc. Falls back to the whole image
    when there is no dark surround (e.g. a cropped photo)."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, bright = cv2.threshold(gray, p["fov_threshold"], 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask = np.zeros_like(gray)
    if contours:
        biggest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(biggest) > 0.1 * gray.size:
            cv2.drawContours(mask, [biggest], -1, 255, cv2.FILLED)
    if not mask.any():
        mask[:] = 255
    k = p["fov_erode"] * 2 + 1
    return cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))


def focus_score(img, mask):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return float(lap[mask > 0].var()) if mask.any() else 0.0


def detect_wbc(hsv, mask, p):
    """WBC nuclei: large, strongly saturated, dark purple blobs."""
    s, v = hsv[..., 1], hsv[..., 2]
    blob = ((s >= p["wbc_sat_min"]) & (v <= p["wbc_val_max"]) & (mask > 0)).astype(np.uint8) * 255
    blob = cv2.morphologyEx(blob, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    blob = cv2.morphologyEx(blob, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(blob)
    cells = []
    single_area = (p["wbc_area_min"] + p["wbc_area_max"]) / 3
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < p["wbc_area_min"]:
            continue
        x, y = centroids[i]
        r = max(stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]) / 2 + 4
        if area <= p["wbc_area_max"]:
            cells.append({"x": round(float(x), 1), "y": round(float(y), 1), "r": round(float(r), 1)})
        else:
            # Touching cells: split the clump by area into k marks along its blob pixels.
            k = max(2, round(area / single_area))
            ys, xs = np.nonzero(labels == i)
            pts = np.float32(np.column_stack([xs, ys]))
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
            _, _, centers = cv2.kmeans(pts, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
            rk = float(np.sqrt(area / k / np.pi)) + 4
            for cx, cy in centers:
                cells.append({"x": round(float(cx), 1), "y": round(float(cy), 1), "r": round(rk, 1)})
    return cells, blob


def detect_parasites(img, hsv, mask, wbc_blob, p):
    """Parasites: small dark dots in the background (ring forms / chromatin)."""
    g = img[..., 1]
    k = p["par_tophat_kernel"] | 1
    response = cv2.morphologyEx(255 - g, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    spots = ((response >= p["par_tophat_min"]) & (mask > 0)).astype(np.uint8) * 255
    e = p["wbc_exclusion"] * 2 + 1
    near_wbc = cv2.dilate(wbc_blob, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (e, e)))
    spots[near_wbc > 0] = 0
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(spots)
    sat = hsv[..., 1]
    found = []
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        if not p["par_area_min"] <= area <= p["par_area_max"]:
            continue
        w, h = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
        circularity = area / (np.pi * (max(w, h) / 2) ** 2)
        if circularity < p["par_circularity_min"]:
            continue
        x0, y0 = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP]
        region = labels[y0:y0 + h, x0:x0 + w] == i
        if sat[y0:y0 + h, x0:x0 + w][region].mean() < p["par_sat_min"]:
            continue
        x, y = centroids[i]
        found.append({"x": round(float(x), 1), "y": round(float(y), 1), "r": round(float(max(w, h) / 2 + 5), 1)})
    return found


def analyze(img, params=None):
    """Analyse one field. `img` is a BGR image (any size).

    Returns the API's analysis result:
      {width, height, quality: {ok, focusScore, reason}, wbc: [...], parasites: [...], ms}
    """
    started = time.perf_counter()
    p = params or load_params()
    img = to_work_size(img)
    mask = field_of_view(img, p)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    focus = focus_score(img, mask)
    wbc, wbc_blob = detect_wbc(hsv, mask, p)
    parasites = detect_parasites(img, hsv, mask, wbc_blob, p)

    reason = None
    stain_frac = (wbc_blob > 0).sum() / max(1, (mask > 0).sum())
    if not wbc and stain_frac < p["no_cells_stain_frac"] and len(parasites) < 3:
        reason = "no_cells"
    elif focus < p["focus_min"]:
        reason = "blur"

    return {
        "width": int(img.shape[1]),
        "height": int(img.shape[0]),
        "quality": {"ok": reason is None, "focusScore": round(focus, 2), "reason": reason},
        "wbc": wbc,
        "parasites": parasites,
        "ms": round((time.perf_counter() - started) * 1000),
    }
