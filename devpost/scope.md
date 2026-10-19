---
doc: scope
status: approved
---

# MalariaScope

A smartphone-microscopy assistant that counts malaria parasites on a thick blood smear, field by field, and tells the lab technician when they have counted enough to report a parasite density.

## The Unique Kernel
MalariaScope doesn't just detect parasites in one picture — it **follows the WHO counting protocol with the technician**. After each photographed field it updates the running count of white blood cells (WBC) and parasites, and tells the technician whether to capture another field or stop. When the protocol's stopping rule is met, it computes parasites/µL. The technician always has the final say on every count.

## Who It's For
A laboratory technician in a rural or district health centre in Benin (and similar settings across sub-Saharan Africa), reading Giemsa-stained thick smears under a microscope, often with a long queue of patients.
Today they count by eye, field after field, tallying white cells and parasites on paper or a hand counter until they reach 200 WBC. It is slow, tiring, and error-prone at the end of a long day, and there aren't enough trained microscopists.

## The Core Loop
1. The technician starts a new slide (patient reference only — no names).
2. They hold their phone to the microscope eyepiece, photograph a field, and upload it.
3. MalariaScope checks the photo is usable (in focus, properly stained), then marks each white blood cell and each parasite it found directly on the image.
4. The technician glances at the marks, corrects any obvious mistake, and confirms.
5. The running totals update: "128 / 200 WBC — capture another field."
6. Repeat until the stopping rule is met, then MalariaScope shows the parasite density and a short report the technician validates.

They come back for every slide, every day: it replaces the tally counter and the mental arithmetic.

## Inspiration & Identity
Clinical, calm, trustworthy — a lab tool, not a gadget. Clear, high-contrast, works on a cheap phone screen and a laptop.
Reference: WHO microscopy counting method for thick films (parasites counted against 200 WBC, assumed 8,000 WBC/µL).

## Why This Matters to the Learner
Malaria is a daily reality in Benin. The learner wants a project with global impact ("pense problème dans le monde"), and malaria is one of the world's deadliest diseases, concentrated in Africa.

## What "Working" Looks Like
Open MalariaScope, start a slide, upload real smartphone-microscope photos of a thick smear one by one (from a public annotated dataset). For each one, the photo appears with **white cells circled in one colour and parasites circled in red**, the counters climb field after field, and the app says "capture another field" until it says "done" and shows the parasite density per µL.
The "oh, that's cool" beat: the counts climbing on screen, then a side-by-side **"MalariaScope vs. expert annotation"** for the same images, showing how close the automatic count is.

## The POC Boundary
- One slide session at a time: upload fields → automatic WBC + parasite detection → technician confirms/corrects → running totals → stopping rule → parasite density + simple report.
- Image quality check (blur / bad stain) with a "retake" message.
- Classical computer vision in Python (OpenCV), tuned on a public annotated thick-smear dataset (dataset and licence confirmed in the spec).
- A small evaluation on held-out dataset images comparing our counts with the experts'.
- Runs in a browser; demonstrated with dataset images (no microscope needed for the demo).

## Later
- Live camera capture straight from the phone, held on the eyepiece.
- Offline use on a phone with no internet.
- Species identification (P. falciparum vs. others) and thin-smear support.
- A trained deep-learning detector to improve accuracy.
- Patient history and export to the health centre's records.
- French / Fon interface.

## Explicitly Cut
- **Diagnosis or treatment advice** — this is a counting aid; a human technician validates every result. Making medical decisions is unsafe for a proof of concept.
- **Patient identity or personal data** — not needed to prove the counting loop; avoids privacy risk.
- **User accounts and multi-clinic management** — no value for the demo.
- **Native mobile app** — a web page is enough to prove the loop and lets judges try it.
- **Paid cloud services or AI APIs** — no budget, and not needed for classical counting.
