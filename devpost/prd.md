---
doc: prd
status: approved
---

# MalariaScope — Product Requirements

A web app that helps a health-centre lab technician count malaria parasites on a Giemsa-stained thick blood smear, field by field, following the WHO counting method, and produce a parasite density the technician validates.
Source: `scope.md > The Unique Kernel`, `scope.md > Who It's For`.

## The Core Journey
Develops `scope.md > The Core Loop`.

1. The technician opens MalariaScope and lands on the **Start screen**.
2. They type a slide reference (e.g. `SLIDE-0142`, no patient name) and press **Start counting** — or press **Try a sample slide** to use real images from a public dataset.
3. The **Counting screen** opens with an empty image area and counters at 0 / 200 white blood cells (WBC).
4. They upload a photo of one microscope field (or, in sample mode, press **Next sample field**).
5. MalariaScope checks the photo's quality. If it is unusable, it says why and asks for a retake; the field is not counted.
6. If usable, the photo appears with every detected **WBC circled in blue** and every **parasite circled in red**, plus this field's counts.
7. The technician fixes any mistake (remove a wrong mark, add a missed one), then presses **Confirm field**.
8. The running totals update and a guidance message says what to do next: "Capture another field" or "Enough counted — see result".
9. Steps 4–8 repeat until the WHO stopping rule is met.
10. The **Result screen** shows the parasite density per µL, the totals, the per-field breakdown, and requires the technician to tick **"I have reviewed these counts"** before the report is marked final. They can print / save the report as PDF.
11. **New slide** clears everything and returns to step 1.

Success = a technician (or a judge in sample mode) goes from first field to a validated parasite density without counting by hand.

## Screens and Layout
Four surfaces, all in one web page, usable on a laptop and a phone screen.

- **Start screen** — app name, one-line purpose, slide reference field, **Start counting**, **Try a sample slide**, a link to **How accurate is it?**, and a short disclaimer ("Counting aid only. Not a diagnosis.").
- **Counting screen** — the main workspace.
  - Large image area (left on laptop, top on phone) with the coloured marks and an upload button / drop zone.
  - Side panel (right on laptop, below on phone): WBC progress bar `128 / 200`, parasite total, number of fields confirmed, this field's counts, the quality badge, the guidance message, mark-editing tools, and **Confirm field** / **Discard field**.
  - A strip of thumbnails of confirmed fields with their counts.
- **Result screen** — big parasite density number, totals, per-field table, review checkbox, **Print report**, **New slide**.
- **How accurate is it? (Evaluation screen)** — MalariaScope's counts vs. expert annotations on test images the tool was not tuned on, with summary error figures and examples of where it fails.

## Look and Feel
Direction delegated to the agent by the learner ("fait ce qui est le mieux adapté"); proposed and accepted at PRD review.

- A calm, trustworthy **lab instrument**, not a gadget or a generic "AI app". No gradients, no glowing effects, no emoji.
- Light, clean background (near-white), dark navy text, a **teal** accent for primary actions.
- Marks: **blue** for white blood cells, **red** for parasites — high contrast against the purple/pink stain, consistent everywhere (image, legend, counters).
- Clean sans-serif type; counters and the final density in large, bold numerals readable at arm's length.
- Generous spacing, big touch targets (usable with gloves on a phone).
- Interface language: English (for judges). French is deferred.

## Features and Behavior

### Starting a slide
- [ ] Start counting is disabled until a slide reference is entered.
- [ ] Try a sample slide starts a session with the reference pre-filled (e.g. `SAMPLE-01`) and swaps the upload button for **Next sample field**.

### Field analysis
- As a lab technician, I want each field photo analysed automatically so that I don't have to tally cells by eye.
  - [ ] After upload, the photo appears with blue circles on WBCs and red circles on parasites within a few seconds, with a "Analysing…" indicator meanwhile.
  - [ ] The panel shows this field's WBC and parasite counts, matching the number of circles on the image.
  - [ ] A legend shows what blue and red mean.

### Image quality check
- [ ] A blurred photo is flagged "Out of focus — please refocus and retake", with no counts added.
- [ ] A photo with no detectable cells (wrong image, empty field, bad stain) is flagged "No cells found — is this a thick smear field?", with no counts added.
- [ ] The technician can choose **Use anyway** on a flagged photo, which then gets analysed normally.

### Correcting marks
- As a technician, I want to fix the tool's mistakes so that the final number is mine, not the machine's.
  - [ ] Clicking/tapping an existing mark removes it; the field counts update immediately.
  - [ ] With **Add parasite** or **Add WBC** selected, clicking the image adds a mark of that type; counts update immediately.
  - [ ] Corrections are possible until **Confirm field** is pressed.

### Running count and guidance (the kernel)
Implements the WHO thick-film method: count parasites against WBCs, assume 8,000 WBC/µL.
- [ ] Confirming a field adds its counts to the totals and its thumbnail to the strip.
- [ ] While fewer than 200 WBC are counted, the guidance says "Capture another field" and shows how many WBCs remain.
- [ ] At ≥ 200 WBC with ≥ 100 parasites, guidance says "Enough counted — see result" and **See result** becomes available.
- [ ] At ≥ 200 WBC with < 100 parasites, guidance says "Fewer than 100 parasites — keep counting up to 500 WBC", and the progress target becomes 500.
- [ ] At ≥ 500 WBC, **See result** becomes available whatever the parasite count.
- [ ] **Discard field** drops the current, unconfirmed field without changing totals.

### Result and report
- [ ] Density is shown as `parasites/µL = parasites counted × 8,000 ÷ WBC counted`, with the formula visible.
- [ ] If no parasites were counted, the result reads "No parasites seen in the fields examined" (not "negative").
- [ ] The report lists slide reference, date/time, fields examined, WBC total, parasite total, density, and the disclaimer.
- [ ] The report is marked **Preliminary** until the review checkbox is ticked, then **Reviewed by technician**.
- [ ] Print report produces a clean printable page (save as PDF from the browser).

### Accuracy evaluation
- As a judge or a clinician, I want to see how close MalariaScope is to experts so that I know how far to trust it.
  - [ ] The Evaluation screen lists test images with expert vs. MalariaScope counts for WBC and parasites.
  - [ ] It shows summary error figures and at least two failure examples with an honest one-line explanation.

## States and Boundaries
- **First use / empty slide** — Counting screen shows the drop zone, "Upload your first field" and 0 / 200.
- **Analysing** — indicator on the image; buttons disabled until done.
- **Flagged photo** — reason shown, nothing counted, Retake or Use anyway.
- **Not an image / unreadable file** — "This file isn't an image we can read." Nothing changes.
- **Leaving mid-slide** — New slide asks for confirmation before clearing an unfinished count.
- **Persistence** — nothing is stored on a server and no patient data is collected. A slide session lasts until New slide or the page is closed.

## Product Decisions
- Keep MalariaScope over simpler ideas — the learner wants a globally important problem ("pense problème dans le monde").
- Demo with public, expert-annotated smartphone-microscope images — the learner has no microscope; expert annotations also enable the accuracy comparison.
- English interface — submission and judges are English-speaking.
- Human always validates (review checkbox, "counting aid only" wording) — from `scope.md > Explicitly Cut` (no diagnosis).
- Screens, correction method, stopping-rule wording and look & feel were **delegated by the learner to the agent** ("je te laisse champ libre") and accepted at review.

## What We're Building
Start screen with sample mode; field upload; quality check; automatic WBC + parasite marking; mark correction; running totals with WHO stopping rule and guidance; result screen with density, review checkbox and printable report; evaluation screen comparing against experts.

## Deferred From the POC
- Saving sessions across page reloads or devices — needs storage; not needed to prove the loop.
- Live camera capture from the eyepiece — upload is enough for the demo.
- Patient records / export to clinic systems — privacy and integration work beyond the PoC.

## Possible Later Enhancements
- Offline phone app for clinics without internet.
- Species identification and thin-smear parasitaemia (%).
- A trained deep-learning detector for higher accuracy.
- French and Fon interface.
- WHO "100 fields" rule to formally report a negative slide.

## Non-Goals
- No diagnosis, severity grading or treatment advice — clinical decisions stay with health workers.
- No accounts, logins or multi-clinic management — irrelevant to the demo.
- No patient names or personal data.
- No paid cloud or AI services.

## Open Questions
- Which public dataset and licence (must be resolved in `4-spec`).
- Whether the dataset gives enough images per patient to reach 200 WBC in sample mode — check in `4-spec`; if not, sample mode may combine fields from one patient's slide only.
