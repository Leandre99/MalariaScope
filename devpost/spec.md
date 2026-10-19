---
doc: spec
status: approved
---

# MalariaScope — Technical Spec

## How This Works, In Plain Language
MalariaScope has two halves.

- **The page** (HTML, CSS and JavaScript, no framework) is everything the technician sees and clicks: the start screen, the photo with its circles, the counters, the result and the report. It also *remembers the slide being counted* — the running totals live in the browser's memory, so nothing about the patient is ever stored anywhere else. Closing the page forgets the slide.
- **The analyser** is a small Python program (a *server*: a program that waits for requests and answers them) built with **FastAPI**. It has one job: receive one field photo and answer with the positions of the white blood cells and parasites it found, plus whether the photo is usable. The finding is done with **OpenCV**, the standard computer-vision library: it isolates the purple-stained spots, measures their size and shape, and sorts them into "white blood cell", "parasite" or "ignore".

The WHO counting rule (200 or 500 WBC, ×8,000/µL) is simple arithmetic, so it lives in the page, in its own small file that we can test on its own.

To tune and prove the analyser, we use a public set of real smartphone-microscope photos in which an expert marked every parasite and white cell. We tune OpenCV's thresholds on some patients, then measure accuracy on *other* patients the analyser never saw — that's the honest "How accurate is it?" screen.

Why this shape: the photo analysis needs Python/OpenCV, but clicking circles on an image to correct them needs JavaScript in the browser. One small server plus one plain page is the smallest setup that does both, and Vercel can host both for free.

## The Core Journey Through the System
PRD ref: `prd.md > The Core Journey`.

1. Technician opens the site → Vercel serves `public/index.html` → **Start screen**.
2. Types a slide reference, clicks **Start counting** → the page creates an empty *slide session* in memory → **Counting screen**.
3. Picks a photo → the page shrinks it to at most 1600 px on its long side (keeps uploads small and analysis consistent) → sends it to `POST /api/analyze`.
4. The analyser finds the circular field of view, scores focus, detects WBCs and parasites → returns JSON (positions + quality).
5. The page draws the photo on a canvas with blue/red circles, shows this field's counts and the quality badge (`Out of focus` / `No cells found` with **Use anyway**).
6. Clicks remove or add marks — handled entirely in the page; counts update instantly.
7. **Confirm field** → `protocol.js` adds the field to the session, recomputes totals and returns the guidance message ("Capture another field", "Keep counting up to 500 WBC", "Enough counted").
8. When the protocol says enough → **See result** → the page computes density with `protocol.js` and shows the **Result screen**; printing uses the browser's print-to-PDF.
9. **Try a sample slide** follows the same path, except step 3 takes the next image from `public/samples/` instead of a file picker — the *real* analyser still runs on it.
10. **How accurate is it?** loads `public/evaluation/evaluation.json`, produced offline by `tools/evaluate.py`.

## Stack
Learner agreed to the recommended stack at spec review ("oui").

- **Python 3.12** — learner's chosen language. https://docs.python.org/3.12/
- **OpenCV** (`opencv-python-headless`, the smaller no-GUI build suited to servers) + **NumPy** — image analysis. https://docs.opencv.org/4.x/
- **FastAPI** + `python-multipart` (file uploads) — the analyser's web interface; **Uvicorn** to run it locally. https://fastapi.tiangolo.com/ — tradeoff accepted: one new concept (a server) for the learner.
- **Plain HTML/CSS/JavaScript** with an HTML `<canvas>` for the image and marks — chosen because click-to-correct marks are awkward in all-Python UI tools (Streamlit). https://developer.mozilla.org/docs/Web/API/Canvas_API
- **Tests:** `pytest` for the analyser; Node's built-in test runner (`node --test`, Node 22 is installed) for `protocol.js`.
- Exact versions are pinned in `requirements.txt` at build time (latest stable then); not verified yet.

## Where It Runs and How Someone Tries It
- **Locally:** `pip install -r requirements.txt`, then `uvicorn app:app --reload`, then open http://127.0.0.1:8000. The FastAPI app also serves `public/` locally, so one command runs everything. This is what we record for the demo video if deployment misbehaves.
- **Public link (learner's choice: Vercel):** the repo is imported into Vercel (learner creates the free Vercel account and connects GitHub himself). Vercel serves `public/` as static files and runs `app.py` as a Python function. https://vercel.com/docs/frameworks/backend/fastapi
- Constraints checked: Vercel functions accept **at most 4.5 MB per request** → handled by resizing in the browser (step 3); Python function bundles may be up to **500 MB** → OpenCV headless + NumPy fit. https://vercel.com/docs/functions/limitations
- **To verify early in the build:** FastAPI zero-config detection on Vercel and OpenCV importing correctly there (first deploy of a "hello" analyser).
- Submission still needs the demo video (< 3 min, YouTube/Vimeo) and the public GitHub repo with an open-source licence (MIT) — handled in `6-ship`.

## Look and Feel
From `prd.md > Look and Feel`. Implemented as CSS custom properties in `public/styles.css`.

- Colours: background `#F7F9FA`, surface `#FFFFFF`, text navy `#14213D`, muted text `#5B6474`, accent teal `#0F766E` (buttons, progress bar), WBC mark blue `#2563EB`, parasite mark red `#DC2626`, warning amber `#B45309`. Marks drawn as 2–3 px rings so the stain under them stays visible.
- Type: Inter (Google Fonts) with a system sans-serif fallback — changed from system fonts only at final review for a more polished look. Counters and density: large, bold, tabular numerals.
- Layout: two columns on laptop (image left, panel right), stacked on phones (< 800 px). Buttons ≥ 44 px tall.
- Tone of copy: short, factual, lab-like ("Capture another field — 72 WBC to go"). No emoji, no gradients, no "AI magic" language. Disclaimer visible on Start and Result.

## Components

### Analyser API (`app.py`)
- `POST /api/analyze` — multipart field `image` (JPEG/PNG). Returns the **analysis result** (see Data Model). 400 with `{"error": "not_an_image"}` if unreadable.
- `GET /api/health` → `{"ok": true}` (deploy check).
- Locally also mounts `public/` as static files.
PRD ref: `prd.md > Field analysis`, `prd.md > Image quality check`.

### Field analysis engine (`malariascope/analysis.py`)
Pure functions, no web code, so it can be tested and reused by the tools.
1. **Normalise:** resize to 1600 px long side if larger.
2. **Field of view:** smartphone-through-eyepiece photos are a bright disc in black; threshold brightness, keep the largest contour, erode slightly → mask. Everything outside is ignored.
3. **Focus score:** variance of the Laplacian inside the mask; below `focus_min` → `quality.reason = "blur"`.
4. **Stain map:** Giemsa-stained chromatin/nuclei are dark purple on a pale background; build a "stain" channel (darkness weighted by purple hue/saturation) and threshold it inside the mask (Otsu, with a tunable offset).
5. **White blood cells:** large blobs after morphological opening; area within `[wbc_area_min, wbc_area_max]`; blobs larger than the max are counted as `round(area / median_wbc_area)` touching cells.
6. **Parasites:** small dark spots enhanced with a black-hat filter; area within `[par_area_min, par_area_max]`, roundish, and not inside or touching a WBC.
7. If the mask has no WBC and almost no stain → `quality.reason = "no_cells"`.
All thresholds come from `malariascope/params.json`, produced by `tools/tune.py`.
PRD ref: `prd.md > Field analysis`, `prd.md > Image quality check`.

### Counting page (`public/app.js`)
Screens as sections shown/hidden by a tiny state switch: `start`, `counting`, `result`, `evaluation`.
- Upload: file input + drag-and-drop; resize via canvas to ≤ 1600 px, JPEG quality 0.9; "Analysing…" overlay while waiting.
- Canvas drawing of the photo and marks, legend, this-field counts, quality badge with **Use anyway** / **Retake**.
- **Mark editing:** default tool = remove (click within a mark's radius removes it); **Add parasite** / **Add WBC** tools add a mark at the click point. Click coordinates are converted from screen size to image pixels.
- **Confirm field**, **Discard field**, thumbnails strip, **New slide** with confirmation when unfinished.
- Sample mode reads `public/samples/manifest.json` and fetches the next image, then posts it to `/api/analyze` exactly like an upload.
PRD ref: `prd.md > Starting a slide`, `prd.md > Correcting marks`, `prd.md > States and Boundaries`.

### WHO protocol (`public/protocol.js`)
Pure functions, unit-tested:
- `addField(session, field)` → new session with totals updated.
- `guidance(session)` → `{ target: 200|500, remainingWbc, canFinish, message }` following: < 200 WBC → continue; ≥ 200 WBC and ≥ 100 parasites → finish; ≥ 200 and < 100 → target 500; ≥ 500 → finish.
- `density(session)` → `round(parasites × 8000 / wbc)`; `null` if wbc = 0.
PRD ref: `prd.md > Running count and guidance (the kernel)`, `prd.md > Result and report`.

### Result and report (`public/app.js` + print CSS)
Density with formula, totals, per-field table, review checkbox toggling **Preliminary** / **Reviewed by technician**, `window.print()` with a print stylesheet that hides buttons.
PRD ref: `prd.md > Result and report`.

### Evaluation screen (`public/app.js` + `public/evaluation/`)
Renders `evaluation.json`: summary figures, per-image table (expert vs MalariaScope, WBC and parasites), and failure examples with saved annotated images and one-line explanations written after looking at them.
PRD ref: `prd.md > Accuracy evaluation`.

### Dataset tools (`tools/`)
Run on the learner's PC, never on Vercel.
- `fetch_dataset.py` — downloads a chosen handful of patients (target ~12) from the NLM zip into `data/` (git-ignored). Tries reading only the needed files from the remote zip using HTTP range requests; falls back to the full 3.9 GB download if the server refuses.
- `annotations.py` — parses the NLM annotation files into `{wbc: [(x,y)], parasites: [(x,y)]}` per image, rescaled to 1600 px.
- `tune.py` — grid-searches `params.json` on the **tuning patients** to minimise count error.
- `evaluate.py` — runs the analyser on the **held-out patients**, matches detections to expert points (same type, within a radius), writes `public/evaluation/evaluation.json` (+ failure images).
- `make_samples.py` — copies one **held-out** patient's fields, resized, into `public/samples/` with `manifest.json`.

## Data Model
- **Analysis result** (API → page, not stored):
  `{ width, height, quality: { ok, focusScore, reason: null|"blur"|"no_cells" }, wbc: [{x, y, r}], parasites: [{x, y, r}], ms }`
- **Field** (page memory): `{ id, thumbnailUrl, wbc: [...], parasites: [...], wbcCount, parasiteCount, flagged }` — editable until confirmed.
- **Slide session** (page memory only): `{ reference, startedAt, sample: bool, fields: [Field], totals: { wbc, parasites } }`. Updated on Confirm; cleared by New slide; lost on page close (accepted in `prd.md > States and Boundaries`).
- **params.json** (repo file): thresholds for the engine; changed only by `tune.py` or by hand.
- **evaluation.json** (repo file): `{ dataset, patients, images: [{ file, expert: {wbc, parasites}, ours: {wbc, parasites}, precision, recall }], summary: {...}, failures: [...] }`.

## File Structure

```
malariascope/
├── app.py                    # FastAPI app: /api/analyze, /api/health (+ serves public/ locally)
├── vercel.json               # explicit builds: app.py as Python function, public/ as static files
├── .python-version           # 3.12 for Vercel
├── malariascope/
│   ├── __init__.py
│   ├── analysis.py           # OpenCV engine: field of view, focus, WBC + parasite detection
│   └── params.json           # tuned thresholds
├── public/                   # everything the browser loads (served by Vercel as static files)
│   ├── index.html            # the 4 screens
│   ├── styles.css            # look & feel + print styles
│   ├── app.js                # screens, upload, canvas marks, corrections, report, evaluation
│   ├── protocol.js           # WHO counting rule + density (pure functions)
│   ├── i18n.js               # English/French interface text + language switch
│   ├── samples/              # one held-out patient's fields + manifest.json (sample mode)
│   └── evaluation/           # evaluation.json + failure example images
├── tools/                    # offline scripts: fetch, parse, tune, evaluate, make samples
├── tests/
│   ├── test_analysis.py      # pytest: engine on known sample images
│   └── protocol.test.mjs     # node --test: stopping rule and density
├── data/                     # raw NLM images (git-ignored, never committed)
├── devpost/                  # Devpost learning workspace (scope, prd, spec, checklist)
├── requirements.txt          # pinned runtime deps (used by Vercel too)
├── requirements-dev.txt      # pytest
├── DATA.md                   # dataset source, citation, licence note, what is included
├── LICENSE                   # MIT (code only)
└── README.md                 # what it is, how to run, how to deploy, how accuracy was measured
```

## External Services and Dependencies
- **NLM Thick Smears 150 dataset** — https://data.lhncbc.nlm.nih.gov/public/Malaria/Thick_Smears_150/index.html — one zip of ~3.9 GB, 3024×4032 JPEGs, expert annotations of parasites and WBCs (file format to confirm at fetch). Citation requested: Yang F. et al., "Deep Learning for Smartphone-Based Malaria Parasite Detection in Thick Blood Smears", IEEE J Biomed Health Inform, 2020. **No explicit licence found** on NLM's pages (checked the dataset page and datasheet); see Decisions.
- **Vercel** (Hobby, free) — static hosting + Python function. No API keys. Limits: 4.5 MB request body, 500 MB Python bundle. https://vercel.com/docs/functions/limitations
- **GitHub** — public repo https://github.com/Leandre99/MalariaScope.
- No paid APIs, no database, no accounts.

## Important Failure Modes
- **Counts are wrong on some images** (different stain intensity, crowded fields) → the technician corrects marks; the Evaluation screen shows the error honestly with failure examples. This is expected, not hidden.
- **Upload too big or slow on Vercel** → browser-side resize keeps requests well under 4.5 MB; "Analysing…" indicator; on network error, show "Couldn't reach the analyser — try again" and keep the current session intact.
- **Remote zip reading not supported by NLM's server** → full download fallback (slow on a weak connection; can be left running).
- **OpenCV fails to load on Vercel** → caught by the early hello-deploy check; fallback is recording the demo locally (a link is optional).

## What Was Simplified and Why
- **Classical OpenCV detection** instead of a trained deep-learning detector — fits 2–4 hours and is explainable; a trained model would need GPU time and a training pipeline.
- **Slide session in browser memory** instead of a database — no patient data stored, no infrastructure; the fuller version would need storage and privacy safeguards.
- **File upload** instead of live camera capture — enough to prove the loop; live capture is in `prd.md > Deferred From the POC`.
- **A handful of patients** instead of the full 150 — enough to tune and to evaluate honestly; the full set would take hours to download and process.
- **Sample slide** is labelled as sample data from the public dataset, and the real analyser runs on it — the kernel is never faked.

## Decisions and Open Issues
- **Stack (Python + FastAPI + plain JS, OpenCV classical)** — recommended by the agent, accepted by the learner ("oui"). Tradeoff: learning what a small server is; lower accuracy than a trained model.
- **Small dataset sample in the repo, with citation** — accepted by the learner. Tradeoff: NLM states no explicit licence; we commit only a few resized images, credit NLM and cite Yang et al. 2020 in `DATA.md`, and state the absence of a written licence plainly.
- **Public link on Vercel** — learner's choice (agent had suggested Hugging Face Spaces). Consequences handled: browser-side resizing for the 4.5 MB limit; early deploy check.
- **Code licence MIT** — agent default to satisfy the "open source licence" rule; learner can change it in `6-ship`.
- **Implementation details derived by the agent:** 1600 px working resolution, remove-on-click as the default tool, tuning/held-out patient split.
- **Learner uncertainty discussed:** "Je n'ai pas de microscope — en quoi la plateforme va servir ?" Clarified: the product is for lab technicians who have microscopes; the demo uses real expert-annotated smartphone-microscope photos, which also make the accuracy comparison possible.
- **Open — to check at the start of the build:** the annotation file format; whether one held-out patient has enough fields to reach 200 WBC in sample mode (if not, the sample stops at "Keep counting" and the video explains it, or we pick a richer patient); FastAPI + OpenCV working on Vercel.
