# Wound-attribute model (D1-F) — model card

**What it does.** From one photo of a surgical wound, estimates six attributes that surgeons annotate: redness, swelling,
discharge, healing status, infection-risk rating and urgency. Each answer is *yes / no / uncertain* with a probability,
plus an evidence map showing which parts of the photo pushed the redness score up.

**What it is not.** Not a diagnosis, not a medical device. It never closes or downgrades a case: a "yes" on discharge,
risk or urgency can only ADD a reason for the clinician to look; a "no" removes nothing. Urgent symptoms go through the
rule-based urgent lane, which never waits for this model.

## Data
- **SurgWound** (Hugging Face `Sonulee/SurgWound`, licence **CC BY-SA 4.0**; SurgWound-Bench, arXiv 2508.15189):
  686 usable surgical-wound photos, each labelled by surgical experts at The Ohio State University Wexner Medical Center.
- Official split kept: **train 480 + val 69** for every training decision, **test 137 used once** at the end.
- Labels marked *Uncertain* by the annotators are left out of that attribute (never guessed).
- Caveat: images were collected from public online sources (variable cameras, light, framing, skin tones); performance
  on our patients' phone photos is **not yet measured**.

## Method (CPU, ~15 min, no fine-tuning of the encoder)
1. Frozen image encoder; features = [CLS token, mean of patch tokens], averaged with the mirror image.
   Encoder chosen by **cross-validation on train+val only**: CLIP ViT-B/16 (mean CV AUROC 0.817)
   vs DINOv2-small (0.75). Encoder in use: `openai/clip-vit-base-patch16`.
2. One class-balanced, L2-regularised logistic regression per attribute (regularisation chosen by 5-fold CV AUROC).
3. Operating threshold chosen on out-of-fold predictions for **sensitivity ≥ 0.85** (missing a sign is worse than a
   false alarm), and an **uncertain band** (±0.05 around the threshold) where the model abstains.
4. Explanation: **occlusion sensitivity** — each cell of a 7×7 grid is greyed out and the drop in the redness score is
   measured; the heat map shows which regions the decision depended on. (Raw CLIP patch-token attributions were tried
   first and rejected: they highlighted the background, a known artefact.)

Why this design: 549 labelled photos are too few to fine-tune a large network without over-fitting; a frozen
pre-trained encoder + linear heads is the standard, reproducible approach for small medical datasets, trains on a laptop,
and stays explainable.

## Results on the untouched test split
| Attribute | Test n (positives) | AUROC [95 % CI, bootstrap] | CV AUROC | Sens / Spec (all photos) | Sens / Spec (after abstaining) | Abstained |
|---|---|---|---|---|---|---|
| Redness (erythema) | 131 (40+) | **0.759** [0.665–0.839] | 0.748 | 0.9 / 0.462 | 0.914 / 0.452 | 17.6 % |
| Swelling (edema) | 115 (21+) | **0.767** [0.65–0.865] | 0.77 | 0.81 / 0.574 | 0.85 / 0.556 | 20.0 % |
| Discharge (exudate: serous, sanguineous, purulent) | 125 (16+) | **0.818** [0.692–0.922] | 0.855 | 0.75 / 0.633 | 0.857 / 0.649 | 13.6 % |
| Not yet healed | 137 (55+) | **0.771** [0.687–0.844] | 0.835 | 0.818 / 0.512 | 0.824 / 0.521 | 10.9 % |
| Infection-risk rating medium/high | 137 (20+) | **0.843** [0.746–0.929] | 0.856 | 0.9 / 0.675 | 0.889 / 0.68 | 11.7 % |
| Urgency: clinic or emergency (vs home care) | 137 (16+) | **0.823** [0.703–0.917] | 0.841 | 0.812 / 0.653 | 0.812 / 0.649 | 7.3 % |

- Baseline for redness: the OpenCV redness measure we used before this model scores **AUROC 0.503**
  on the same test photos (chance level); the trained model scores **0.759**.
- A majority-class predictor has balanced accuracy 0.5 on every attribute.
- Small positive counts (e.g. 16 photos with discharge in the test split) give wide confidence intervals: they are
  reported, not hidden.

## Known limits / what we would do next
- Validate on our own consented patient photos (same phone, same lighting guidance) before any clinical use.
- More labelled surgical wounds, especially discharge and high-risk cases; per-skin-tone performance analysis.
- The attributes are what *surgeons labelled from a photo*; warmth, pain, smell and depth cannot be seen.

Reproduce: `python scripts/prepare_surgwound.py <hf json files> <prep>` then `python scripts/train_wound_model.py <prep>`
(metrics in `models/wound_model_metrics.json`, heads in `models/wound_heads.joblib`, ~100 KB).
