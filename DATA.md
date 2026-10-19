# Data used by MalariaScope

## Source

**NLM Thick Smears 150** — Giemsa-stained thick blood smears from 150 *P. falciparum* patients, photographed with a smartphone through a microscope at Chittagong Medical College Hospital, Bangladesh, and annotated by an expert slide reader (parasites and white blood cells). Published by the U.S. National Library of Medicine (Lister Hill National Center for Biomedical Communications).

- Download page: https://data.lhncbc.nlm.nih.gov/public/Malaria/Thick_Smears_150/index.html
- Dataset overview: https://lhncbc.nlm.nih.gov/LHC-research/LHC-projects/image-processing/malaria-datasheet.html

Please cite:

> F. Yang, M. Poostchi, H. Yu, Z. Zhou, K. Silamut, J. Yu, R. J. Maude, S. Jaeger, S. Antani. *Deep Learning for Smartphone-Based Malaria Parasite Detection in Thick Blood Smears.* IEEE Journal of Biomedical and Health Informatics, 24(5), 2020.

## Licence

We did not find an explicit licence on NLM's dataset pages. The images are de-identified and publicly released by NLM for research. To stay respectful of that release, this repository:

- does **not** redistribute the dataset; `tools/fetch_dataset.py` downloads what you need from NLM directly into `data/` (git-ignored);
- includes only a **small derived sample**: one patient's fields resized to 1600 px (`public/samples/`), a few evaluation illustrations (`public/evaluation/`), the start-screen picture (`public/img/hero.jpg`, a sample field with MalariaScope's own detections, made by `tools/make_hero.py`) and one test fixture (`tests/fixtures/field.jpg`), each credited here;
- credits NLM and the authors above.

If you are the data owner and want these sample images removed, please open an issue.

## How the data is used

| Patients | Role |
|---|---|
| TF102_234, TF15_C87P48, TF19_C94P55, TF35_Sc521, TF49_CW3, TF86_BD2_93 | Tuning the detector's thresholds (`tools/tune.py`) |
| TF63_CS25, TF31_Sc440, TF45_UW18, TF7_C49P10 | Held out: accuracy evaluation (`tools/evaluate.py`) — never used for tuning |
| TF63_CS25 (held out) | "Try a sample slide" in the app (`tools/make_samples.py`) |

The split is defined in `tools/split.py`. Reproduce everything with:

```bash
python tools/fetch_dataset.py --patients 10
python tools/tune.py
python tools/evaluate.py
python tools/make_samples.py
```
