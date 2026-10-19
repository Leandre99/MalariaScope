"""Engine and API tests on a committed sample field (no dataset download needed)."""
import sys
from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from api.index import app  # noqa: E402
from malariascope.analysis import WORK_SIZE, analyze  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "field.jpg"
client = TestClient(app)


def load_fixture():
    return cv2.imread(str(FIXTURE), cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)


def test_result_shape_and_detections():
    res = analyze(load_fixture())
    assert max(res["width"], res["height"]) == WORK_SIZE
    assert set(res) >= {"width", "height", "quality", "wbc", "parasites", "ms"}
    assert set(res["quality"]) == {"ok", "focusScore", "reason"}
    assert res["quality"]["ok"] is True
    # The expert marked 9 WBCs and 79 parasites on this field.
    assert 6 <= len(res["wbc"]) <= 12
    assert len(res["parasites"]) > 20
    for mark in res["wbc"] + res["parasites"]:
        assert set(mark) == {"x", "y", "r"}
        assert 0 <= mark["x"] <= res["width"] and 0 <= mark["y"] <= res["height"]


def test_api_health():
    assert client.get("/api/health").json() == {"ok": True}


def test_api_analyze_image():
    data = FIXTURE.read_bytes()
    r = client.post("/api/analyze", files={"image": ("field.jpg", data, "image/jpeg")})
    assert r.status_code == 200
    assert len(r.json()["wbc"]) > 0


def test_api_rejects_non_image():
    r = client.post("/api/analyze", files={"image": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 400
    assert r.json() == {"error": "not_an_image"}


def test_blank_image_has_no_cells():
    blank = np.full((1200, 1600, 3), 230, np.uint8)
    assert analyze(blank)["quality"]["reason"] == "no_cells"
