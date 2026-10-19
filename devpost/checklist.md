---
doc: checklist
status: approved
---

# Build Checklist

Build mode: fast (learner: "travaille en autodidacte, termine le projet")

## Slices

- [x] **1. Real expert-annotated smear images are on disk and readable**
  Becomes usable: A handful of NLM thick-smear patients in `data/`, their annotations parsed, and a preview image with the expert's WBCs (blue) and parasites (red) drawn on it.
  Why now: Risk first — the dataset's size, download method and annotation format are unknown, and every later slice (tuning, evaluation, sample mode) depends on them. This is the one allowed "technical layer" slice: it proves a critical risk and leaves runnable evidence. Bootstrapping (requirements, .gitignore for data/) lives here.
  PRD ref: `prd.md > Accuracy evaluation`, `prd.md > Open Questions`
  Spec ref: `spec.md > Dataset tools (tools/)`, `spec.md > External Services and Dependencies`
  Build: Pin requirements; `tools/fetch_dataset.py` (remote-zip range reads, full-download fallback) for ~12 patients; `tools/annotations.py` parser rescaling to 1600 px; a preview script that writes an overlay PNG; record per-patient WBC totals to pick the sample patient; add `data/` to .gitignore.
  Verify (mechanical): Run fetch for the chosen patients and confirm image counts; run the parser and print WBC/parasite counts per image; open the generated overlay and confirm marks sit on cells.
  Learner check: Open the overlay PNG and say whether the blue and red circles land on white cells and parasites.
  Commit: `Fetch NLM thick-smear sample and parse expert annotations`

- [x] **2. Upload a field photo and see blue and red circles**
  Becomes usable: Run one command, open the page, start a slide, upload a field: the photo appears with detected WBCs and parasites circled and this field's counts shown.
  Why now: The first end-to-end path (page → API → OpenCV → page) that everything else builds on; the detection quality can be improved later without changing this path.
  PRD ref: `prd.md > The Core Journey` (steps 1–6), `prd.md > Starting a slide`, `prd.md > Field analysis`
  Spec ref: `spec.md > Analyser API (app.py)`, `spec.md > Field analysis engine (malariascope/analysis.py)`, `spec.md > Counting page (public/app.js)`, `spec.md > Look and Feel`
  Build: FastAPI app with `/api/health` and `/api/analyze`; first-pass engine (field of view, stain map, WBC and parasite blobs) with hand-picked params; `index.html` + `styles.css` + `app.js` for Start and Counting screens, browser-side resize, canvas drawing, legend, "Analysing…" state, not-an-image error.
  Verify (mechanical): `pytest` on the engine with one dataset image (returns non-empty WBC list, JSON shape matches the spec); start uvicorn, `curl` `/api/health` and POST a dataset image to `/api/analyze`; load the page in the browser and upload an image.
  Learner check: Run the app, upload one of the downloaded field photos, and say whether the circles roughly match what you see.
  Commit: `Analyse an uploaded field and draw detections`

- [ ] **3. The app runs on a public Vercel link**
  Becomes usable: The same upload-and-circles flow works at a `*.vercel.app` URL.
  Why now: OpenCV on Vercel is unverified; finding out now leaves time to fall back to a local demo.
  PRD ref: `prd.md > The Core Journey`
  Spec ref: `spec.md > Where It Runs and How Someone Tries It`, `spec.md > Important Failure Modes`
  Build: Any Vercel config needed for FastAPI + `public/`; learner creates the Vercel account and imports the GitHub repo; push.
  Verify (mechanical): `curl` the deployed `/api/health`; POST a resized dataset image to the deployed `/api/analyze` and check the JSON.
  Learner check: Open the Vercel link on your phone, upload a field photo, and confirm the circles appear.
  Commit: `Configure Vercel deployment`

- [x] **4. Count a slide field by field with WHO guidance (the kernel)**
  Becomes usable: Confirm or discard each field; totals and the WBC progress bar climb; guidance says "Capture another field", "Keep counting up to 500 WBC" or "Enough counted"; confirmed-field thumbnails; New slide with confirmation.
  Why now: This is `scope.md > The Unique Kernel`; it must exist before polish.
  PRD ref: `prd.md > Running count and guidance (the kernel)`, `prd.md > States and Boundaries`
  Spec ref: `spec.md > WHO protocol (public/protocol.js)`, `spec.md > Counting page (public/app.js)`, `spec.md > Data Model`
  Build: `protocol.js` (addField, guidance, density) with `tests/protocol.test.mjs`; wire Confirm/Discard, totals, progress target 200→500, guidance text, thumbnails strip, New slide confirmation.
  Verify (mechanical): `node --test tests/protocol.test.mjs` passes for <200, ≥200 & ≥100 parasites, ≥200 & <100 (target 500), ≥500, zero WBC; in the browser, confirm several fields and watch totals and guidance change.
  Learner check: Upload and confirm fields one after another; tell me whether the counter and the "what to do next" message feel right for a technician.
  Commit: `Add WHO field-by-field counting and guidance`

- [x] **5. Fix the machine's mistakes and catch bad photos**
  Becomes usable: Click a circle to remove it; Add parasite / Add WBC tools to add missed ones; blurred or cell-less photos are flagged with Retake / Use anyway and not counted unless overridden.
  Why now: Human correction is what makes the count trustworthy; the quality check needs the focus score from the engine already in place.
  PRD ref: `prd.md > Correcting marks`, `prd.md > Image quality check`
  Spec ref: `spec.md > Counting page (public/app.js)`, `spec.md > Field analysis engine (malariascope/analysis.py)`
  Build: Hit-testing and add/remove tools with screen→image coordinate mapping; focus score and no-cells rule in the engine; quality badge and buttons in the page.
  Verify (mechanical): pytest — a blurred copy of a dataset image returns `reason: "blur"`, a blank image returns `"no_cells"`; in the browser, remove and add marks and check counts update; flagged field adds nothing until Use anyway.
  Learner check: Remove a wrong circle, add a missed parasite, and upload a blurry photo; say whether correcting feels quick enough.
  Commit: `Add mark correction and image quality check`

- [ ] **6. Tuned detector with an honest accuracy screen**
  Becomes usable: Thresholds tuned on tuning patients; "How accurate is it?" screen comparing MalariaScope to experts on held-out patients, with failure examples.
  Why now: Needs the engine, data and screens from earlier slices; its numbers feed the demo and README.
  PRD ref: `prd.md > Accuracy evaluation`
  Spec ref: `spec.md > Dataset tools (tools/)`, `spec.md > Evaluation screen (public/app.js + public/evaluation/)`, `spec.md > Data Model`
  Build: `tools/tune.py` grid search → `params.json`; `tools/evaluate.py` with point matching → `public/evaluation/evaluation.json` + failure images; Evaluation screen rendering summary, table and failures with explanations.
  Verify (mechanical): Run tune and evaluate; confirm evaluation.json lists only held-out patients and its summary matches a recomputation; open the Evaluation screen.
  Learner check: Open "How accurate is it?" and say whether you'd trust the numbers and understand the failure examples.
  Commit: `Tune detector and add accuracy evaluation`

- [ ] **7. Result, report and sample slide**
  Becomes usable: See result with density and formula, per-field table, review checkbox (Preliminary → Reviewed by technician), print to PDF; "Try a sample slide" runs a held-out patient's real fields through the analyser.
  Why now: Closes the core journey and gives judges a no-microscope way in; depends on protocol (slice 4) and a chosen held-out patient (slice 6).
  PRD ref: `prd.md > Result and report`, `prd.md > Starting a slide`, `prd.md > The Core Journey` (steps 8–11)
  Spec ref: `spec.md > Result and report (public/app.js + print CSS)`, `spec.md > Dataset tools (tools/)`, `spec.md > Counting page (public/app.js)`
  Build: Result screen + print stylesheet + disclaimer; `tools/make_samples.py` → `public/samples/` + manifest; sample-mode Next sample field button; `DATA.md` with source, citation and licence note.
  Verify (mechanical): Unit-check density on a known session; run a full sample slide in the browser to the result; print preview shows a clean report; deployed site serves the samples.
  Learner check: Click "Try a sample slide", go all the way to the result, tick the review box and print the report.
  Commit: `Add result report and sample slide mode`

## Hands-on Checkpoints

- [ ] Early usable behavior explored — after slice 4 (WHO counting loop working end to end)
- [ ] Final kick-the-tires exploration and feedback completed

## Final Review

- [ ] Final review complete — feedback resolved and learner confirms ready to ship

## Code Tour and App Map

- [ ] Learning activity complete — guided route, focused alternative, prior practice connected, or brief recap
- [ ] Optional edit and transfer reflection addressed — offered/declined/already covered/not applicable as appropriate
- [ ] `devpost/app-map.html` generated from finished code, checked, and shown, including a project-grounded practice to reuse

Activity and evidence:
Route and stops:
Edit outcome:
Reflection:
Activity mode:

## Revisions
- Dataset layout differs from the spec's guess — images are `<patient>/<name>.jpg` and annotations `GT_updated/<patient>/<name>.txt` (parasites = circles, WBCs = single points); the photos carry an EXIF rotation while expert coordinates use the raw landscape pixel grid, so tools load images ignoring EXIF orientation. Remote-zip range reads worked, no full download needed. 10 patients fetched; 9 have ≥ 200 WBC across their fields, so sample mode can reach the WHO threshold.
- API moved from `api/index.py` to root `app.py` (+ `vercel.json`, `.python-version`) — Vercel's FastAPI support detects `app.py`/`index.py` entrypoints and treats an `api/` folder as legacy per-file functions; it also asks not to mount `public/` in the app, so the static mount now runs only outside Vercel.
- Slice 4 built before slice 3 was verified — slice 3's config is committed and pushed, but its live check waits for the learner to create the Vercel project; building continued rather than idling.
