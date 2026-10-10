import json
from datetime import date
from pathlib import Path

import pytest

from surgiguard_d1.legacy.trajectory_model import flatten
from surgiguard_d1.legacy.trajectory_model.d2 import dossier_from_d2, normalise_drug_class, normalise_procedure
from surgiguard_d1.legacy.twin_record import Episode, TwinInputs, build_snapshot

from .conftest import T0

SAMPLE = json.loads((Path(__file__).resolve().parents[1] / "examples" / "d2_sample.json").read_text())


def test_developer_2_sample_becomes_a_dossier():
    assert dossier_from_d2(SAMPLE) == {
        "age": 64,
        "surgery": {"procedure": "knee_replacement", "side": "right"},
        "medications": [{"name": "analgesic"}, {"name": "anticoagulant"}, {"name": "nsaid"}],
        "drugs": ["celecoxib", "enoxaparine_sodique", "paracetamol"],
        "medication_count": 3,
        "allergies": ["penicilline"],
    }


def test_age_is_counted_on_the_given_date():
    assert dossier_from_d2(SAMPLE, on=date(2026, 3, 14))["age"] == 64
    assert dossier_from_d2(SAMPLE, on=date(2026, 3, 15))["age"] == 65


def test_nothing_identifying_reaches_the_model_or_the_twin():
    dossier = dossier_from_d2(SAMPLE)
    profile = flatten(dossier)
    episode = Episode(patient_id="pt_demo_001", episode_id="ep_demo_001", surgery_at=T0,
                      discharge_at=None, timezone="Europe/Paris")
    snap = build_snapshot(TwinInputs(episode=episode, dossier=dossier), T0)
    for text in (str(dossier), str(profile), snap.model_dump_json()):
        for secret in ("MILLER", "Sarah", "Ruiz", "1961", "15/03", "Doliprane"):
            assert secret not in text
    assert profile.flags >= {"medications.nsaid", "medications.anticoagulant",
                             "drugs.celecoxib", "allergies.penicilline"}
    assert profile.categorical == {"surgery.procedure": "knee_replacement", "surgery.side": "right"}


@pytest.mark.parametrize("text, expected", [
    ("Prothèse Totale du Genou Droite", ("knee_replacement", "right")),
    ("PTG gauche", ("knee_replacement", "left")),
    ("Prothèse totale de hanche", ("hip_replacement", None)),
    ("Cholécystectomie par cœlioscopie", ("laparoscopic_cholecystectomy", None)),
    ("Colectomie droite", ("colectomy", "right")),
    ("Arthroscopie de l'épaule gauche", ("arthroscopie_de_l'epaule", "left")),
])
def test_french_surgery_wording_is_normalised(text, expected):
    assert normalise_procedure(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("Analgésique", "analgesic"), ("AINS COX-2", "nsaid"), ("HBPM", "anticoagulant"),
    ("Bêtabloquant", "beta_blocker"), ("Opioïde faible", "opioid"), ("Statine", "statine"),
    (None, None),
])
def test_french_drug_classes_are_normalised(text, expected):
    assert normalise_drug_class(text) == expected


def test_missing_fields_are_left_out_not_invented():
    assert dossier_from_d2({"extraction": {"surgery_type": "PTG"}}) == {
        "surgery": {"procedure": "knee_replacement"}, "medications": [], "drugs": [],
        "medication_count": 0, "allergies": []}
