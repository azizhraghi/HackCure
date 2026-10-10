from datetime import datetime, timedelta, timezone

import pytest

from surgiguard_d1.physiology import CodeConfig, PhysiologyConfig, analyze_physiology
from surgiguard_d1.legacy.twin_record import (
    AnalysisInput,
    ApprovedMilestone,
    Episode,
    MedicationReport,
    ProtocolView,
    StaleInputError,
    SymptomReport,
    TwinInputs,
    TwinStore,
    VersionConflictError,
    build_snapshot,
    caregiver_view,
    clinician_view,
    patient_view,
)
from surgiguard_d1.legacy.twin_record.timeline import calendar_days_between

from .conftest import T0, make_obs

EPISODE = Episode(
    patient_id="pt_demo_001",
    episode_id="ep_demo_001",
    surgery_at=T0 - timedelta(days=3),
    discharge_at=T0 - timedelta(days=1),
    timezone="Africa/Algiers",
)
PROTOCOL = ProtocolView(
    protocol_id="protocol_demo",
    version="protocol_demo_v1",
    milestones=[
        ApprovedMilestone(milestone_id="ms_walk", version="1", label="Fixture milestone A",
                          expected_from_day=1, expected_to_day=2),
        ApprovedMilestone(milestone_id="ms_stairs", version="1", label="Fixture milestone B",
                          expected_from_day=7, expected_to_day=14),
    ],
    dimension_references={"physiological_trends": "ref_demo_vitals"},
)


def physiology(n_points=5, at=T0 + timedelta(hours=1), bump=0):
    cfg = PhysiologyConfig(codes={"hr": CodeConfig(), "spo2": CodeConfig()})
    obs = [make_obs(i, {"hr": 70 + i + bump}, minutes=10 * i) for i in range(n_points)]
    run = analyze_physiology(obs, cfg, at, timedelta(hours=24))
    return AnalysisInput.from_payload(run.payload, run.input_watermark)


def symptom(n, minutes, pain=None, mood="okay", items=(), answers=(), status="structured", confirmed=True):
    at = T0 + timedelta(minutes=minutes)
    return SymptomReport(
        event_id=f"ev_sym_{n}", occurred_at=at, received_at=at + timedelta(seconds=5),
        report_id=f"sym_{n}", original_report_ref=f"raw_sym_{n}", mood_label=mood,
        pain_score=pain, items=list(items), warning_answers=list(answers),
        extraction_status=status, confirmed_by_patient=confirmed,
    )


def medication(n, minutes, status="taken", symptoms=()):
    at = T0 + timedelta(minutes=minutes)
    return MedicationReport(
        event_id=f"ev_med_{n}", occurred_at=at, received_at=at + timedelta(seconds=5),
        report_id=f"med_{n}", prescription_id="rx_demo_001", scheduled_dose_id=f"dose_{n}",
        reported_status=status, reported_taken_at=at if status == "taken" else None,
        reporter_id="pt_demo_001", symptom_report_ids=list(symptoms),
    )


def inputs(**kw):
    return TwinInputs(episode=EPISODE, protocol=PROTOCOL, **kw)


NOW = T0 + timedelta(hours=2)


# ------------------------------------------------------------- content


def test_empty_episode_has_every_dimension_as_no_data_never_normal():
    snap = build_snapshot(TwinInputs(episode=EPISODE), NOW)
    assert len(snap.dimensions) == 7
    for d in snap.dimensions:
        if d.name != "recovery_timeline":
            assert d.status == "no_data" and d.missing
    assert snap.dimension("recovery_timeline").missing == ["no active approved protocol"]
    assert snap.protocol_version is None


def test_there_is_no_overall_score_anywhere():
    snap = build_snapshot(inputs(analyses=[physiology()]), NOW)
    dumped = clinician_view(snap)
    assert not {"score", "recovery_score", "risk", "risk_score"} & set(dumped)
    assert snap.forecasts == []


def test_physiology_keeps_measurement_and_calculation_apart():
    dim = build_snapshot(inputs(analyses=[physiology()]), NOW).dimension("physiological_trends")
    by_code = {s.code: s for s in dim.metric_summaries}
    assert by_code["hr"].basis == "observation" and by_code["hr"].value == 74
    assert by_code["hr.window_median"].basis == "derived_summary"
    assert by_code["hr.slope"].unit == "beats/min/h"
    assert dim.status == "limited"  # spo2 was expected and never arrived
    assert dim.missing == ["spo2: no_recent_measurement"]
    assert dim.reference_id == "ref_demo_vitals"
    assert dim.latest_observed_at == T0 + timedelta(minutes=40)


def test_symptoms_unknown_is_not_absent():
    report = symptom(
        1, 30, pain=None,
        items=[{"code": "dizziness", "assertion": "uncertain"}],
        status="needs_clarification", confirmed=False,
    )
    dim = build_snapshot(inputs(symptom_reports=[report]), NOW).dimension("pain_symptoms")
    by_code = {s.code: s for s in dim.metric_summaries}
    assert by_code["symptom.dizziness"].value == "uncertain"
    assert by_code["warning_answers"].detail["answered"] == 0
    assert dim.status == "limited"
    assert "pain score not given" in dim.missing
    assert "warning questions not answered" in dim.missing


def test_pain_change_compares_with_the_previous_report():
    reports = [symptom(1, 0, pain=3), symptom(2, 60, pain=6)]
    dim = build_snapshot(inputs(symptom_reports=reports), NOW).dimension("pain_symptoms")
    by_code = {s.code: s for s in dim.metric_summaries}
    assert by_code["pain_score"].value == 6 and by_code["pain_score"].basis == "reported"
    assert by_code["pain_score.change_from_previous"].value == 3
    assert dim.evidence_ids == ["evref_sym_1", "evref_sym_2"]


def test_medication_is_reported_and_unreported_doses_are_not_missed():
    reports = [medication(1, 0), medication(2, 60, "missed"), medication(3, 120, "unsure", ["sym_9"])]
    dim = build_snapshot(inputs(medication_reports=reports), NOW).dimension("medication")
    by_code = {s.code: s for s in dim.metric_summaries}
    assert {k: by_code[f"reports.{k}"].value for k in ("taken", "missed", "unsure")} == {
        "taken": 1, "missed": 1, "unsure": 1}
    assert all(s.basis == "reported" for s in dim.metric_summaries)
    assert by_code["linked_symptom_reports"].detail["symptom_report_ids"] == ["sym_9"]
    assert dim.quality.reasons == ["reported_not_verified"]


def test_other_analyses_are_labelled_as_model_estimates():
    wound = AnalysisInput(
        analysis_id="an_wound_1", analysis_type="wound", status="limited",
        observations=[{"code": "visible_redness_change", "value": "review_suggested",
                       "comparable": False}],
        quality={"status": "limited", "reasons": ["lighting_differs"], "usable_for": ["clinician_review"]},
        evidence=[], limitations=["Colour comparison not defensible."],
        model_version="wound-0.0.1", created_at=T0,
    )
    dim = build_snapshot(inputs(analyses=[wound]), NOW).dimension("wound_visual_changes")
    assert dim.metric_summaries[0].basis == "model_estimate"
    assert dim.metric_summaries[0].detail == {"comparable": False}
    assert dim.status == "limited"


def test_postoperative_day_follows_the_patient_calendar():
    surgery = datetime(2026, 10, 7, 22, 30, tzinfo=timezone.utc)  # 23:30 in Algiers
    just_after = datetime(2026, 10, 7, 23, 30, tzinfo=timezone.utc)  # 00:30 next day there
    assert calendar_days_between(surgery, just_after, "Africa/Algiers") == 1
    assert calendar_days_between(surgery, just_after, "UTC") == 0


def test_milestones_show_calendar_position_without_claiming_achievement():
    dim = build_snapshot(inputs(), NOW).dimension("recovery_timeline")
    by_code = {s.code: s for s in dim.metric_summaries}
    assert by_code["postoperative_day"].value == 3
    assert by_code["days_since_discharge"].value == 1
    assert by_code["milestone.ms_walk"].basis == "approved_expectation"
    assert by_code["milestone.ms_walk"].detail["timing"] == "after_window"
    assert by_code["milestone.ms_stairs"].detail["timing"] == "before_window"
    assert not any("achieved" in str(s.detail) for s in dim.metric_summaries)


# ----------------------------------------------------------- versioning


def test_versions_increase_and_old_snapshots_stay_readable():
    store = TwinStore()
    v1 = store.update(inputs(analyses=[physiology()]), NOW)
    v2 = store.update(inputs(analyses=[physiology()], symptom_reports=[symptom(1, 90, pain=4)]), NOW)
    assert (v1.snapshot_version, v2.snapshot_version) == (1, 2)
    assert (v1.recompute_reason, v2.recompute_reason) == ("initial", "new_input")
    assert v2.changed_dimensions == ["pain_symptoms"]
    assert v2.previous_snapshot_id == v1.snapshot_id
    assert store.get(v1.snapshot_id) == v1
    assert store.get(v1.snapshot_id).dimension("pain_symptoms").status == "no_data"


def test_rebuilding_with_the_same_inputs_creates_no_new_version():
    store = TwinStore()
    data = inputs(analyses=[physiology()], symptom_reports=[symptom(1, 30, pain=2)])
    first = store.update(data, NOW)
    again = store.update(
        inputs(analyses=[physiology()], symptom_reports=[symptom(1, 30, pain=2)] * 3),
        NOW + timedelta(minutes=5),
    )
    assert again is first
    assert len(store.history("ep_demo_001")) == 1


def test_rebuild_from_scratch_reproduces_the_stored_snapshot():
    data = inputs(analyses=[physiology()], medication_reports=[medication(1, 10)])
    a = build_snapshot(data, NOW)
    b = build_snapshot(data, NOW)
    assert a == b and a.content_hash == b.content_hash


def test_correction_recomputes_only_the_affected_dimension():
    store = TwinStore()
    sym = [symptom(1, 30, pain=2)]
    store.update(inputs(analyses=[physiology()], symptom_reports=sym), NOW)
    corrected = physiology(at=T0 + timedelta(hours=1, minutes=30), bump=5)
    v2 = store.update(inputs(analyses=[physiology(), corrected], symptom_reports=sym), NOW, "correction")
    assert v2.recompute_reason == "correction"
    assert v2.changed_dimensions == ["physiological_trends"]


def test_older_job_cannot_replace_a_newer_snapshot():
    store = TwinStore()
    old = inputs(symptom_reports=[symptom(1, 0, pain=2)])
    new = inputs(symptom_reports=[symptom(1, 0, pain=2), symptom(2, 60, pain=5)])
    store.update(new, NOW)
    with pytest.raises(StaleInputError):
        store.update(old, NOW)

    # Two jobs that both started from version 1: the second to finish is refused.
    racing = build_snapshot(
        inputs(symptom_reports=[*new.symptom_reports, symptom(3, 70, pain=6)]), NOW, store.latest("ep_demo_001"))
    store.append(racing)
    with pytest.raises(VersionConflictError):
        store.append(racing)


def test_protocol_change_and_new_day_are_named_as_the_reason():
    store = TwinStore()
    store.update(inputs(), NOW)
    v2 = store.update(inputs(), NOW + timedelta(days=1))
    assert v2.recompute_reason == "time_advanced"
    newer = PROTOCOL.model_copy(update={"version": "protocol_demo_v2"})
    v3 = store.update(TwinInputs(episode=EPISODE, protocol=newer), NOW + timedelta(days=1))
    assert v3.recompute_reason == "protocol_change"
    assert v3.protocol_version == "protocol_demo_v2"


# ---------------------------------------------------------------- views


def full_snapshot():
    return build_snapshot(
        inputs(analyses=[physiology()], symptom_reports=[symptom(1, 30, pain=4)],
               medication_reports=[medication(1, 10)]),
        NOW,
    )


def test_event_payload_matches_the_shared_contract_fields():
    payload = full_snapshot().event_payload()
    assert set(payload) == {
        "snapshot_id", "snapshot_version", "as_of", "input_watermark", "protocol_version",
        "dimensions", "forecasts", "evidence", "limitations"}
    assert {"name", "status", "metric_summaries", "latest_observed_at", "reference_id"} <= set(
        payload["dimensions"][0])


def test_patient_view_hides_statistics_and_evidence():
    view = patient_view(full_snapshot())
    assert "evidence" not in view
    codes = [i["code"] for d in view["dimensions"] for i in d["items"]]
    assert "hr" in codes and "pain_score" in codes
    assert "hr.slope" not in codes and "hr.window_median" not in codes


def test_caregiver_sees_only_granted_dimensions():
    snap = full_snapshot()
    view = caregiver_view(snap, {"recovery_timeline", "pain_symptoms"})
    assert [d["name"] for d in view["dimensions"]] == ["pain_symptoms", "recovery_timeline"]
    assert "rx_demo_001" not in str(view)
    assert caregiver_view(snap, set())["dimensions"] == []


# ------------------------------------- patient background via D2's protocol

from surgiguard_d1.legacy.twin_record import ContextItem, MetricReference, physiology_config  # noqa: E402

PERSONALISED = PROTOCOL.model_copy(update={
    "procedure": "Fixture procedure",
    "patient_context": [
        ContextItem(code="age", label="Age", value=68, unit="a"),
        ContextItem(code="condition.fixture_a", label="Fixture condition A", value="present"),
    ],
    "metric_references": {
        "hr": MetricReference(reference_id="ref_demo_hr", version="1", lower=50, upper=100,
                              baseline=70, expected_interval_minutes=30),
    },
})


def test_patient_background_is_shown_as_clinical_record_from_the_protocol():
    snap = build_snapshot(TwinInputs(episode=EPISODE, protocol=PERSONALISED), NOW)
    assert snap.context.procedure == "Fixture procedure"
    assert [(i.code, i.value, i.basis) for i in snap.context.items] == [
        ("age", 68, "clinical_record"), ("condition.fixture_a", "present", "clinical_record")]
    ev = next(e for e in snap.evidence if e.evidence_id == snap.context.evidence_ids[0])
    assert (ev.kind, ev.resource_version, ev.locator) == ("protocol", "protocol_demo_v1", "patient_context")


def test_missing_background_is_stated():
    assert build_snapshot(TwinInputs(episode=EPISODE), NOW).context.missing == [
        "no active approved protocol"]
    assert build_snapshot(inputs(), NOW).context.missing == [
        "procedure not stated", "no patient background supplied"]


def test_baseline_and_range_from_the_protocol_drive_the_vital_sign_comparison():
    cfg = physiology_config(PERSONALISED)
    assert cfg.protocol_version == "protocol_demo_v1"
    assert cfg.codes["hr"].max_gap == timedelta(minutes=30)

    obs = [make_obs(i, {"hr": 80 + i}, minutes=10 * i) for i in range(5)]
    run = analyze_physiology(obs, cfg, T0 + timedelta(hours=1), timedelta(hours=24))
    analysis = AnalysisInput.from_payload(run.payload, run.input_watermark)
    dim = build_snapshot(
        TwinInputs(episode=EPISODE, protocol=PERSONALISED, analyses=[analysis]), NOW
    ).dimension("physiological_trends")
    by_code = {s.code: s for s in dim.metric_summaries}

    assert by_code["hr.vs_reference"].value == "within"
    assert by_code["hr.vs_reference"].detail["change_from_baseline"] == pytest.approx(12.0)
    approved = by_code["hr.approved_reference"]
    assert approved.basis == "approved_expectation"
    assert approved.detail["baseline"] == 70 and approved.reference_id == "ref_demo_hr"


def test_changed_background_arrives_as_a_protocol_change():
    store = TwinStore()
    store.update(TwinInputs(episode=EPISODE, protocol=PERSONALISED), NOW)
    revised = PERSONALISED.model_copy(update={
        "version": "protocol_demo_v2",
        "patient_context": [ContextItem(code="age", label="Age", value=69, unit="a")]})
    v2 = store.update(TwinInputs(episode=EPISODE, protocol=revised), NOW)
    assert v2.recompute_reason == "protocol_change"
    assert v2.context.items[0].value == 69
    assert store.history("ep_demo_001")[0].context.items[0].value == 68


def test_background_is_not_in_patient_or_caregiver_views():
    snap = build_snapshot(TwinInputs(episode=EPISODE, protocol=PERSONALISED), NOW)
    assert "context" in clinician_view(snap)
    assert "Fixture condition A" not in str(caregiver_view(snap, {"recovery_timeline", "pain_symptoms"}))
    assert "context" not in patient_view(snap)


# --------------------------------------- predicted normal trajectory

from surgiguard_d1.legacy.trajectory_model import TrajectoryModel  # noqa: E402
from surgiguard_d1.legacy.twin_record import dossier_from_protocol, predict_expected  # noqa: E402

from .sim_cohort import SPEC, simulate  # noqa: E402

KNOWN = PERSONALISED.model_copy(update={
    "procedure": "proc_a",
    "patient_context": [ContextItem(code="age", label="Age", value=68, unit="a"),
                        ContextItem(code="condition.fixture_a", label="Fixture condition A", value="present")],
})


@pytest.fixture(scope="module")
def trajectory_model():
    return TrajectoryModel(SPEC, "simulated").fit(simulate(200))


def twin_with_hr(model, protocol, hr):
    obs = [make_obs(i, {"hr": hr + i * 0.1}, minutes=10 * i) for i in range(5)]
    run = analyze_physiology(obs, physiology_config(protocol), T0 + timedelta(hours=1), timedelta(hours=24))
    expected = predict_expected(
        model, dossier_from_protocol(protocol), ["hr", "temperature"], [float(d) for d in range(15)])
    return build_snapshot(TwinInputs(
        episode=EPISODE, protocol=protocol, expected=expected,
        analyses=[AnalysisInput.from_payload(run.payload, run.input_watermark)]), NOW)


def test_without_a_dossier_one_is_built_from_the_protocol():
    assert dossier_from_protocol(KNOWN) == {
        "procedure": "proc_a", "age": 68, "condition.fixture_a": True, "baseline": {"hr": 70}}


def test_dossier_is_shown_in_full_as_the_patient_context():
    dossier = {"patient_id": "pt_demo_001", "age": 68, "sex": "male", "smoker": True,
               "surgery": {"procedure": "colectomy", "surgery_date": "2026-10-07"},
               "medications": [{"name": "beta_blocker", "dose": "fixture"}]}
    snap = build_snapshot(TwinInputs(episode=EPISODE, protocol=PROTOCOL, dossier=dossier), NOW)
    assert snap.context.procedure == "colectomy"
    assert {(i.code, i.value) for i in snap.context.items} == {
        ("age", 68.0), ("sex", "male"), ("smoker", "yes"), ("surgery.procedure", "colectomy"),
        ("medications.beta_blocker", "yes")}
    assert all(i.basis == "clinical_record" for i in snap.context.items)
    assert "pt_demo_001" not in str([i.model_dump() for i in snap.context.items])

    changed = build_snapshot(
        TwinInputs(episode=EPISODE, protocol=PROTOCOL, dossier={**dossier, "age": 69}), NOW, snap)
    assert changed.snapshot_version == 2  # a changed dossier is a new version


def test_reading_is_placed_on_the_predicted_normal_curve(trajectory_model):
    snap = twin_with_hr(trajectory_model, KNOWN, hr=120)
    by_code = {s.code: s for s in snap.dimension("physiological_trends").metric_summaries}
    expected = by_code["hr.expected"]
    assert expected.basis == "model_estimate"
    assert expected.detail["data_origin"] == "simulated"
    assert expected.detail["lower"] < expected.value < expected.detail["upper"]
    assert expected.detail["day"] == pytest.approx(3.03, abs=0.01)
    assert by_code["hr.vs_expected"].value == "above"
    assert by_code["hr.vs_expected"].detail["difference_from_expected"] > 20

    typical = twin_with_hr(trajectory_model, KNOWN, hr=expected.value)
    assert {s.code: s for s in typical.dimension("physiological_trends").metric_summaries}[
        "hr.vs_expected"].value == "within"


def test_snapshot_carries_the_whole_curve_and_says_what_it_was_learned_from(trajectory_model):
    snap = twin_with_hr(trajectory_model, KNOWN, hr=80)
    hr = next(t for t in snap.expected_trajectories if t.metric == "hr")
    assert len(hr.points) == 15 and hr.training_patients == 200
    assert snap.pipeline_versions["trajectory_model"] == hr.model_version
    assert any("simulated patient data" in x for x in snap.limitations)
    assert "expected_trajectories" not in snap.event_payload()


def test_when_the_model_abstains_the_twin_says_so_and_makes_no_comparison(trajectory_model):
    unknown = KNOWN.model_copy(update={"procedure": "proc_never_seen"})
    dim = twin_with_hr(trajectory_model, unknown, hr=80).dimension("physiological_trends")
    assert not any(s.code.endswith("expected") for s in dim.metric_summaries)
    assert any("hr: no expected trajectory" in m and "not in training data" in m for m in dim.missing)
    assert any("temperature: no expected trajectory" in m for m in dim.missing)


# ------------------------------------------------- near-term forecasts

from surgiguard_d1.patient_twin import PersistenceForecaster, forecast_metric  # noqa: E402
from surgiguard_d1.physiology import build_series  # noqa: E402


def test_forecasts_travel_with_the_snapshot_and_an_abstention_is_kept_visible():
    cfg = physiology_config(KNOWN)
    long = [make_obs(i, {"hr": 80 + (i % 5)}, minutes=30 * i - 1440) for i in range(50)]
    short = long[-4:]
    for obs, status in ((long, "available"), (short, "abstained")):
        points = list(build_series(obs, cfg).by_code["hr"].points)
        forecasts = forecast_metric("hr", "beats/min", points, T0 + timedelta(minutes=40), PersistenceForecaster())
        snap = build_snapshot(TwinInputs(episode=EPISODE, protocol=KNOWN, forecasts=forecasts), NOW)
        assert [f.status for f in snap.forecasts] == [status] * 3
        assert [f.horizon_hours for f in snap.forecasts] == [6, 12, 24]
        assert any("never replace a safety decision" in x for x in snap.limitations)
        payload = snap.event_payload()["forecasts"][0]
        assert set(payload) == {"forecast_id", "target_code", "unit", "issued_at", "horizon_hours",
                                "status", "point", "interval", "method_version", "evidence_ids",
                                "limitations"}
