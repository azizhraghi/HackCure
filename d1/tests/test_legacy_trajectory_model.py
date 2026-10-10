import pytest

from surgiguard_d1.legacy.trajectory_model import (
    PatientProfile, TrajectoryModel, evaluate, load_csv, save_csv, split_by_patient,
)

from .sim_cohort import SPEC, simulate

DAYS = [0.0, 1.0, 3.0, 7.0, 14.0]


@pytest.fixture(scope="module")
def data():
    return split_by_patient(simulate(), test_fraction=0.2, seed=0)


@pytest.fixture(scope="module")
def model(data):
    return TrajectoryModel(SPEC, data_origin="simulated").fit(data[0])


def profile(age=60.0, procedure="proc_a", flag=False):
    return PatientProfile({"age": age}, {"procedure": procedure},
                          frozenset({"condition.fixture_a"}) if flag else frozenset())


def test_no_patient_is_in_both_train_and_test(data):
    train, test = data
    assert not {r.patient_id for r in train} & {r.patient_id for r in test}
    assert len({r.patient_id for r in test}) == 60


def test_it_learns_the_shape_of_recovery(model):
    t = model.predict(profile(), "hr", DAYS)
    assert t.status == "available" and t.unit == "beats/min"
    medians = [p.median for p in t.points]
    assert medians[0] > medians[2] > medians[4]  # settles after surgery
    assert all(p.lower <= p.median <= p.upper for p in t.points)


def test_it_uses_the_patient_background(model):
    def day1(**kw):
        return model.predict(profile(**kw), "hr", [1.0]).points[0].median

    assert day1(age=80) > day1(age=40) + 3
    assert day1(procedure="proc_b") > day1(procedure="proc_a") + 2
    assert day1(flag=True) > day1(flag=False) + 2


def test_on_unseen_patients_it_beats_ignoring_the_background(model, data):
    report = evaluate(model, *data)
    for metric in ("hr", "spo2"):
        r = report[metric]
        # a few test patients are older or younger than anyone in training
        assert r["n"] > 500 and r["abstained"] < 0.1 * r["n"]
        assert r["mae"] < r["baseline_mae"]
        assert 0.70 <= r["band_coverage"] <= 0.90  # the band is meant to hold ~80%


def test_it_abstains_for_patients_unlike_the_training_ones(model):
    def why(p, metric="hr", days=DAYS):
        t = model.predict(p, metric, days)
        assert t.status == "abstained" and t.points == []
        return " ".join(t.reasons)

    assert "not in training data" in why(profile(procedure="proc_unknown"))
    assert "outside trained range" in why(profile(age=12))
    assert "no model trained" in why(profile(), metric="temperature")
    assert "not provided" in why(PatientProfile({}, {"procedure": "proc_a"}))
    assert "no requested day" in why(profile(), days=[60.0])


def test_days_beyond_the_training_data_are_dropped_not_extrapolated(model):
    t = model.predict(profile(), "hr", [1.0, 5.0, 40.0])
    assert [p.day for p in t.points] == [1.0, 5.0]
    assert "omitted" in t.reasons[0]


def test_too_few_patients_means_no_model():
    few = [r for r in simulate(20)]
    m = TrajectoryModel(SPEC, "simulated").fit(few, min_patients=30)
    assert m.predict(profile(), "hr", DAYS).status == "abstained"


def test_saved_model_predicts_the_same_and_records_where_it_came_from(model, tmp_path):
    model.save(tmp_path)
    loaded = TrajectoryModel.load(tmp_path)
    assert loaded.predict(profile(), "hr", DAYS) == model.predict(profile(), "hr", DAYS)
    manifest = loaded.manifest()
    assert manifest["data_origin"] == "simulated"
    assert manifest["metrics"]["hr"]["patients"] == 240
    assert len(manifest["training_data_sha256"]) == 64

    (tmp_path / "model.joblib").write_bytes(b"tampered")
    with pytest.raises(ValueError):
        TrajectoryModel.load(tmp_path)


def test_csv_round_trip(tmp_path):
    rows = simulate(5)
    save_csv(rows, tmp_path / "cohort.csv", SPEC)
    assert load_csv(tmp_path / "cohort.csv", SPEC) == rows



# ------------------------------ shipped simulated cohort, full dossiers

from surgiguard_d1.legacy.trajectory_model import FeatureSpec, flatten, load_jsonl, rows_from_patients, save_jsonl  # noqa: E402
from surgiguard_d1.legacy.trajectory_model.simulate import LAST_DAY, PROCEDURES, simulate_patients  # noqa: E402

DOSSIER = {
    "patient_id": "pt_x", "age": 65, "sex": "Male", "bmi": 27.0, "asa_class": 2, "smoker": False,
    "surgery": {"procedure": "Colectomy", "approach": "open", "duration_minutes": 180,
                "urgency": "elective", "surgery_date": "2026-10-07"},
    "conditions": [], "medications": [],
}


def with_(**changes):
    d = {**DOSSIER, **{k: v for k, v in changes.items() if k != "surgery"}}
    d["surgery"] = {**DOSSIER["surgery"], **changes.get("surgery", {})}
    return flatten(d)


@pytest.fixture(scope="module")
def sim_model():
    rows = [r for r in rows_from_patients(simulate_patients(500, seed=3)) if r.metric in {"hr", "spo2"}]
    return TrajectoryModel(FeatureSpec.infer(rows), "simulated").fit(rows)


def test_whole_dossier_is_read_and_identifiers_are_skipped():
    p = flatten({**DOSSIER, "smoker": True, "conditions": ["Diabetes", "COPD"],
                 "medications": [{"name": "Beta blocker", "dose": "5 mg"}],
                 "baseline": {"hr": 70}})
    assert p.numeric == {"age": 65.0, "bmi": 27.0, "asa_class": 2.0,
                         "surgery.duration_minutes": 180.0, "baseline.hr": 70.0}
    assert p.categorical == {"sex": "male", "surgery.procedure": "colectomy",
                             "surgery.approach": "open", "surgery.urgency": "elective"}
    assert p.flags == {"smoker", "conditions.diabetes", "conditions.copd", "medications.beta_blocker"}


def test_simulated_cohort_is_reproducible_and_covers_every_procedure():
    assert simulate_patients(20, seed=5) == simulate_patients(20, seed=5)
    patients = simulate_patients(200, seed=5)
    assert {p["dossier"]["surgery"]["procedure"] for p in patients} == set(PROCEDURES)
    rows = rows_from_patients(patients)
    assert {r.metric for r in rows} == {"hr", "spo2", "sbp", "dbp", "temperature"}
    assert max(r.day for r in rows) < LAST_DAY + 1
    assert all(r.value <= 100 for r in rows if r.metric == "spo2")


def test_features_are_discovered_from_the_training_dossiers(sim_model):
    spec = sim_model.spec
    assert spec.categorical == ("surgery.procedure",) and spec.numeric == ("age",)
    assert {"bmi", "asa_class", "baseline.hr", "surgery.duration_minutes"} <= set(spec.optional_numeric)
    assert {"sex", "surgery.approach"} <= set(spec.optional_categorical)
    assert {"medications.beta_blocker", "conditions.diabetes", "smoker"} <= set(spec.flags)


def test_medications_status_and_surgery_details_change_the_prediction(sim_model):
    def hr(day, profile):
        return sim_model.predict(profile, "hr", [day]).points[0].median

    def spo2(day, profile):
        return sim_model.predict(profile, "spo2", [day]).points[0].median

    plain = with_()
    assert hr(1.0, with_(medications=[{"name": "beta_blocker"}])) < hr(1.0, plain) - 3
    assert hr(2.0, with_(surgery={"approach": "minimally_invasive"})) < hr(2.0, plain)
    assert spo2(1.0, with_(surgery={"procedure": "lobectomy"})) < spo2(
        1.0, with_(surgery={"procedure": "laparoscopic_cholecystectomy", "approach": "minimally_invasive"}))
    assert spo2(25.0, plain) > spo2(1.0, plain)  # recovers over time


def test_patients_own_baseline_personalises_the_curve_and_is_optional(sim_model):
    def day20(**kw):
        return sim_model.predict(with_(**kw), "hr", [20.0]).points[0]

    low, high, unknown = day20(baseline={"hr": 60}), day20(baseline={"hr": 85}), day20()
    assert high.median > low.median + 15  # late recovery sits near the patient's own normal
    assert low.median < unknown.median < high.median
    assert (high.upper - high.lower) < (unknown.upper - unknown.lower)


def test_it_reports_which_dossier_fields_it_could_not_use(sim_model):
    t = sim_model.predict(
        with_(medications=[{"name": "metformin"}], allergies=["penicillin"], sex="other"), "hr", [3.0])
    assert t.status == "available"
    assert {"medications.metformin", "allergies.penicillin", "sex=other"} <= set(t.unused_inputs)
    assert {"age", "bmi", "surgery.procedure", "surgery.approach"} <= set(t.used_inputs)


def test_unknown_procedure_or_missing_age_still_means_no_prediction(sim_model):
    t = sim_model.predict(with_(surgery={"procedure": "appendectomy"}), "hr", [3.0])
    assert t.status == "abstained" and "not in training data" in t.reasons[0]
    no_age = flatten({k: v for k, v in DOSSIER.items() if k != "age"})
    assert "age not provided" in sim_model.predict(no_age, "hr", [3.0]).reasons[0]


def test_patient_file_round_trip(tmp_path):
    patients = simulate_patients(5, seed=1)
    save_jsonl(patients, tmp_path / "patients.jsonl")
    assert load_jsonl(tmp_path / "patients.jsonl") == rows_from_patients(patients)
