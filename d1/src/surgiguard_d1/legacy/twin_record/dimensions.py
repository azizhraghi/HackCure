"""Build each Twin dimension from its own source. Dimensions never mix."""

from collections import Counter
from datetime import datetime
from typing import get_args

import numpy as np

from ...physiology.models import Evidence, Quality
from ..trajectory_model.dossier import flatten
from ..trajectory_model.model import ExpectedTrajectory
from .models import (
    AnalysisInput,
    Dimension,
    DimensionName,
    MedicationReport,
    MetricSummary,
    PatientContext,
    ProtocolView,
    SymptomReport,
    TwinInputs,
)
from .timeline import POD_CONVENTION, calendar_days_between, milestone_timing

ANALYSIS_DIMENSIONS = {
    "physiology": "physiological_trends",
    "neurological_motor": "motor_performance",
    "wound": "wound_visual_changes",
    "rehabilitation": "functional_recovery",
}

_NO_DATA = Quality(status="unknown", reasons=["no_input"], usable_for=[])


def build_dimensions(inputs: TwinInputs, as_of: datetime) -> tuple[list[Dimension], list[Evidence]]:
    refs = inputs.protocol.dimension_references if inputs.protocol else {}
    evidence: dict[str, Evidence] = {}
    dims: list[Dimension] = []

    def add(dim: Dimension, ev: list[Evidence]) -> None:
        dims.append(dim.model_copy(update={"reference_id": refs.get(dim.name)}))
        evidence.update((e.evidence_id, e) for e in ev)

    latest = _latest_by_type(inputs.analyses)
    for analysis_type, name in ANALYSIS_DIMENSIONS.items():
        dim, ev = _from_analysis(name, latest.get(analysis_type))
        if name == "physiological_trends" and inputs.protocol:
            extra, extra_ev = _approved_references(inputs.protocol)
            dim = dim.model_copy(update={
                "metric_summaries": dim.metric_summaries + extra,
                "evidence_ids": dim.evidence_ids + [e.evidence_id for e in extra_ev],
            })
            ev = ev + extra_ev
        if name == "physiological_trends" and inputs.expected:
            dim = _against_expected(dim, inputs.expected, inputs.episode.surgery_at)
        add(dim, ev)
    add(*_symptoms(_dedupe(inputs.symptom_reports)))
    add(*_medication(_dedupe(inputs.medication_reports)))
    add(*_timeline(inputs, as_of))

    order = get_args(DimensionName)
    dims.sort(key=lambda d: order.index(d.name))
    return dims, list(evidence.values())


def _latest_by_type(analyses: list[AnalysisInput]) -> dict[str, AnalysisInput]:
    out: dict[str, AnalysisInput] = {}
    for a in sorted(analyses, key=lambda a: (a.created_at, a.analysis_id)):
        out[a.analysis_type] = a
    return out


def _dedupe(reports):
    """One entry per report_id; a re-sent or edited report replaces the earlier one."""
    latest = {}
    for r in sorted(reports, key=lambda r: (r.received_at, r.event_id)):
        latest[r.report_id] = r
    return sorted(latest.values(), key=lambda r: (r.occurred_at, r.report_id))


def _empty(name: str, missing: str) -> tuple[Dimension, list[Evidence]]:
    return (
        Dimension(
            name=name, status="no_data", metric_summaries=[], latest_observed_at=None,
            reference_id=None, quality=_NO_DATA, evidence_ids=[], missing=[missing],
            limitations=["No information available; this is not a normal result."],
        ),
        [],
    )


# ------------------------------------------------------------ analyses


def _from_analysis(name: str, a: AnalysisInput | None) -> tuple[Dimension, list[Evidence]]:
    if a is None:
        return _empty(name, "no analysis received")

    summaries: list[MetricSummary] = []
    missing: list[str] = []
    if a.analysis_type == "physiology":
        for f in a.observations:
            summaries.extend(_physiology_summaries(f))
            if f["state"] != "summarized":
                missing.append(f"{f['code']}: {f['state']}")
    else:
        # Motor, wound and rehabilitation outputs come from pose/image models.
        for o in a.observations:
            value = o.get("value")
            summaries.append(
                MetricSummary(
                    code=str(o.get("code", "finding")),
                    basis="model_estimate",
                    value=value if isinstance(value, (int, float, str)) else None,
                    unit=o.get("unit"),
                    observed_at=o.get("observed_at"),
                    detail={k: v for k, v in o.items() if k not in {"code", "value", "unit", "observed_at"}},
                )
            )

    observed = [s.observed_at for s in summaries if s.observed_at] + [
        e.observed_at for e in a.evidence if e.observed_at
    ]
    ev = Evidence(
        evidence_id=f"evref_{a.analysis_id}", kind="analysis", resource_id=a.analysis_id,
        resource_version="1", observed_at=a.created_at, locator=None,
    )
    if a.status == "complete":
        status = "observed"
    else:
        status = "limited" if summaries else "no_data"
    dim = Dimension(
        name=name, status=status, metric_summaries=summaries,
        latest_observed_at=max(observed, default=None), reference_id=None,
        quality=a.quality, evidence_ids=[ev.evidence_id], missing=missing,
        limitations=list(a.limitations),
    )
    return dim, [ev]


def _physiology_summaries(f: dict) -> list[MetricSummary]:
    code, unit = f["code"], f["unit"]
    out: list[MetricSummary] = []
    if f["latest"]:
        out.append(MetricSummary(
            code=code, basis="observation", value=f["latest"]["value"], unit=unit,
            observed_at=f["latest"]["observed_at"],
            detail={"observation_id": f["latest"]["observation_id"]},
        ))
    if f["median"] is not None:
        out.append(MetricSummary(
            code=f"{code}.window_median", basis="derived_summary", value=f["median"], unit=unit,
            detail={k: f[k] for k in ("mad", "usable_count", "window_start", "window_end", "coverage")},
        ))
    if f["slope"]:
        out.append(MetricSummary(
            code=f"{code}.slope", basis="derived_summary",
            value=f["slope"]["value"], unit=f["slope"]["unit"],
        ))
    r = f["reference"]
    if r and any(r[k] is not None for k in ("latest", "window_median", "change_from_baseline")):
        out.append(MetricSummary(
            code=f"{code}.vs_reference", basis="derived_summary", value=r["latest"],
            reference_id=r["reference_id"],
            detail={k: r[k] for k in ("reference_version", "window_median", "change_from_baseline")},
        ))
    return out


# ------------------------------------------- approved protocol from D2


def _approved_references(protocol: ProtocolView) -> tuple[list[MetricSummary], list[Evidence]]:
    """The approved range and the patient's baseline, shown beside the readings."""
    summaries, evidence = [], []
    for code, r in sorted(protocol.metric_references.items()):
        summaries.append(MetricSummary(
            code=f"{code}.approved_reference", basis="approved_expectation", value=None,
            reference_id=r.reference_id,
            detail={"version": r.version, "lower": r.lower, "upper": r.upper,
                    "baseline": r.baseline,
                    "expected_interval_minutes": r.expected_interval_minutes},
        ))
        evidence.append(Evidence(
            evidence_id=f"evref_{r.reference_id}", kind="protocol",
            resource_id=protocol.protocol_id, resource_version=protocol.version,
            observed_at=None, locator=f"metric_references[{code}]",
        ))
    return summaries, evidence


def _against_expected(
    dim: Dimension, expected: list[ExpectedTrajectory], surgery_at: datetime
) -> Dimension:
    """Place each latest reading on the predicted normal curve for this patient."""
    latest = {s.code: s for s in dim.metric_summaries if s.basis == "observation"}
    extra: list[MetricSummary] = []
    missing = list(dim.missing)
    for t in sorted(expected, key=lambda t: t.metric):
        if t.status != "available":
            missing.append(f"{t.metric}: no expected trajectory ({'; '.join(t.reasons)})")
            continue
        obs = latest.get(t.metric)
        if obs is None or obs.observed_at is None:
            continue
        day = (obs.observed_at - surgery_at).total_seconds() / 86400
        days = [p.day for p in t.points]
        if not days[0] <= day <= days[-1]:
            missing.append(f"{t.metric}: no expected value for day {day:.1f}")
            continue
        lower, median, upper = (
            float(np.interp(day, days, [getattr(p, k) for p in t.points]))
            for k in ("lower", "median", "upper")
        )
        extra.append(MetricSummary(
            code=f"{t.metric}.expected", basis="model_estimate", value=round(median, 2), unit=t.unit,
            detail={"lower": round(lower, 2), "upper": round(upper, 2), "day": round(day, 2),
                    "band_coverage": t.band_coverage, "model_version": t.model_version,
                    "data_origin": t.data_origin, "training_patients": t.training_patients},
        ))
        side = "below" if obs.value < lower else "above" if obs.value > upper else "within"
        extra.append(MetricSummary(
            code=f"{t.metric}.vs_expected", basis="derived_summary", value=side,
            detail={"difference_from_expected": round(obs.value - median, 2), "day": round(day, 2)},
        ))
    return dim.model_copy(update={"metric_summaries": dim.metric_summaries + extra, "missing": missing})


def build_context(
    protocol: ProtocolView | None, dossier: dict | None = None, episode_id: str = ""
) -> tuple[PatientContext, list[Evidence]]:
    if dossier is not None:
        return _context_from_dossier(dossier, episode_id)
    if protocol is None:
        return PatientContext(procedure=None, items=[], evidence_ids=[],
                              missing=["no active approved protocol"]), []
    ev = Evidence(
        evidence_id=f"evref_{protocol.protocol_id}_context", kind="protocol",
        resource_id=protocol.protocol_id, resource_version=protocol.version,
        observed_at=None, locator="patient_context",
    )
    missing = []
    if protocol.procedure is None:
        missing.append("procedure not stated")
    if not protocol.patient_context:
        missing.append("no patient background supplied")
    return PatientContext(
        procedure=protocol.procedure,
        items=[
            MetricSummary(code=c.code, basis="clinical_record", value=c.value, unit=c.unit,
                          detail={"label": c.label})
            for c in protocol.patient_context
        ],
        evidence_ids=[ev.evidence_id],
        missing=missing,
    ), [ev]


def _context_from_dossier(dossier: dict, episode_id: str) -> tuple[PatientContext, list[Evidence]]:
    """Every dossier field the model can read, shown as clinical record."""
    p = flatten(dossier)
    ev = Evidence(
        evidence_id=f"evref_dossier_{episode_id}", kind="reference", resource_id=f"dossier_{episode_id}",
        resource_version="1", observed_at=None, locator="dossier",
    )
    items = (
        [MetricSummary(code=k, basis="clinical_record", value=v) for k, v in sorted(p.numeric.items())]
        + [MetricSummary(code=k, basis="clinical_record", value=v) for k, v in sorted(p.categorical.items())]
        + [MetricSummary(code=k, basis="clinical_record", value="yes") for k in sorted(p.flags)]
    )
    procedure = next((v for k, v in p.categorical.items() if k.split(".")[-1] == "procedure"), None)
    return PatientContext(
        procedure=procedure, items=items, evidence_ids=[ev.evidence_id],
        missing=[] if items else ["dossier is empty"],
    ), [ev]


# ---------------------------------------------------- reports from D2


def _symptoms(reports: list[SymptomReport]) -> tuple[Dimension, list[Evidence]]:
    if not reports:
        return _empty("pain_symptoms", "no symptom report received")
    last = reports[-1]
    at = last.occurred_at
    s: list[MetricSummary] = []
    used = [last]
    if last.mood_label is not None:
        s.append(MetricSummary(code="mood", basis="reported", value=last.mood_label, observed_at=at))
    if last.pain_score is not None:
        s.append(MetricSummary(code="pain_score", basis="reported", value=last.pain_score, unit="0-10", observed_at=at))
        earlier = [r for r in reports[:-1] if r.pain_score is not None]
        if earlier:
            used.insert(0, earlier[-1])
            s.append(MetricSummary(
                code="pain_score.change_from_previous", basis="derived_summary",
                value=last.pain_score - earlier[-1].pain_score, unit="0-10",
                detail={"previous_report_id": earlier[-1].report_id,
                        "previous_at": earlier[-1].occurred_at.isoformat()},
            ))
    for item in last.items:
        s.append(MetricSummary(
            code=f"symptom.{item.code}", basis="reported", value=item.assertion, observed_at=at,
            detail={"severity": item.severity,
                    "onset_at": item.onset_at.isoformat() if item.onset_at else None},
        ))
    answers = Counter(a.answer for a in last.warning_answers)
    s.append(MetricSummary(
        code="warning_answers", basis="reported", value=None, observed_at=at,
        detail={"yes": answers["yes"], "no": answers["no"], "unknown": answers["unknown"],
                "answered": len(last.warning_answers)},
    ))

    missing, limitations = [], []
    if last.pain_score is None:
        missing.append("pain score not given")
    if not last.warning_answers:
        missing.append("warning questions not answered")
        limitations.append("No warning answers were supplied; this does not mean no warning signs.")
    if last.extraction_status != "structured":
        limitations.append(f"Free-text extraction status: {last.extraction_status}.")
    if not last.confirmed_by_patient:
        limitations.append("Structured symptoms not yet confirmed by the patient.")

    clean = last.extraction_status == "structured" and last.confirmed_by_patient
    ev = [_report_evidence(r.report_id, "symptom", r.occurred_at) for r in used]
    return (
        Dimension(
            name="pain_symptoms", status="observed" if clean else "limited",
            metric_summaries=s, latest_observed_at=at, reference_id=None,
            quality=Quality(status="usable" if clean else "limited",
                            reasons=["patient_reported"], usable_for=["clinician_review"]),
            evidence_ids=[e.evidence_id for e in ev], missing=missing, limitations=limitations,
        ),
        ev,
    )


def _medication(reports: list[MedicationReport]) -> tuple[Dimension, list[Evidence]]:
    if not reports:
        return _empty("medication", "no medication report received")
    last = reports[-1]
    counts = Counter(r.reported_status for r in reports)
    linked = sorted({sid for r in reports for sid in r.symptom_report_ids})
    s = [
        MetricSummary(
            code="latest_report", basis="reported", value=last.reported_status,
            observed_at=last.occurred_at,
            detail={"prescription_id": last.prescription_id,
                    "scheduled_dose_id": last.scheduled_dose_id,
                    "reporter_id": last.reporter_id},
        ),
        *(
            MetricSummary(code=f"reports.{k}", basis="reported", value=counts[k], unit="reports")
            for k in ("taken", "missed", "unsure")
        ),
    ]
    if linked:
        s.append(MetricSummary(
            code="linked_symptom_reports", basis="reported", value=len(linked), unit="reports",
            detail={"symptom_report_ids": linked},
        ))
    ev = [_report_evidence(r.report_id, "medication", r.occurred_at) for r in reports]
    return (
        Dimension(
            name="medication", status="observed", metric_summaries=s,
            latest_observed_at=last.occurred_at, reference_id=None,
            quality=Quality(status="limited", reasons=["reported_not_verified"],
                            usable_for=["clinician_review"]),
            evidence_ids=[e.evidence_id for e in ev], missing=[],
            limitations=[
                "Reported by the patient or caregiver; not proof a dose was taken.",
                "Doses with no report are unknown, not missed.",
            ],
        ),
        ev,
    )


def _report_evidence(report_id: str, kind: str, at: datetime) -> Evidence:
    return Evidence(
        evidence_id=f"evref_{report_id}", kind=kind, resource_id=report_id,
        resource_version="1", observed_at=at, locator=None,
    )


# ------------------------------------------------------------ timeline


def _timeline(inputs: TwinInputs, as_of: datetime) -> tuple[Dimension, list[Evidence]]:
    ep, protocol = inputs.episode, inputs.protocol
    pod = calendar_days_between(ep.surgery_at, as_of, ep.timezone)
    s = [MetricSummary(
        code="postoperative_day", basis="derived_summary", value=pod, unit="d",
        detail={"surgery_at": ep.surgery_at.isoformat(), "timezone": ep.timezone,
                "convention": POD_CONVENTION},
    )]
    missing: list[str] = []
    if ep.discharge_at is not None:
        s.append(MetricSummary(
            code="days_since_discharge", basis="derived_summary", unit="d",
            value=calendar_days_between(ep.discharge_at, as_of, ep.timezone),
            detail={"discharge_at": ep.discharge_at.isoformat()},
        ))
    else:
        missing.append("discharge time not recorded")

    ev: list[Evidence] = []
    if protocol is None:
        missing.append("no active approved protocol")
    elif not protocol.milestones:
        missing.append("no approved milestones")
    else:
        for m in protocol.milestones:
            s.append(MetricSummary(
                code=f"milestone.{m.milestone_id}", basis="approved_expectation",
                value=m.label, reference_id=m.milestone_id,
                detail={"version": m.version, "expected_from_day": m.expected_from_day,
                        "expected_to_day": m.expected_to_day, "timing": milestone_timing(m, pod)},
            ))
            ev.append(Evidence(
                evidence_id=f"evref_{m.milestone_id}", kind="protocol",
                resource_id=protocol.protocol_id, resource_version=protocol.version,
                observed_at=None, locator=f"milestones[{m.milestone_id}]",
            ))
    return (
        Dimension(
            name="recovery_timeline", status="limited" if missing else "observed",
            metric_summaries=s, latest_observed_at=None, reference_id=None,
            quality=Quality(status="usable", reasons=[], usable_for=["display"]),
            evidence_ids=[e.evidence_id for e in ev], missing=missing,
            limitations=["Milestone timing is a calendar position; it does not show "
                         "whether a milestone was reached."],
        ),
        ev,
    )
