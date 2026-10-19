"""MalariaScope field analysis engine (OpenCV).

Pure functions: no web code. Takes one thick-smear field photo and returns
the white blood cells and parasites found, plus a quality verdict.
"""
import cv2
import numpy as np

# Analysis resolution: long side in pixels. The page resizes uploads to this too.
WORK_SIZE = 1600


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
