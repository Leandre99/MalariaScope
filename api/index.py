"""MalariaScope analyser API (FastAPI).

POST /api/analyze  multipart field "image" -> analysis result JSON
GET  /api/health   -> {"ok": true}

Run locally:  uvicorn api.index:app --reload   (also serves public/ at /)
On Vercel:    public/ is served as static files; this file runs as a Python function.
"""
import sys
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from malariascope.analysis import analyze, decode_image  # noqa: E402

MAX_UPLOAD_BYTES = 4_000_000  # Vercel rejects request bodies over 4.5 MB

app = FastAPI(title="MalariaScope")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/analyze")
async def analyze_field(image: UploadFile = File(...)):
    data = await image.read()
    if len(data) > MAX_UPLOAD_BYTES:
        return JSONResponse({"error": "too_large"}, status_code=413)
    img = decode_image(data)
    if img is None:
        return JSONResponse({"error": "not_an_image"}, status_code=400)
    return analyze(img)


# Local development: serve the page from the same server. On Vercel the
# public/ folder is served by the CDN before requests reach this function.
if (ROOT / "public").is_dir():
    app.mount("/", StaticFiles(directory=ROOT / "public", html=True), name="public")
