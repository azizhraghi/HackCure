# SurgiGuard AI — Developer 1
## ML, Patient Recovery Twin and Computer Vision

**Mission:** transform attributable postoperative measurements and patient-initiated assessments into interpretable recovery observations, longitudinal comparisons and cautiously qualified forecasts. Deliver evidence to the clinician and investigation service without asserting a diagnosis.

## 1. Scope, deliverables and non-goals

You own six modules: physiological analysis; the Patient Recovery Twin; selected near-term trajectory prediction; guided neurological motor assessment; rehabilitation pose estimation; and longitudinal wound-photo analysis. All are required workstreams. Advanced models may remain gated while deterministic baselines and honest abstention are delivered.

Deliver versioned services, generated API types, reproducible feature pipelines, model/configuration manifests, annotation guidance, evaluation reports, synthetic fixtures and dashboard-ready data. Supporting data preparation can be shared with the other developers, but this developer remains accountable for measurement validity and model limitations.

Do not build continuous home-camera monitoring, background camera capture, camera-derived BP, emotion recognition, neurological diagnosis, automated rehabilitation prescription, autonomous wound diagnosis, automatic dressing removal instructions or a universal recovery score. Respiratory-rate analysis is conditional on a reliable approved input method; do not infer it from the phone camera by default. Do not add sensors merely because a model could use them.

The clinical context matters: normal postoperative expectations depend on the procedure, recovery phase, baseline and restrictions. A missing measurement is not improvement. Poor-quality imagery is not evidence of healthy recovery. Patient symptoms can require escalation even when the most recent measured values appear reassuring.

## 2. Modules and implementation tasks

### D1-A — Physiological time-series pipeline

1. Implement canonical code/unit validation for SpO2, HR, paired manual BP and temperature. Preserve raw records, measurement method, source device and reporter. Separate measurement time, receipt time and corrected records.
2. Preserve irregular sampling. Generate display series at native timestamps and analysis windows with explicit sample count, observed coverage, elapsed time and missingness. Do not interpolate across long gaps or display an interpolation as an observed measurement.
3. Add device-supplied quality indicators where available, out-of-order handling, duplicate detection, clock-skew flags, detached-device indications and manual-entry plausibility prompts. A doubtful extreme value remains available to the safety lane; filtering cannot silently suppress it.
4. Start with transparent rolling medians, robust dispersion, time-aware slope and change-from-patient-baseline summaries. Choose window lengths from expected sampling and approved clinical use. Report slope units, minimum sample count and actual window coverage. Compare HR values under comparable activity conditions where those observations are available; do not invent activity labels.
5. Provide separate systolic and diastolic BP curves, not a merged BP score. Temperature method/device and source changes must be visible when available. Expose gaps and correction history to the dashboard.
6. Publish `analysis.completed` with quality and evidence references. D3 owns alert category and policy execution. D1 may report a deviation from an approved reference but cannot choose a new clinical threshold.

**Failure behavior:** insufficient samples produces `limited` or `abstained`, a reason and the usable raw data. Distinguish “no recent measurement,” “analysis failed” and “no detected deviation.”

### D1-B — Patient Recovery Twin

The Twin is a versioned patient-state representation, not a simulated person or diagnostic oracle. Its dimensions are physiological trends, observable motor performance, wound visual changes, pain/symptoms, medication adherence and relevant reported side effects, functional recovery, time since surgery and approved milestones.

- Build an episode timeline keyed to surgery and discharge timestamps. Use actual elapsed duration; display postoperative day using an agreed timezone convention.
- Materialize immutable snapshots from observations, D2 symptom/medication events, D1 analyses and the effective approved protocol. Every dimension retains latest observed time, quality, evidence, missingness and the version of the expected reference.
- Separate observations, model estimates and clinician-approved expectations in storage and UI payloads. An expectation can be a milestone, interval or qualitative restriction; do not invent a reference curve when none is approved.
- Show direct measurements and dimension-specific change. “Medication taken” remains patient-reported. “Wound appearance changed” remains an image observation. No unsupported normalized whole-patient recovery number.
- Recompute affected snapshots after late or corrected events. Store `snapshot_version`, `input_watermark`, pipeline/model versions and reason for recomputation. Keep the snapshot referenced by an existing investigation reproducible.
- Serve patient-friendly and clinician-detail views through authorization-aware projections. Caregiver data exposure is controlled upstream and repeated at retrieval; the Twin itself does not grant access.

### D1-C — Cautious trajectory prediction

Start disabled for clinical use. Select a forecast target only after documenting a clinically meaningful use, sufficient longitudinal data and a measurable horizon. Examples of technical candidates are a measured HR trend or a defined mobility metric; inclusion here is not approval for clinical deployment.

Baseline sequence: last-value/persistence forecast, simple time-aware statistical baseline, then a learned model only if justified by held-out evaluation. Candidate methods include robust regression or a state-space model; more complex sequence models require enough representative data and a demonstrated advantage over the baseline.

Each output specifies target, unit, issue time, horizon, method, training/evaluation population, point estimate and calibrated interval when available. Disable prediction under unsupported procedure, excessive missingness, distribution shift, incompatible acquisition method, stale protocol or inadequate individual history. Do not emit a numerical confidence merely because an LLM or neural model can generate one.

Forecasts are supplementary evidence. They never delay emergency handling, provide a “safe until” time, promise recovery, diagnose a complication or directly change a surveillance schedule. A proposed cadence change goes through D2 and clinician approval.

### D1-D — Opt-in neurological guided motor assessment

1. Fetch the active protocol's authorized assessment definition: movement instructions, eligibility, recovery phase, restrictions, maximum duration, stopping criteria and approved symptom questions. Clinical owners select actual tests; engineering does not prescribe a new test.
2. Before capture, check episode authorization, current restrictions and whether the patient is already reporting a warning sign. A detected warning routes to D3 immediately, without requiring movement completion.
3. Request session consent and foreground camera access. Present positioning and framing guidance plus the approved demonstration. The patient can decline or stop; record “not completed,” never “failed neurological test.”
4. Estimate landmarks using a pinned pose model such as MediaPipe Pose Landmarker. Convert visible landmarks to features: task-specific projected joint angles, range, bilateral difference, movement timing and completion. Save camera orientation, visible joints and relevant acquisition settings.
5. Filter low-visibility frames and quantify usable frame coverage. Explicitly handle occlusion, multiple people, mirrored front cameras, left/right ambiguity, frame drops, rotation and incomplete movement. Do not treat estimated 3D landmarks as clinically calibrated anatomical measurements.
6. Ask the approved post-assessment questions for pain, weakness, dizziness and difficulty. Stop advice follows approved wording. Symptoms route to D2/D3 even if CV fails.
7. Compare only compatible sessions with the same assessment/version and sufficiently comparable view. Explain when a change could be caused by camera placement or task execution. Provide features and uncertainty, not a diagnosis.
8. Close camera resources on completion, decline, cancellation and app backgrounding. Prefer on-device processing and derived features; retain video only for a defined approved purpose with explicit retention policy.

### D1-E — Rehabilitation pose estimation

Reuse the capture and landmark infrastructure but maintain a separate `assessment_type=rehabilitation` and exercise-specific configuration. Use only clinician-approved exercises within postoperative restrictions. Count repetitions or summarize range/timing only when the approved exercise and acquisition view make the metric meaningful. Expose incomplete repetitions and uncertain counts instead of forcing completion.

Do not reward movement beyond a prescribed range, increase workload automatically, infer pain from appearance, or turn a poor camera view into “incorrect rehabilitation.” The patient's reported pain/difficulty is separate evidence. Unsafe symptoms stop the task using approved instructions and enter the safety lane. Provide clinician review of progress, not an autonomous exercise progression system.

### D1-F — Wound-photo analysis

- Trigger capture prompts only at medically authorized dressing changes and only when the care plan permits a photograph. Do not prompt dressing removal for an image; declining or missing a photo must not generate instructions to uncover the wound.
- Patient initiates capture; guide lighting, focus, framing and comparable distance without delaying urgent assessment. Link photo to wound/site ID, episode, capture time and dressing-change task.
- Check blur, exposure, framing, occlusion, visibility and comparability. Store raw photo privately and publish `artifact_id`, not public URLs. Record whether color and scale comparisons are defensible.
- Start with a clinician-viewable longitudinal sequence and quality assessment. Add region localization/segmentation only with appropriate annotated data; any automated visible-change output must remain reviewable.
- Assess visible redness, apparent swelling, wound-edge appearance and possible visible discharge, qualifying limitations. A photo cannot measure all swelling or confirm discharge composition. Avoid precise wound-size measurements without valid calibration, and avoid color-change claims under incompatible lighting.
- Compare the same wound across compatible photos; do not compare different sites or allow misidentification to look like deterioration. Link visible changes to contemporaneous pain, temperature and reported symptoms through the Twin/D3.
- Return review-worthy visual observations or abstention. Never label the wound “infected,” “healed” or clinically safe from a photo alone. Photo collection and analysis never replace urgent medical assessment.

## 3. Service design, storage and algorithms

Proposed deployment: a Python API with typed validation, separate CPU/GPU analysis workers where needed, a relational/time-indexed observation store, private media storage, and immutable model manifests. These are replaceable implementation choices; no specific vendor is required. Keep urgent D3 processing in a separate queue/runtime so image work cannot starve it.

Suggested internal packages: `physiology`, `twin`, `forecast`, `capture_contracts`, `motor_features`, `rehab_features`, `wound_quality`, `wound_compare`. Keep feature extraction deterministic where possible, save model weights/checksums and dependency versions, and track exactly which features were computed by which release. Use vectorized numerical operations for time-series analysis and a standard image-processing library for quality checks; do not train a complex model merely to replace a transparent calculation.

Resource tables: observations, correction links, analysis jobs, analysis results, assessment sessions, private artifacts, Twin snapshots, approved reference bindings and model runs. Store consent and protocol references, not disconnected copies that become stale. Use signed artifact access only after checking user rights. Concurrency control prevents an older job overwriting a newer snapshot.

## 4. Developer-specific API and payload examples

All examples use synthetic IDs. The shared section defines envelope, quality, evidence and error handling.

| Endpoint | Input | Output / behavior |
|---|---|---|
| `POST /v1/episodes/{episode_id}/assessment-sessions` | Approved `assessment_id`, `protocol_version`, `consent_record_id` | `201`: session ID, expiry, permitted capture mode, approved instruction reference; deny stale/ineligible tests |
| `POST /v1/episodes/{episode_id}/assessment-sessions/{id}/complete` | Derived metrics or authorized artifact ID; capture metadata; symptom report ID | `202`: analysis job ID; never a diagnosis |
| `POST /v1/episodes/{episode_id}/analyses` | `analysis_type`, `observation_ids[]`, exact protocol version | Internal service only; `202` job ID; later `analysis.completed` |
| `GET /v1/episodes/{episode_id}/analyses/{id}` | Authorized resource ID | State and reproducible result; reason if limited/abstained |
| `GET /v1/episodes/{episode_id}/trends?code=spo2` | Approved window and metric code | Actual timestamp/value/unit points, gaps, quality and separately labeled references |

A complete manual BP event:

```json
{
  "schema_version": "1.0",
  "event_id": "ev_bp_001",
  "event_type": "observation.recorded",
  "patient_id": "pt_demo_001",
  "episode_id": "ep_demo_001",
  "occurred_at": "2026-10-10T08:00:00Z",
  "received_at": "2026-10-10T08:01:00Z",
  "producer": "ingestion",
  "trace_id": "trace_demo_001",
  "protocol_version": "protocol_demo_v1",
  "payload": {
    "observation_id": "obs_bp_001",
    "kind": "physiology",
    "source": {"method": "manual", "device_id": "cuff_demo_001", "reporter_id": "pt_demo_001"},
    "quality": {"status": "unknown", "reasons": ["patient_entered"], "usable_for": ["clinician_review"]},
    "metrics": [{"code": "sbp", "value": 120, "unit": "mmHg"}, {"code": "dbp", "value": 80, "unit": "mmHg"}],
    "artifact_id": null,
    "assessment_id": null,
    "supersedes_id": null
  }
}
```

Numbers demonstrate formatting only, not thresholds or an assessment of the patient.

### Forecast item JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RecoveryForecastV1",
  "type": "object",
  "additionalProperties": false,
  "required": ["forecast_id", "target_code", "unit", "issued_at", "horizon_hours", "status", "point", "interval", "method_version", "evidence_ids", "limitations"],
  "properties": {
    "forecast_id": {"type": "string"},
    "target_code": {"type": "string"},
    "unit": {"type": "string"},
    "issued_at": {"type": "string", "format": "date-time"},
    "horizon_hours": {"type": "number", "exclusiveMinimum": 0},
    "status": {"enum": ["available", "abstained"]},
    "point": {"type": ["number", "null"]},
    "interval": {
      "oneOf": [
        {"type": "null"},
        {"type": "object", "additionalProperties": false, "required": ["lower", "upper", "coverage"], "properties": {
          "lower": {"type": "number"}, "upper": {"type": "number"}, "coverage": {"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 1}
        }}
      ]
    },
    "method_version": {"type": ["string", "null"]},
    "evidence_ids": {"type": "array", "items": {"type": "string"}},
    "limitations": {"type": "array", "items": {"type": "string"}}
  },
  "allOf": [{"if": {"properties": {"status": {"const": "abstained"}}}, "then": {"properties": {"point": {"type": "null"}, "interval": {"type": "null"}}}, "else": {"properties": {"point": {"type": "number"}, "method_version": {"type": "string"}}}}]
}
```

Application validation additionally enforces ordered interval bounds, a nonempty reason for abstention, a supported target/unit pair and provenance for the reported interval coverage. Interval omission on an available forecast must be explicitly explained; UI must not imply certainty.

```json
{
  "forecast_id": "fc_demo_001",
  "target_code": "hr",
  "unit": "beats/min",
  "issued_at": "2026-10-10T08:02:00Z",
  "horizon_hours": 6,
  "status": "abstained",
  "point": null,
  "interval": null,
  "method_version": null,
  "evidence_ids": ["evref_hr_001"],
  "limitations": ["Insufficient comparable longitudinal observations for this target and horizon."]
}
```

## 5. Data acquisition and evaluation plan

Create a dataset inventory before model selection: source, license, consent, procedure mix, device/camera, sampling pattern, label definition, target population and missingness. Public datasets may support pretraining or engineering experiments but cannot establish postoperative home-use performance. Do not invent dataset size or promise an accuracy level.

| Workstream | Ground truth and split | Evaluation and limitations |
|---|---|---|
| Physiology | Recorded device exports, verified manual-entry fixtures and clinician-reviewed events; split by patient/episode and time | Unit correctness, gap handling, slope/window calculations, agreement with reference implementation, quality detection and artifact failure cases |
| Twin | Curated multi-event timelines with expected snapshots | Provenance completeness, temporal ordering, correction consistency, no future-data leakage, accurate unknown states |
| Forecast | Outcome measurements strictly after issue time; patient-level and temporal holdouts | MAE/RMSE by target and horizon, interval coverage/width, baseline comparison, abstention coverage, subgroup sample counts and confidence intervals |
| Neurological motor / rehabilitation | Authorized volunteer/clinical recordings with trained assessor annotations; independent patient/session splits | Landmark visibility, per-feature agreement, joint-angle errors where reference measurement is valid, repeatability, repetition error, completion and abstention rates |
| Wound | Consented same-wound sequences, quality labels and clinician-adjudicated visible findings | Quality rejection, region agreement if segmentation used, change-review agreement, sensitivity/specificity only for precisely labeled review tasks, false-review burden and missed-change cases |

Define annotation manuals, double-label a subset, quantify inter-rater agreement and adjudicate disagreements. Wound labels must not use photograph-only “infection” as diagnostic ground truth. If clinical outcomes are studied later, obtain proper clinical adjudication and separate that study from visual-feature evaluation.

Stratify evaluation by procedure, postoperative phase, acquisition device, lighting, skin appearance where ethically collected, mobility limitations and relevant missingness. Report subgroup counts and uncertainty; small samples do not justify generalization. Prevent adjacent frames, same patient and same wound sequences leaking across splits. Freeze test sets and model/configuration hashes before evaluation. No forecast or CV metric is a claim of clinical efficacy.

## 6. Safety, privacy and dependency handoffs

D2 must deliver approved restrictions, assessment definitions, wound-photo permissions, milestone references and versioned symptom/medication data. D3 must deliver reliable safety ingress, event acknowledgements, investigation evidence requirements and cancellation signals when an urgent warning makes further assessment inappropriate. App engineers must deliver camera lifecycle handling, consent UX and capture timestamps. Clinicians must approve each movement and wound workflow before patient use.

Maintain raw-data provenance and minimize media retention. Do not derive identity or unrelated characteristics from wound or movement images. A revoked optional camera consent blocks new capture; the feature remains usable through missing-data status and existing permitted observations. Model failures do not block manual measurements or symptom submission.

## 7. Acceptance criteria and test matrix

| ID | Pass condition | Test |
|---|---|---|
| D1-01 | Accepted physiological events conform to units, time and attribution contracts | Valid/invalid SpO2, HR, paired BP, temperature and duplicate fixtures |
| D1-02 | Gaps and stale data remain visible; no interpolation is presented as measurement | Irregular sampling, clock skew, missing-day and correction replay |
| D1-03 | Twin is reproducible for a recorded input watermark and protocol | Rebuild snapshot and compare dimension/evidence outputs |
| D1-04 | No camera starts without active eligibility and consent; all exits stop capture | Denial, cancellation, backgrounding, expiry and sudden-warning scenarios |
| D1-05 | Invalid framing and mirrored/occluded sessions do not create confident motor findings | Device/view matrix with adjudicated quality failures |
| D1-06 | Wound capture never requests unauthorized dressing removal | No dressing permission, missed task, declined photo and urgent symptom cases |
| D1-07 | Wound outputs describe visible changes/limitations without diagnosis | Clinical terminology review and adversarial output checks |
| D1-08 | Forecast abstains under every declared unsupported condition | Missingness, unfamiliar procedure, changed device and insufficient-history fixtures |
| D1-09 | D3 receives symptoms immediately despite stalled CV | Fault injection with analysis worker unavailable |
| D1-10 | Unauthorized artifacts and caregiver views are denied | Cross-episode access, expired URL and revoked grant tests |

Passing these is an engineering release gate. Clinical deployment also requires signed clinical validation criteria and an evaluation report; no unexplained numerical performance target can substitute for clinical review.

## 8. Phased work plan and integration evidence

1. **Contract and clinical-definition gate:** agree metric vocabulary, event schemas, device inputs, approved assessments, media policy and D2/D3 interfaces. Deliver schemas, fixtures and unresolved-decision register.
2. **Transparent baseline:** implement ingestion analysis, raw trend views and the versioned Twin, including unknown states. Demonstrate manual BP and out-of-order updates end to end.
3. **Camera workstreams:** implement common session gating, motor/rehabilitation features and wound capture/quality/longitudinal display. Deliver independent quality tests for each; do not hide wound work behind the motor demonstration.
4. **Model evaluation:** benchmark forecast and any learned wound/motor components. Deliver model cards, dataset documentation, baseline comparisons and explicit enable/disable decisions.
5. **Three-role integration:** run the shared demonstration with D2/D3, export event traces and show actual curves, approved references, visual evidence and abstention. Include emergency interruption of a camera session.
6. **Release gate:** close safety defects, document rollback/model disabling, obtain clinical acceptance for enabled assessments and metrics, and retain unvalidated capabilities in demonstration-only mode.

**Done means:** all six modules have working interfaces, tests and documented limitations; every learned capability has an evidence-based release decision; and D3 can investigate D1 outputs without reconstructing lost provenance.

## 9. Supporting primary references

These references inform implementation only; they do not expand the finalized project scope or supply a patient-specific protocol. Verified 10 October 2026.

- [FDA: Pulse Oximeters](https://www.fda.gov/medical-devices/products-and-medical-procedures/pulse-oximeters): pulse oximetry has limitations and possible inaccuracy, including concerns about skin pigmentation. Treat the device output as evidence with limitations, not absolute truth.
- [Google: Pose landmark detection guide](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker): pose landmarks are a technical building block. This documentation is not validation of neurological or rehabilitation clinical use.

---

# Shared platform and integration appendix

## Project authority and clinical context

**SurgiGuard AI — Updated Project Version · HackCure 2026**  
Specification version: 1.0 · Prepared: 10 October 2026 · Status: implementation specification; clinical configuration pending approval.

The authority is the user's most recent full pasted “SurgiGuard AI — Updated Project Version,” message `8b454a2d-bcf1-4771-ab58-0dbe2b12ecf4` in the referenced conversation, together with the user's current explicit responsibilities and exclusions. Earlier drafts and assistant responses do not define scope. This document translates that scope into engineering decisions; proposed internal APIs, storage choices, and algorithms are implementation recommendations, not additional product capabilities.

The platform supports recovery at home after hospital discharge: observe postoperative changes, compare recovery against clinician-approved expectations, investigate evidence, and coordinate appropriate follow-up. Respiratory, hemodynamic, and neurological surveillance are priorities, not an exhaustive taxonomy of complications. Wound, medication, pain, and functional recovery evidence remain part of the same platform.

There are **exactly three product roles**:

| Role and interface | Authorized experience | Authority boundary |
|---|---|---|
| Patient mobile space | Own recovery dashboard, readings, symptom check-ins, prescription reminders, authorized camera sessions and exercises, wound photos, appointments, assistance | Can report and acknowledge; cannot approve clinical protocols |
| Caregiver mobile space | Permission-scoped updates, assistance requests, reminders, practical tasks and alerts | Grant is patient- and purpose-specific; never assumes all patient data is visible |
| Medical team web dashboard | Assigned patients, measurement curves, wound evolution, motor observations, investigation reports, protocol approval, decisions and follow-up | Authorized clinicians approve clinical content and record decisions |

Engineering service identities are not a fourth user role. The three AI developers supply backend services and integration contracts; mobile/web teams own rendering, identity flows and notification UX, with joint acceptance testing. Appointment display supports the finalized patient experience; these AI services do not add an appointment-booking product.

### Shared ownership and execution architecture

```text
Patient app / permission-aware caregiver app / IoT adapter
                    | authenticated, attributable inputs
                    v
        API validation + immutable observation/event store
                    |                         |
                    v                         v
  Immediate deterministic safety lane     Analysis lane
  D3 runtime, clinician-approved policy    D1 Twin + time series + CV
                    |                     D2 protocol + knowledge + symptoms
                    |                         |
                    |                     D3 evidence investigation
                    +-----------+-------------+
                                v
                  Role-aware notifications and follow-up
             Patient app / caregiver app / clinician dashboard

Clinician dashboard -> D2 draft/review/approve protocol -> all services
```

D1 owns observation-derived measurements, multimodal Twin snapshots and cautious predictions. D2 owns protocol compilation, approved schedule definitions, symptom structuring, medication evidence and role-scoped assistants. D3 owns deterministic escalation execution, investigation, delivery orchestration and follow-up state. Clinical owners supply and approve thresholds, tests, milestones, content and response pathways. D2 publishes immutable approved configuration; D3 executes it; D1 consumes it. No service silently edits another service's authoritative records.

**Emergency processing cannot depend on an LLM, CV job, forecast, retrieval call or complete Twin snapshot.** Structured warning-sign answers reach the safety lane before optional enrichment. Free text is retained and processed promptly, but an LLM cannot guarantee recognition of all emergencies: pair it with approved structured red-flag questions and conservative deterministic phrase handling validated for each supported language. Do not require a questionnaire or camera test before showing approved emergency instructions when a warning is already identified.

## Shared integration contract v1 — identical in all three specifications

### General conventions

Use HTTPS JSON APIs and authenticated service-to-service events. Proposed routes use `/v1`. Validate JSON with JSON Schema 2020-12 and format checks enabled. IDs are opaque strings. Timestamps are RFC 3339 UTC; retain the patient's IANA timezone for schedules. `occurred_at` describes the event; `received_at` is server ingestion time. Do not substitute receipt time for clinical measurement time.

Every persistent resource carries `patient_id`, `episode_id`, version and source provenance. The server derives actor identity, patient authorization and role from authenticated context; it never trusts a client-supplied role. Raw observations remain append-only. Corrections reference `supersedes_id` and cause a versioned recomputation. A correction does not erase an earlier escalation.

Every mutation accepts `Idempotency-Key`; persist key, caller, operation and request hash. Same key and same body returns the original response; same key and changed body returns `409`. Partition analysis by episode, deduplicate on `event_id`, accept out-of-order events, and record the input watermark used by each result. Consumers support at-least-once delivery with idempotent writes, a transactional outbox, bounded retries and a visible failed-job queue. Safety decisions run before asynchronous analysis retries.

### Event envelope JSON Schema

The envelope is shared. `payload` must additionally pass the domain contract named by `event_type`; this generic envelope alone is not sufficient validation. Unknown versions or types are rejected or quarantined, never guessed.
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SurgiGuardEventV1",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "event_id",
    "event_type",
    "patient_id",
    "episode_id",
    "occurred_at",
    "received_at",
    "producer",
    "trace_id",
    "protocol_version",
    "payload"
  ],
  "properties": {
    "schema_version": {
      "const": "1.0"
    },
    "event_id": {
      "type": "string",
      "minLength": 1
    },
    "event_type": {
      "enum": [
        "observation.recorded",
        "symptoms.structured",
        "medication.reported",
        "protocol.activated",
        "analysis.completed",
        "twin.updated",
        "investigation.completed",
        "alert.created",
        "followup.updated"
      ]
    },
    "patient_id": {
      "type": "string",
      "minLength": 1
    },
    "episode_id": {
      "type": "string",
      "minLength": 1
    },
    "occurred_at": {
      "type": "string",
      "format": "date-time"
    },
    "received_at": {
      "type": "string",
      "format": "date-time"
    },
    "producer": {
      "enum": [
        "ingestion",
        "developer1",
        "developer2",
        "developer3"
      ]
    },
    "trace_id": {
      "type": "string",
      "minLength": 1
    },
    "protocol_version": {
      "type": [
        "string",
        "null"
      ]
    },
    "payload": {
      "type": "object"
    }
  }
}
```
### Domain resources and event payloads

Unless explicitly called optional, fields listed here are required. Expand these contracts into generated schemas and client types in the shared contracts package before parallel implementation. Domain examples below demonstrate valid shapes; production IDs, values and policies must come from approved records.

| Event / owner | Payload contract |
|---|---|
| `observation.recorded` / ingestion, D1 validates metrics | `observation_id`, `kind`, `source`, `quality`, `metrics[]`, `artifact_id` (nullable), `assessment_id` (nullable), `supersedes_id` (nullable). Use the exact observation schema below. |
| `symptoms.structured` / D2 | `report_id`, `original_report_ref`, `mood_label` (nullable), `pain_score` (nullable integer 0–10), `items[]` with `code`, `assertion` (`present/absent/uncertain`), `onset_at` (nullable), `severity` (nullable), `source_span` (nullable); `warning_answers[]` with approved `question_id` and `answer` (`yes/no/unknown`); `extraction_status` (`structured/needs_clarification/unavailable`), `confirmed_by_patient` boolean. Unknown is never absent. |
| `medication.reported` / D2 | `report_id`, `prescription_id`, `scheduled_dose_id` (nullable), `reported_status` (`taken/missed/unsure`), `reported_taken_at` (nullable timestamp), `reporter_id`, `symptom_report_ids[]`. This is a report, not proof of ingestion. |
| `protocol.activated` / D2 | `protocol_id`, `version`, `approval_id`, `effective_at`, `content_hash`, `previous_version` (nullable). Consumer fetches and verifies exact immutable content. |
| `analysis.completed` / D1 | `analysis_id`, `analysis_type` (`physiology/neurological_motor/rehabilitation/wound`), `status` (`complete/limited/abstained`), `observations[]` of typed metric or visible-change findings, `quality`, `evidence[]`, `limitations[]`, `model_version` (nullable), `created_at`. No diagnosis field. |
| `twin.updated` / D1 | `snapshot_id`, `snapshot_version` positive integer, `as_of`, `input_watermark`, `protocol_version`, `dimensions[]`, `forecasts[]`, `evidence[]`, `limitations[]`. Each dimension carries `name`, `status`, `metric_summaries[]`, `latest_observed_at` (nullable), `reference_id` (nullable). Each forecast follows D1's schema. |
| `investigation.completed` / D3 | `investigation_id`, `trigger_event_ids[]`, `snapshot_id` (nullable), `state` (`complete/partial/failed`), `domains[]`, `findings[]`, `missing_data[]`, `conflicts[]`, `uncertainty[]`, `evidence[]`, `safety_decision_ids[]`, `model_version` (nullable). Each finding has `statement`, `evidence_ids[]`, `limitations[]`; no uncited clinical conclusion. |
| `alert.created` / D3 | `alert_id`, `category` (`technical/routine_missing/clinical_review/emergency`), `status`, `reason_codes[]`, `safety_decision_id` (nullable), `investigation_id` (nullable), `evidence[]`, `instruction_template_id`, `recipient_policy_id`, `created_at`. Delivery status belongs to delivery records, not the alert category. |
| `followup.updated` / D3 | `followup_id`, `alert_id`, `state`, `assigned_role` (`patient/caregiver/clinician`), `assignee_id`, `due_at`, `version`, `transition_id`, `completion_evidence_id` (nullable), `clinician_decision_id` (nullable). State transition requirements are defined in D3's specification. |

`quality` is always `{status, reasons, usable_for}`: status is `usable/limited/unusable/unknown`; reasons and usable_for are arrays of strings. Quality is task-specific: a photo may be viewable by a clinician but unsuitable for color comparison. Device quality claims and software quality assessment remain separately attributable in source records.

`evidence` is always an array of `{evidence_id, kind, resource_id, resource_version, observed_at, locator}`. `kind` is `observation/symptom/medication/analysis/protocol/reference/clinical_decision`; `observed_at` and `locator` may be null. A locator is a section, table or source span, not a public image URL. Dereferencing evidence repeats authorization checks. References preserve publisher, title, jurisdiction, revision, retrieval date, content hash and supporting passage in the referenced resource. An evidence record is not a permission grant.

### Observation payload JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ObservationV1",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "observation_id",
    "kind",
    "source",
    "quality",
    "metrics",
    "artifact_id",
    "assessment_id",
    "supersedes_id"
  ],
  "properties": {
    "observation_id": {
      "type": "string"
    },
    "kind": {
      "enum": [
        "physiology",
        "neurological_motor",
        "rehabilitation",
        "wound"
      ]
    },
    "source": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "method",
        "device_id",
        "reporter_id"
      ],
      "properties": {
        "method": {
          "enum": [
            "iot",
            "manual",
            "smartphone_session"
          ]
        },
        "device_id": {
          "type": [
            "string",
            "null"
          ]
        },
        "reporter_id": {
          "type": [
            "string",
            "null"
          ]
        }
      }
    },
    "quality": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "status",
        "reasons",
        "usable_for"
      ],
      "properties": {
        "status": {
          "enum": [
            "usable",
            "limited",
            "unusable",
            "unknown"
          ]
        },
        "reasons": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "usable_for": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      }
    },
    "metrics": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "code",
          "value",
          "unit"
        ],
        "properties": {
          "code": {
            "type": "string"
          },
          "value": {
            "type": "number"
          },
          "unit": {
            "type": "string"
          }
        }
      }
    },
    "artifact_id": {
      "type": [
        "string",
        "null"
      ]
    },
    "assessment_id": {
      "type": [
        "string",
        "null"
      ]
    },
    "supersedes_id": {
      "type": [
        "string",
        "null"
      ]
    }
  }
}
```
Cross-field validators are mandatory: physiology has at least one metric; camera inputs require a valid authorized session and artifact or derived measurements. A BP observation contains both `sbp` and `dbp` from one measurement, with source `manual`; a camera must not estimate BP. Missing readings are absent records, never numeric zero. Accept only these physiological code/unit pairs: `spo2/%`, `hr/beats/min`, `sbp/mmHg`, `dbp/mmHg`, `temperature/Cel`; optionally `rr/breaths/min` only when a reliable approved measurement method exists. Preserve original unit/value in ingestion provenance when converting. Plausibility limits are device/domain validation configuration and are not emergency thresholds. Do not drop clinically concerning values merely because they are unusual.

### Shared API behavior

| Request | Response and authorization |
|---|---|
| `POST /v1/episodes/{episode_id}/observations` | Body: observation payload plus `occurred_at`; `201` with `observation_id`, `event_id`, `safety_status` (`evaluated/pending/fallback_shown`). API constructs the event envelope. Missing active policy cannot masquerade as a safe result. |
| `POST /v1/episodes/{episode_id}/symptom-reports` | Body: original text, emoji choice, pain score, structured answers and occurred time; `202` with `report_id`, `event_id`, `safety_status`. Safety handling starts before LLM extraction. |
| `GET /v1/episodes/{episode_id}/protocol` | Current approved version with permissions and effective interval. Never return a draft as active. |
| `GET /v1/episodes/{episode_id}/twin` | Latest snapshot and staleness; `200` can contain insufficient data, never a fabricated normal state. |
| `GET /v1/episodes/{episode_id}/investigations/{id}` | Authorized report; caregivers receive only their allowed projection. |
| `GET /v1/episodes/{episode_id}/alerts` | Role-filtered alerts plus delivery/follow-up summaries. |

Use `400` malformed JSON; `401` unauthenticated; `403` denied; `404` absent or deliberately concealed resource; `409` idempotency/version conflict; `422` valid JSON but invalid domain content; `503` temporary unavailability. Error body is `{code, message, trace_id, retryable, field_errors[]}`. Do not echo clinical free text in logs or error messages. Accepted-but-incomplete analysis has an explicit status, not a misleading success summary.

## Shared privacy, consent and safety baseline

- Enforce patient/episode/clinician-assignment checks at API, database, retrieval and artifact access. Caregiver grants list data categories, task permissions, effective/expiry dates and revocation. Recheck grants at dispatch and access, not only when a notification is queued.
- Encrypt transport and storage; use short-lived authenticated artifact access; strip unnecessary photo metadata and location. Never place clinical text or photos in push previews by default. Log resource IDs and operational counters rather than raw health content.
- Camera permission is session-specific, opt-in and foreground-only. Stop capture on completion, cancellation or app backgrounding. Operating-system permission alone does not authorize a clinical assessment or long-term media retention.
- Use the minimum necessary media retention. Prefer derived motor features when raw video is unnecessary. The clinical deployment owner must approve exact retention periods, deletion/export handling, backup treatment and legal retention exceptions before collecting patient data. Consent withdrawal prevents new optional capture; it does not silently erase required clinical audit records.
- Training/research consent is separate from care participation. Do not send identifiable records to model vendors without approved processing arrangements and retention settings. Demo records are synthetic; demos do not validate clinical utility.
- No autonomous diagnosis, treatment adjustment, prescription change, discharge decision or declaration of safety. No image-only wound infection/healing claim, movement-only neurological diagnosis, or unvalidated aggregate recovery score.
- Protocol changes, emergency wording, measurement intervals, exercise eligibility and clinically consequential schedule proposals need authorized clinical approval. No numeric medical thresholds are invented in these specs. Missing configuration blocks clinical activation and leaves approved fallback instructions available.

## Shared integration demonstration

Use a synthetic episode `ep_demo_001` for patient `pt_demo_001`, one authorized caregiver, one ungranted caregiver and an assigned clinician. The demonstration procedure and all numerical data are fixtures, not a clinical protocol.

1. D2 compiles a procedure-specific draft from supplied discharge instructions. The clinician reviews restrictions, cadence, camera tests, dressing permissions, verified prescriptions and escalation content, then approves an immutable version.
2. Ingestion accepts IoT SpO2/HR, manual BP and temperature. D1 produces actual trend curves and a Twin with explicit missingness and approved expectations.
3. The patient completes a foreground, consented, approved motor session and reports pain/difficulty; a permitted dressing-change photo is compared with an earlier image. D1 publishes quality-aware findings, without diagnosis.
4. D2 structures an emoji plus free-text report and retrieves a verified medication passage as a possible association. D3 considers this alongside physiological, motor, wound and symptom evidence; the association cannot dismiss warning signs.
5. A non-urgent deviation creates a clinician review alert and authorized practical caregiver task. A separate structured emergency fixture triggers the deterministic safety lane while the LLM is deliberately unavailable; approved patient emergency instructions appear without waiting for investigation.
6. The clinician reviews evidence and records a decision. Notification delivery, acknowledgement, action and clinical closure are recorded separately. The ungranted caregiver sees no episode details.
7. Replay duplicate/out-of-order events, revoke the authorized caregiver grant before queued delivery, submit an unusable photo, decline camera consent and interrupt connectivity. Verify no duplicate clinical action, no unauthorized disclosure and no false “normal” recovery status.

Capture event traces, screen recordings of all three role views, schema validation results, latency measurements and state-transition audit records. Agree operational latency budgets before testing; report observed distributions and failures, not invented clinical performance claims.
