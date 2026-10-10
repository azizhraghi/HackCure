"""Simulated cohort of uncomplicated recoveries, each with a full medical dossier.

No public dataset covers vital signs at home after surgery, so this generates
stand-in patients. EVERY NUMBER BELOW IS AN ASSUMPTION written by the
developers: the direction of each effect follows general expectations (a
disturbance after surgery that fades, slower in older and sicker patients and
after bigger operations; a beta blocker lowering heart rate), but the sizes
are not taken from patient data and have not been reviewed by a clinician.
A model trained on this is labelled "simulated" everywhere it is used.

The dossier shape is a placeholder for the JSON Developer 2 will provide.
When the real one arrives, make this generator emit the same fields.

Each patient gets a personal baseline per vital sign. After surgery the
value is pushed away from baseline and returns to it exponentially.
"""

import math
import random

from .dataset import Row, rows_from_patients

CONDITIONS = ("diabetes", "hypertension", "copd", "heart_failure")
MEDICATIONS = ("beta_blocker", "antihypertensive", "opioid", "corticosteroid", "anticoagulant")

# procedure: (HR rise beats/min, SpO2 drop %, temperature rise Cel, systolic change mmHg,
#             recovery time constant in days, typical duration in minutes)
PROCEDURES = {
    "laparoscopic_cholecystectomy": (8.0, 1.0, 0.4, -3.0, 2.0, 60),
    "hip_replacement": (12.0, 1.5, 0.5, -6.0, 4.0, 100),
    "colectomy": (15.0, 2.0, 0.6, -5.0, 5.0, 180),
    "lobectomy": (14.0, 3.5, 0.5, -4.0, 6.5, 160),
    "cabg": (18.0, 2.5, 0.5, -8.0, 7.0, 240),
}
# Procedures that can be done either way; the others have one fixed approach.
BOTH_APPROACHES = {"colectomy", "lobectomy"}

LAST_DAY = 30


def simulate_patients(n_patients: int = 1500, seed: int = 0) -> list[dict]:
    """Patients as {"patient_id", "dossier", "measurements"} records."""
    rng = random.Random(seed)
    patients = []
    for i in range(n_patients):
        age = round(min(90.0, max(18.0, rng.gauss(62, 14))))
        sex = rng.choice(["female", "male"])
        bmi = round(min(45.0, max(17.0, rng.gauss(27, 4.5))), 1)
        smoker = rng.random() < 0.2
        procedure = rng.choice(list(PROCEDURES))
        if procedure in BOTH_APPROACHES:
            approach = rng.choice(["open", "minimally_invasive"])
        else:
            approach = "minimally_invasive" if procedure == "laparoscopic_cholecystectomy" else "open"
        has = {c: rng.random() < p for c, p in zip(
            CONDITIONS, (0.20, 0.25 + 0.004 * (age - 40), 0.06 + 0.10 * smoker, 0.07))}
        takes = {
            "beta_blocker": rng.random() < (0.55 if has["heart_failure"] or procedure == "cabg" else 0.12),
            "antihypertensive": rng.random() < (0.8 if has["hypertension"] else 0.03),
            "opioid": rng.random() < 0.5,
            "corticosteroid": rng.random() < (0.3 if has["copd"] else 0.04),
            "anticoagulant": rng.random() < (0.6 if procedure in {"hip_replacement", "cabg"} else 0.15),
        }
        asa = min(4, 1 + sum(has.values()) + (age > 75) + (bmi >= 35))

        hr_up, spo2_down, temp_up, sbp_shift, tau, minutes = PROCEDURES[procedure]
        duration = round(minutes * rng.lognormvariate(0, 0.2))
        open_surgery = approach == "open" and procedure in BOTH_APPROACHES

        # How long the disturbance lasts, and how strong it is, for this patient.
        tau *= ((1 + 0.012 * (age - 60)) * (1.15 if has["diabetes"] else 1.0)
                * (1.10 if smoker else 1.0) * (1 + 0.08 * (asa - 2))
                * (1.20 if open_surgery else 1.0) * rng.lognormvariate(0, 0.2))
        tau = max(0.8, tau)
        size = rng.lognormvariate(0, 0.25) * (1.25 if open_surgery else 1.0) * (duration / minutes) ** 0.3

        baseline = {
            "hr": rng.gauss(72, 8) - (8 if takes["beta_blocker"] else 0),
            "spo2": min(99.5, 97.5 - 0.03 * (age - 50) - (2.5 if has["copd"] else 0)
                        - (0.6 if smoker else 0) + rng.gauss(0, 0.6)),
            "sbp": rng.gauss(122, 9) + 0.35 * (age - 50) + (12 if has["hypertension"] else 0)
                   - (7 if takes["antihypertensive"] else 0),
            "dbp": rng.gauss(77, 6) + (6 if has["hypertension"] else 0)
                   - (4 if takes["antihypertensive"] else 0),
            "temperature": rng.gauss(36.7, 0.2),
        }
        offset = {
            "hr": hr_up * size * (0.7 if takes["beta_blocker"] else 1.0),
            "spo2": -spo2_down * size * (1.3 if has["copd"] else 1.0)
                    * (1 + 0.02 * max(0.0, bmi - 25)) * (1.2 if takes["opioid"] else 1.0),
            "sbp": sbp_shift * size,
            "dbp": 0.5 * sbp_shift * size,
            "temperature": temp_up * size * (0.7 if takes["corticosteroid"] else 1.0),
        }
        noise = {"hr": 3.5, "spo2": 0.7, "sbp": 6.0, "dbp": 4.0, "temperature": 0.15}

        dossier = {
            "age": age, "sex": sex, "bmi": bmi, "asa_class": asa, "smoker": smoker,
            "surgery": {"procedure": procedure, "approach": approach,
                        "duration_minutes": duration, "urgency": "elective"},
            "conditions": [c for c in CONDITIONS if has[c]],
            "medications": [{"name": m} for m in MEDICATIONS if takes[m]],
        }
        # The baseline is not always on record; the model must cope without it.
        if rng.random() < 0.75:
            dossier["baseline"] = {k: round(v, 1) for k, v in baseline.items()}

        measurements = []
        for metric in baseline:
            t = tau * (0.5 if metric == "temperature" else 1.0)  # temperature settles faster
            for d in range(LAST_DAY + 1):
                day = d + rng.uniform(0.0, 0.9)
                value = baseline[metric] + offset[metric] * math.exp(-day / t) + rng.gauss(0, noise[metric])
                if metric == "spo2":
                    value = min(100.0, value)
                measurements.append({"metric": metric, "day": round(day, 3), "value": round(value, 1)})
        patients.append({"patient_id": f"sim_{i:05d}", "dossier": dossier, "measurements": measurements})
    return patients


def simulate_cohort(n_patients: int = 1500, seed: int = 0) -> list[Row]:
    return rows_from_patients(simulate_patients(n_patients, seed))
