"""A small made-up cohort, used only to test that the training code works.

The formulas below are invented for testing. They are not medical knowledge
and nothing here ships as the model's training data.
"""

import math
import random

from surgiguard_d1.trajectory import FeatureSpec, Row

SPEC = FeatureSpec(numeric=("age",), categorical=("procedure",), flags=("condition.fixture_a",))


def simulate(n_patients: int = 300, seed: int = 1) -> list[Row]:
    rng = random.Random(seed)
    rows: list[Row] = []
    for i in range(n_patients):
        age = rng.uniform(30, 85)
        procedure = rng.choice(["proc_a", "proc_b"])
        flag = rng.random() < 0.3
        common = dict(
            patient_id=f"sim_{i:04d}",
            numeric={"age": age},
            categorical={"procedure": procedure},
            flags=frozenset({"condition.fixture_a"}) if flag else frozenset(),
        )
        for d in range(15):
            day = d + rng.uniform(0, 0.5)
            hr = (70 + 15 * math.exp(-day / 3) * (1.4 if procedure == "proc_b" else 1.0)
                  + 0.15 * (age - 50) + (5 if flag else 0) + rng.gauss(0, 3))
            spo2 = min(100.0, 97.5 - 2.5 * math.exp(-day / 2) - 0.02 * (age - 50) + rng.gauss(0, 0.8))
            rows.append(Row(day=day, metric="hr", value=hr, **common))
            rows.append(Row(day=day, metric="spo2", value=spo2, **common))
    return rows
