# MalariaScope

**A counting aid for malaria microscopy.** A lab technician photographs each field of a Giemsa-stained thick blood smear through the microscope eyepiece with a phone. MalariaScope marks the white blood cells and parasites, keeps the WHO running count, tells the technician when enough has been counted, and computes the parasite density — which the technician reviews and validates.

> Counting aid only. Not a diagnosis. A trained technician reviews every count.

## Why

Malaria kills around 600,000 people a year, most of them in sub-Saharan Africa. Microscopy is still the reference test in health centres, and the WHO method asks the technician to count parasites against 200 (or 500) white blood cells, field after field, often with a hand tally counter at the end of a long day. MalariaScope takes the tallying and the arithmetic off their hands while keeping them in control.

## What it does

1. **Start a slide** with a lab reference (no patient names), or **Try a sample slide** made of real smartphone-microscope photos.
2. **Upload a field photo.** OpenCV checks focus, then circles white blood cells (blue) and parasites (red).
3. **Correct the marks** — tap a circle to remove it, or add a missed parasite / WBC.
4. **Confirm the field.** The running totals and guidance follow the WHO thick-film rule:
   - fewer than 200 WBC → *capture another field*;
   - ≥ 200 WBC and ≥ 100 parasites → *enough*;
   - ≥ 200 WBC and < 100 parasites → *keep counting up to 500 WBC*.
5. **See the result:** parasites/µL = parasites × 8,000 ÷ WBC, with the per-field breakdown. The report stays *Preliminary* until the technician ticks "I have reviewed these counts", then prints to PDF.
6. **How accurate is it?** compares MalariaScope's automatic marks with an expert's on patients it was never tuned on, including failure examples.

## How it works

```
Browser (public/)                          Python function (app.py)
──────────────────                          ────────────────────────
index.html / app.js                         FastAPI  POST /api/analyze
  resize photo to 1600 px  ── JPEG ──▶       malariascope/analysis.py (OpenCV)
  draw marks on <canvas>   ◀── JSON ──         1. microscope disc mask
  corrections, totals                          2. focus score (Laplacian variance)
protocol.js (WHO rule, density)                3. WBC: saturated purple blobs
slide session kept in page memory only         4. parasites: small dark dots (black-hat filter)
```

- No database, no accounts, no patient data: the slide being counted lives only in the browser tab.
- Thresholds in `malariascope/params.json` were tuned by `tools/tune.py` on 6 patients and evaluated by `tools/evaluate.py` on 4 other patients. See [DATA.md](DATA.md).

## Accuracy (held-out patients, automatic marks before any correction)

Measured on 79 fields from 4 patients never used for tuning, against expert annotations (NLM Thick Smears 150). Images go through the same resizing and JPEG compression as an upload from the app:

| | Precision | Recall | Mean count error per field |
|---|---|---|---|
| White blood cells | 98% | 88% | ±1.3 |
| Parasites | 63% | 53% | ±20.8 |

Parasite density per patient compared with the expert: +0.4%, +4% and −27% for three patients. **But** on the patient with few parasites (3,795/µL), debris and stain specks are marked as parasites and the density is overestimated about 4.7×. This is why the technician reviews every field, and why the app shows these numbers and failure examples on its *How accurate is it?* screen.

## Run it locally

Requires Python 3.12 (and Node 22 only for the protocol tests).

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements-dev.txt
uvicorn app:app --reload
```

Open http://127.0.0.1:8000 and click **Try a sample slide**.

## Tests

```bash
python -m pytest -q tests
node --test tests/protocol.test.mjs
```

## Deploy (Vercel)

Import the GitHub repository in Vercel and deploy with the defaults. Vercel detects the FastAPI app in `app.py`, installs `requirements.txt`, serves `public/` from its CDN and runs the analyser as a Python function (settings in `vercel.json`). The page resizes photos before upload to stay under Vercel's 4.5 MB request limit.

## Reproduce the accuracy numbers

```bash
python tools/fetch_dataset.py --patients 10   # ~400 MB from NLM into data/ (git-ignored)
python tools/tune.py                          # writes malariascope/params.json
python tools/evaluate.py                      # writes public/evaluation/
python tools/make_samples.py                  # writes public/samples/
```

## Project layout

```
app.py                 FastAPI app (API + serves public/ locally)
malariascope/          OpenCV engine and tuned parameters
public/                the web page: index.html, styles.css, app.js, protocol.js, samples/, evaluation/
tools/                 dataset download, annotation parsing, tuning, evaluation, sample generation
tests/                 pytest (engine + API) and node tests (WHO rule)
devpost/               planning documents (scope, PRD, spec, build checklist)
```

## Limitations

- Classical image processing, not a trained neural network: accuracy is measured and shown honestly in the app, and depends on stain quality and focus.
- Tested only on *P. falciparum* thick smears from one public dataset (Bangladesh); other stains, microscopes and phones may behave differently.
- No species identification, no thin smears, and no formal "negative slide" rule (100 fields).
- Not a medical device. Every count must be reviewed by a trained technician.

## Credits

Data: U.S. National Library of Medicine, *NLM Thick Smears 150* — Yang F. et al., IEEE J Biomed Health Inform, 2020. See [DATA.md](DATA.md).

Code: MIT licence — see [LICENSE](LICENSE).
