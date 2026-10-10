# SurgiGuard AI — Developer 3
## Evidence Investigation, Safety Escalation and Coordination

**Mission:** turn new recovery observations into timely, attributable action through independent safety rules, bounded evidence investigation, role-aware notifications and verified follow-up. A generated summary is not a diagnosis, and a delivered alert is not completed care.

## 1. Scope, deliverables and non-goals

Own respiratory, hemodynamic and neurological evidence investigation; uncertainty and data-quality synthesis; clinician-approved immediate escalation-rule execution independent of the LLM; notifications to the clinician dashboard and patient/caregiver apps; closed-loop clinical follow-up; and cross-service orchestration.

Deliver a deterministic safety engine, approved-policy loading/validation, event orchestrator, bounded investigation service, notification projections and dispatch records, follow-up state machine, audit trail, failure runbooks and integration tests. Clinical owners author/approve medical rules; D2 versions/publishes approved content; you implement its faithful and timely execution.

Do not independently author medical thresholds, diagnose deterioration, dismiss symptoms because of a medication explanation, automatically prescribe treatment, guarantee emergency response, automatically call emergency services, install home cameras, expand caregiver permissions or add another product role. The platform presents approved urgent instructions and coordinates existing roles; it does not claim an emergency dispatch service.

The three surveillance categories are evidence lenses, not exclusive diagnostic buckets. Wound, medication and functional findings may contribute to any appropriate review. A patient can have multiple concurrent concerns and incomplete evidence.

## 2. Safety and analysis architecture

```text
Validated incoming observation / structured warning answer
             |
             +--> Dedicated safety evaluator --> persisted decision
             |                                  |              |
             |                         approved patient      clinician/authorized
             |                         instructions          caregiver notification
             |
             +--> durable event log --> bounded evidence collection
                                           |
                         D1 Twin/analyses + D2 protocol/symptoms/medications
                                           |
                           evidence graph + contradictions + uncertainty
                                           |
                         validated report --> review notification/follow-up
```

The safety evaluator has a separate execution budget and failure boundary. It does not wait for an image upload, Twin refresh, retrieval response, agent plan or LLM summary. Persist incoming data and the decision/outbox consistently; avoid a database-commit/notification gap. When infrastructure is unavailable, the app retains approved fallback instructions and clearly states that monitoring/delivery is unavailable. Cached rules require integrity, version and validity checks; they cannot silently become permanent stale clinical policy.

Non-urgent jobs may await bounded dependencies; after timeout, emit `partial` with missing evidence. Do not mark a partial investigation complete simply because the model returned text. The deterministic emergency result remains binding even if an investigation suggests a benign explanation.

## 3. Modules and implementation tasks

### D3-A — Independent clinical safety-rule runtime

1. Load only the active approved policy bound to the episode/protocol. Verify approval, content hash, effective interval, applicable operation/recovery phase and supported rule-language version.
2. Use a restricted declarative rule language with typed fields, approved operators and explicit handling of freshness, quality, absence and conflicting inputs. No arbitrary code or LLM-generated executable rules.
3. Support structured symptom/red-flag predicates and approved measurement conditions. The medical team defines exact thresholds, persistence conditions, combinations and fallback actions; these documents intentionally supply none.
4. Evaluate every accepted relevant input promptly. Normal recent measurements cannot automatically negate a new warning symptom. Quality limitations remain visible and are handled by explicit policy; never reinterpret an unusable sensor value as normal.
5. Emit a persisted safety decision with input IDs, policy version, matched rule IDs, outcome, missing context and instruction template. Outcomes are `emergency/clinical_review/no_match/indeterminate`. `no_match` means no rule matched, not “patient safe.”
6. On emergency outcome, issue approved patient instructions and notifications independently of further AI work. Suppress prompts for extra motor testing or wound photography that would delay urgent assessment.
7. Idempotently handle retries. Duplicate event processing cannot duplicate a clinical action; new worsening information can legitimately create an additional decision. Dedupe keys must include patient/episode, rule and the approved episode/time-window semantics rather than just symptom name.
8. Log policy execution failures and activate the approved fallback pathway. Missing policy never results in a green status. Restrict live rule changes to approved, versioned deployment with rollback.

Safety handling for free text: receive original reports immediately; use approved structured questions and tested deterministic matching where available. D2 extraction can add evidence but cannot be the only route for an emergency sign. Unknown text is not clearance. Define a clinically approved unresolved-report workflow; do not invent a universal phrase list or claim exhaustive detection.

### D3-B — Bounded evidence investigation

Use an explicit state machine: `queued → collecting → synthesizing → validating → complete/partial/failed`. Set limits on tool calls, retrieval size, elapsed time and retries. The model can summarize bounded evidence; it does not decide which unrestricted tools to execute.

Evidence collection order:

- Triggering observations/reports and any immediate safety decisions.
- Current approved protocol, restrictions, escalation policy and expected milestones.
- D1 snapshot at a recorded watermark, actual raw measurements, quality flags, motor/rehabilitation findings and wound comparison limitations.
- D2 symptom history, verified regimen, reported adherence and product-specific reference evidence when available.
- Existing related alerts, clinician decisions and unresolved follow-up tasks.

Build a typed evidence graph or equivalent structured table: each claim links to observed facts and source versions; missing facts and contradictions are first-class records. Separate directly observed measurements, patient/caregiver reports, model-derived features, reference associations and clinician decisions.

The report answers: what changed; compared with what and when; what evidence supports it; what conflicts; what is missing; how acquisition quality limits interpretation; which safety rules already ran; and what approved review/follow-up path applies. Do not manufacture a probability of deterioration or a numerical certainty score.

### D3-C — Three surveillance workflows

| Workflow | Evidence to investigate | Mandatory limits |
|---|---|---|
| Respiratory | SpO2 time series, quality/freshness, reported breathing symptoms, HR when relevant, RR only from an approved reliable method, approved procedure context | A reassuring isolated reading does not dismiss reported symptoms; no camera-derived RR by default; no diagnosis of a respiratory condition |
| Hemodynamic | HR, paired manually entered BP, measurement provenance, dizziness/faintness/weakness reports, temperature or medication context when relevant | Do not infer BP from HR; preserve uncertain cuff entry; do not attribute symptoms solely to a medication; no autonomous treatment |
| Neurological | Sudden warning reports, questionnaire/caregiver observations, approved guided motor features and comparisons, acquisition limitations | Warning signs bypass movement tests; motor changes are observable performance evidence, not a neurological diagnosis |

Cross-cutting wound evidence considers visible changes alongside pain, temperature and symptoms, with photo quality and authorization. Rehabilitation evidence concerns approved functional recovery only. Route review outside these three lenses when the approved plan requires it; do not force every concern into one of three diagnoses.

### D3-D — Uncertainty and quality synthesis

Maintain distinct axes: data availability, recency, sensor/manual-entry reliability, media comparability, model applicability, consistency across sources, reference support and protocol applicability. Do not average these into an unexplained single score.

For every investigation, list absent expected data, stale observations, contradictory reports, incompatible measurements, model abstentions and reference gaps. Respect timestamp ordering: a more recent symptom can coexist with older normal measurements. A poor photo does not discredit a patient symptom, and an invalid motor session does not prove impaired movement.

Technical problems create technical tasks when appropriate. Repeat-measurement instructions must be approved and must never delay emergency advice. If patient quality cannot be resolved, provide a partial report to the clinician rather than repeated burdensome data requests.

### D3-E — Role-aware notifications

Maintain four explicit alert categories: `technical`, `routine_missing`, `clinical_review`, `emergency`. Classification comes from approved policy and validated evidence handling, not arbitrary LLM adjectives. An LLM may draft a clinician summary; emergency patient instructions remain approved templates.

Recipient projections:

- **Clinician dashboard:** assigned episode, category, triggering facts, actual measurements, investigation evidence/uncertainty, policy decision, prior actions and follow-up owner.
- **Patient app:** approved plain-language instruction, timing/urgency and acknowledgement/action affordance; no unsupported diagnosis or assurance.
- **Authorized caregiver app:** only granted support information, practical tasks and permitted alerts. Receipt of an alert does not grant access to restricted images or medication details.

Create separate delivery records for each recipient/channel with `queued/sent/delivered/failed/expired`, provider receipt where available, attempt count and next retry. A provider accepting a message does not prove that the person read it. Check grants and clinician assignments at dispatch and deep-link open. Push previews should avoid sensitive details.

Use policy-defined deduplication/grouping for non-urgent alerts, preserving every triggering event. Emergency re-escalation and delivery retries follow approved rules; grouping must not hide worsening signals. Operational alert load is measurable, but notification reduction cannot override clinical policy. If delivery fails, keep an actionable failure state and use only configured approved alternate pathways. Do not invent SMS/email/call integrations outside the specified apps/dashboard.

### D3-F — Closed-loop follow-up

Keep notification state separate from clinical workflow. Proposed follow-up states:

```text
open -> assigned -> acknowledged -> action_recorded -> awaiting_verification -> closed
                     |                   |                    |
                     +-------------------+--------------------+-> overdue
any nonterminal state -> escalated
closed -> reopened (new evidence or clinician decision; preserve prior closure)
```

`overdue` and `escalated` preserve the previous stage, owner and due date; they are not successful completion. A safer implementation stores `stage` and independent overdue/escalation flags internally, projecting the state contract consistently. Document which representation is used and test transitions.

- `assigned`: authorized named owner or approved team queue, task description and due time exist.
- `acknowledged`: intended recipient explicitly acknowledges receipt; delivery receipts do not qualify.
- `action_recorded`: actor records what was done, when and by whom; a checkbox alone is not proof of clinical resolution.
- `awaiting_verification`: required completion evidence/clinical review remains pending.
- `closed`: required task evidence and authorized verification exist. Clinical alerts require clinician decision/closure; routine practical tasks may use the approved verifier policy.
- `overdue`: approved due window passed without the required action; trigger the approved re-escalation path.
- `reopened`: new evidence or an authorized decision reopens follow-up, linking the previous closure rather than overwriting it.

Track patient receipt, caregiver practical help, medical review, documented instructions and verification separately. An emergency task cannot close merely because instructions were shown. The platform cannot verify that medical care occurred unless an authorized record confirms it; unknown remains unknown. Clinician records may revise the care plan via D2, never by directly editing an old approved protocol.

### D3-G — Cross-service orchestration and recovery

Use durable events with an outbox, idempotent consumers and episode-level correlation. Store trace IDs across D1/D2/D3 calls. Apply optimistic concurrency to follow-up updates. Provide bounded retries with backoff, a failed-job queue and explicit operator-visible failure reasons through appropriate existing interfaces.

Handle delayed D1 analysis by completing an initial partial investigation, then issuing a linked revision when results arrive. Keep the original report and notification context. Never overwrite an already-acted-upon report without version history. Protocol activation invalidates affected cached configuration and requires version-specific replay decisions.

Prevent stale jobs from notifying after caregiver revocation, duplicating tasks after reconnect or closing an alert after new evidence arrives. Cancellation, timeout and replay must leave consistent state. Runtime monitoring focuses on event delay, safety evaluation failure, queue age, dependency error, notification delivery and follow-up age, without logging raw health data.

## 4. API contracts and schemas

Use the shared envelope/quality/evidence definitions. The safety service has a distinct endpoint and permissions from the LLM-facing investigation service.

| Endpoint | Request | Response |
|---|---|---|
| `POST /v1/episodes/{episode_id}/safety-evaluations` | `event_ids[]`, exact `protocol_version` | Internal safety ingress; `201` decision, immediate outbox actions; no LLM call |
| `POST /v1/episodes/{episode_id}/investigations` | `trigger_event_ids[]`, `safety_decision_ids[]` | Internal service; `202` investigation ID/state |
| `GET /v1/episodes/{episode_id}/investigations/{id}` | Authorized caller | Versioned complete/partial/failed report with evidence |
| `POST /v1/episodes/{episode_id}/alerts/{id}/acknowledgements` | `expected_version`, actor acknowledgement | `201`; does not close clinical follow-up |
| `POST /v1/episodes/{episode_id}/followups/{id}/transitions` | `expected_version`, `target_state`, `evidence_ids[]`, `clinician_decision_id` nullable | `201` transition; `409` stale version; reject unauthorized/invalid transition |
| `POST /v1/episodes/{episode_id}/clinical-decisions` | Authorized clinician decision, linked alert/report, instructions and follow-up requirements | `201` auditable decision; any protocol change routes through D2 approval |

### Safety decision JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SafetyDecisionV1",
  "type": "object",
  "additionalProperties": false,
  "required": ["decision_id", "patient_id", "episode_id", "protocol_version", "policy_version", "evaluated_at", "input_event_ids", "matched_rule_ids", "outcome", "instruction_template_id", "limitations"],
  "properties": {
    "decision_id": {"type": "string"},
    "patient_id": {"type": "string"},
    "episode_id": {"type": "string"},
    "protocol_version": {"type": ["string", "null"]},
    "policy_version": {"type": ["string", "null"]},
    "evaluated_at": {"type": "string", "format": "date-time"},
    "input_event_ids": {"type": "array", "minItems": 1, "items": {"type": "string"}},
    "matched_rule_ids": {"type": "array", "items": {"type": "string"}},
    "outcome": {"enum": ["emergency", "clinical_review", "no_match", "indeterminate"]},
    "instruction_template_id": {"type": ["string", "null"]},
    "limitations": {"type": "array", "items": {"type": "string"}}
  },
  "allOf": [{"if": {"properties": {"outcome": {"const": "emergency"}}}, "then": {"properties": {"policy_version": {"type": "string"}, "protocol_version": {"type": "string"}, "matched_rule_ids": {"minItems": 1}, "instruction_template_id": {"type": "string"}}}}]
}
```

A synthetic decision demonstrates architecture without inventing a medical threshold or warning definition:

```json
{
  "decision_id": "sd_demo_001",
  "patient_id": "pt_demo_001",
  "episode_id": "ep_demo_001",
  "protocol_version": "protocol_demo_v1",
  "policy_version": "policy_demo_v1",
  "evaluated_at": "2026-10-10T08:06:00Z",
  "input_event_ids": ["ev_warning_001"],
  "matched_rule_ids": ["approved_fixture_warning_rule"],
  "outcome": "emergency",
  "instruction_template_id": "approved_fixture_emergency_text",
  "limitations": ["Synthetic integration fixture; not a deployable clinical rule."]
}
```

An alert event resulting from that decision:

```json
{
  "schema_version": "1.0",
  "event_id": "ev_alert_001",
  "event_type": "alert.created",
  "patient_id": "pt_demo_001",
  "episode_id": "ep_demo_001",
  "occurred_at": "2026-10-10T08:06:00Z",
  "received_at": "2026-10-10T08:06:00Z",
  "producer": "developer3",
  "trace_id": "trace_demo_001",
  "protocol_version": "protocol_demo_v1",
  "payload": {
    "alert_id": "alert_demo_001",
    "category": "emergency",
    "status": "open",
    "reason_codes": ["approved_fixture_warning_rule"],
    "safety_decision_id": "sd_demo_001",
    "investigation_id": null,
    "evidence": [{"evidence_id": "evref_warning_001", "kind": "symptom", "resource_id": "sym_warning_001", "resource_version": "1", "observed_at": "2026-10-10T08:06:00Z", "locator": "warning_answers"}],
    "instruction_template_id": "approved_fixture_emergency_text",
    "recipient_policy_id": "recipient_policy_demo_v1",
    "created_at": "2026-10-10T08:06:00Z"
  }
}
```

`investigation_id=null` is intentional: emergency notification does not wait for the investigation. Clinical closure must link to an authorized decision, even if the investigation remains partial.

## 5. Data and evaluation plan

Develop synthetic event replays plus clinician-authored scenario labels. Use consented retrospective records only under approved access and evaluation arrangements. Label expected rule outcomes, notification recipients, evidence gaps and follow-up transitions. Do not create clinical accuracy claims from passing synthetic rule fixtures.

| Evaluation area | Method and measures |
|---|---|
| Deterministic rules | Exhaust approved rule truth tables, boundary values, stale/missing/poor-quality inputs and conflicting symptoms; measure exact policy execution and uncovered conditions |
| Safety latency | Measure ingestion-to-decision and decision-to-patient-instruction separately from provider delivery/read latency, under normal load and fault injection; report distributions against pre-agreed operational budgets |
| Investigation | Clinician-adjudicated report support, critical omission, contradiction preservation, provenance correctness, uncertainty and inappropriate reassurance; compare templated and LLM summaries |
| Routing | Exhaust role/grant/category matrix, revoked grants, assignment changes, cross-episode attempts and deep-link access |
| Follow-up | State-machine/property tests for duplicate transitions, concurrency, overdue escalation, invalid closure and reopen behavior |
| Orchestration | Replay delayed/duplicated/reordered events; crash before/after commit, dependency timeouts, queue backlog, reference outage and LLM outage |

Use patient/episode-level splits for clinical records and hold out scenario families for evaluation. Report event counts, population/context, assessor agreement and confidence intervals where appropriate. Set model-specific clinical validation criteria before test review. Track false review burden and missed labeled concerns without claiming diagnostic sensitivity from non-diagnostic tasks.

Operational acceptance targets must be defined with the clinical/product team: safety evaluation latency, fallback display behavior, notification retry windows, clinician response expectations and overdue escalation timing. None are invented here. A measurable latency target is not a guarantee that someone will provide care in that interval.

## 6. Privacy, consent and dependency handoffs

D2 provides immutable approved rules/templates, activation events, due tasks, structured symptoms and verified medication evidence. D1 provides versioned Twin snapshots, actual time series, media/motor quality and interpretable findings. Identity services provide active caregiver grants and clinician assignments. App teams provide approved instruction display, offline/failure messaging and explicit acknowledgements.

Store audit records for decisions, retrieval scopes, policy versions, recipients, delivery attempts, transitions and clinical closure. Limit raw content; do not copy wound images or medication details into generic notification logs. Clinical images remain in the authorized media service. Caregiver revocation cancels pending deliveries and prevents new reads; preserve required audit records without turning them into caregiver-visible history.

Use least-privilege service permissions. The investigation model cannot approve protocols, close follow-up, expand sharing or modify safety rules. Model output is schema-checked and evidence-validated before display; safety outcomes cannot be downgraded by generation.

## 7. Acceptance criteria and test matrix

| ID | Pass condition | Required test |
|---|---|---|
| D3-01 | Emergency evaluation and approved instructions work with LLM/CV/retrieval unavailable | Disable every analysis dependency during a structured warning fixture |
| D3-02 | Missing/invalid policy yields explicit indeterminate/fallback behavior | Expired approval, bad hash, unsupported rule version and no active protocol |
| D3-03 | Quality uncertainty never silently becomes normality | Disconnected sensor, stale reading, low-quality image and contradictory symptom |
| D3-04 | Every clinical report finding cites evidence or is removed/qualified | Fabricated citation, conflicting sources and partial data cases |
| D3-05 | Four alert categories stay distinct and clinically meaningful | Technical error, missed routine reading, non-urgent deviation and emergency fixtures |
| D3-06 | Role-specific notifications disclose only authorized content | Revoked caregiver, restricted medication/wound permissions and changed clinician assignment |
| D3-07 | Delivery/acknowledgement cannot close a clinical alert | Attempt closure after push receipt and patient acknowledgement only |
| D3-08 | Overdue and reopened work remains visible with an owner | Missed due time, new evidence after closure and simultaneous updates |
| D3-09 | Event replay does not duplicate clinical action or lose new evidence | Duplicate event IDs, out-of-order completion and worker crash/restart |
| D3-10 | Forecasts and medication explanations cannot downgrade urgent rule results | Benign-looking forecast/possible side effect alongside emergency decision |

Engineering gates require all applicable safety invariants to pass, no unresolved critical defects, a complete audit trail and a clinician-approved policy set. Clinical release requires the separate evidence review appropriate to the intended use.

## 8. Phased plan and integration demonstration

1. **Policy and state contracts:** agree D2 policy language, D1 evidence semantics, recipient grants, task states and failure behavior. Deliver truth-table fixtures and clinical configuration checklist.
2. **Deterministic safety first:** implement independent evaluation, persisted decisions, approved instruction delivery and audit/outbox. Demonstrate functioning safety with all AI disabled.
3. **Notifications and follow-up:** implement four categories, role projections, delivery records, acknowledgements, due windows and clinical verification. Demonstrate failed delivery and overdue ownership.
4. **Evidence investigation:** add bounded D1/D2 retrieval, quality synthesis, contradictions and report validation. Begin with templates; enable LLM synthesis only after groundedness evaluation.
5. **Cross-service integration:** run the shared discharge-to-follow-up scenario across all three role views; verify restricted caregiver access and emergency bypass of AI.
6. **Fault and release gate:** replay failures, document policy rollback and operational response to stalled safety evaluation, obtain clinical approval of rules/wording and deliver acceptance evidence.

**Done means:** a concerning input reaches the appropriate approved pathway, all recipients receive only permitted information, every clinical action remains attributable and unresolved follow-up stays visibly unresolved.

## 9. Supporting primary reference

[FDA: Pulse Oximeters](https://www.fda.gov/medical-devices/products-and-medical-procedures/pulse-oximeters), verified 10 October 2026, supports treating pulse-oximetry readings with known limitations rather than as infallible evidence. It is background for quality handling, not a source of patient-specific escalation thresholds. The actual escalation policy must come from the clinical team.

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
