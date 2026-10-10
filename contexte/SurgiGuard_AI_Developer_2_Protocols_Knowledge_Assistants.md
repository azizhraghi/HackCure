# SurgiGuard AI — Developer 2
## Recovery Protocols, Medical Knowledge and Assistants

**Mission:** turn verified discharge information and medical references into reviewable surveillance plans, attributable symptom/medication evidence and helpful role-aware responses. Every clinically consequential plan requires authorized clinician approval.

## 1. Scope, deliverables and non-goals

Own the Recovery Protocol Compiler, operation-specific surveillance configuration, medication safety/adherence evidence, emoji and free-text symptom structuring, and the patient and permission-aware caregiver RAG assistants. Provide versioned structured outputs to D1 and D3; do not hide essential safety facts inside chat text.

Deliver compiler/review APIs, protocol schemas and fixtures, a reference ingestion and versioning pipeline, medication evidence services, symptom extraction contracts, role-scoped assistant interfaces, clinical-content review records and evaluation reports.

Do not autonomously prescribe, change medication dose, create an operation-specific clinical protocol from model memory, approve a plan, independently alter surveillance cadence, grant caregiver access or close clinical follow-up. Do not diagnose from chat or reduce concern because a reported symptom could be a drug adverse effect. No unrelated medical knowledge product or unrestricted general-purpose clinical agent is included.

The patient is recovering at home after surgery. Instructions can depend on the operation, recovery stage and restrictions. A caregiver may help with a task while lacking permission to see the patient's medication list or wound images. The assistant must honor that distinction in both retrieval and answers.

## 2. Modules and actionable tasks

### D2-A — Recovery Protocol Compiler

**Inputs:** verified procedure identifier/name, surgery/discharge dates, discharge instructions, clinician-provided restrictions, approved milestone expectations, supported measurement devices/methods, verified prescriptions and approved escalation policy content. Each source needs ID, version and provenance. Treat unverified extracted text as draft material.

Pipeline:

1. Ingest and normalize discharge documents/structured fields. Preserve source spans and flag missing or conflicting instructions. An LLM can extract or propose structure; it cannot invent omitted timing, numerical thresholds or exercises.
2. Map the procedure and recovery phase to a clinician-maintained approved template when available. Unsupported operations produce a draft with unresolved fields, not a guessed protocol.
3. Generate a typed draft: task definitions, eligibility/restrictions, timing, reference expectations, medication reminder bindings, escalation policy references and stop criteria. Attach evidence to each clinical instruction.
4. Run deterministic completeness and conflict validators. Examples: photo timing outside permitted dressing changes, an exercise contradicting a restriction, medication reminder without a verified prescription, or a rule with no approved patient instruction.
5. Present a reviewable diff to the assigned authorized clinician. Identify unchanged template content, patient-specific changes, missing information and provenance. Approval must bind the full content hash and version, including referenced rule/configuration versions.
6. Activate only after authorized approval and successful validation. Publish `protocol.activated`. Versions are immutable; changes create a new draft. Store approval identity, timestamp, effective interval and reason.
7. On activation, notify consumers and reconcile future tasks. Completed tasks retain the old version. Avoid duplicate reminders and preserve pending follow-ups unless the clinician explicitly revises them.

Separate document states `draft → in_review → approved → active → superseded/retired`. `approved` does not imply active before `effective_at`. Reject self-approval by an AI service and stale review submissions using resource versions/content hashes. Missing or withdrawn approval blocks future clinical activation; keep appropriate approved fallback information available.

### D2-B — Personalized surveillance cadence

Build a declarative schedule engine, not a prompt that asks an LLM what to do next. The approved protocol defines timing type, timezone, anchor, window, frequency where specified, applicable recovery phase, prerequisites and permitted conditions.

| Task | Required configuration |
|---|---|
| SpO2/HR physiology | Continuous or periodic according to hardware capability and approved protocol; do not promise continuous measurements from intermittent hardware |
| Manual BP | Clinician-defined interval/window, approved measurement instructions and separate-monitor source |
| Temperature | Prescribed intervals and/or approved symptom-triggered conditions |
| Neurological movement | Approved assessment ID/version, recovery phase, eligibility, restrictions and stop instructions |
| Wound photo | Permitted dressing-change task binding; no independent reminder to uncover the wound |
| Pain/symptom check-in | Approved scheduled and symptom-triggered questions, numeric and visual options |
| Rehabilitation | Approved exercise ID/version, restrictions and planned cadence |
| Medication reminder | Verified prescription and scheduled-dose instance; conditional instructions remain exactly those approved |

Store planned occurrences separately from observed completion. Handle timezone changes, daylight-saving transitions, late entry, offline synchronization, missed occurrences, pauses and protocol replacement. Missing check-in is a routine monitoring concern; D3 categorizes escalation using policy and context. A symptom-triggered task must not postpone immediate warning-sign instructions.

AI proposals require a rationale, supporting observation IDs and a review diff. They remain `proposed` until approved; never silently write active schedules. Do not infer a missed medication dose from an unopened reminder. Do not assume patient availability or invent a new monitoring frequency.

### D2-C — Medication safety and adherence intelligence

1. Store the verified prescription: medication identity, ingredient/formulation/strength, prescribed instructions, effective dates, source and verifier. Preserve ambiguity for clinician clarification rather than fuzzy-matching a brand to the wrong product.
2. Generate reminder instances directly from that verified regimen. Record patient-reported taken/missed/unsure status, scheduled dose ID, report time and actual taken time if supplied. Editing a report preserves audit history.
3. Build a curated trusted reference collection selected with the clinical team for the deployment's jurisdiction. Official product labeling and approved formularies may be used. US DailyMed is one source option for relevant US labeling, not a substitute for local verification or proof that every listed product is approved.
4. Retrieve supporting passages for a reported concern. Distinguish a documented possible adverse effect from causation in this patient. Include product match, relevant passage, reference version, jurisdiction and limitations.
5. If the verified source supports a potential safety issue, create a reviewable evidence item for D3/clinician. Do not expand into unsupported interaction claims or infer absent contraindications from an incomplete medication record.
6. Preserve other explanations and current observations. A possible medication association must never dismiss serious postoperative warning signs or delay deterministic escalation.
7. Missing source, ambiguous drug identity, stale reference or failed retrieval produces an explicit limitation and clinician-review route. Do not fill gaps with LLM memory or tell the patient to stop, skip, double or change a dose.

Citation provenance is part of the API, not decoration in prose. Store the exact reference passage internally subject to licensing, with section/locator and content hash. When references change, record the new version and identify affected cached explanations for review.

### D2-D — Accessible symptom understanding

Support the specified mood choices: 😄 very good, 🙂 good, 😐 okay, 😣 unwell, 😫 very unwell. Store stable codes (`very_good/good/okay/unwell/very_unwell`) alongside displayed text and raw emoji. Mood is not a diagnosis, urgency level or numeric pain score.

- Accept optional free text, symptom categories and a separate numeric pain scale. Preserve the original report and language, with minimal necessary retention.
- Extract only supported fields: symptom, presence/absence/uncertainty, onset/time course when supplied, patient-described severity, location when supplied, and source span. Do not equate “no fever measurement” with “no fever.”
- Use schema-constrained extraction plus deterministic validation. Separate the patient's assertions from model inference. Provide concise confirmation/clarification for ambiguous statements, especially negation, timing and multiple symptoms.
- Forward structured warning answers immediately to D3. Clinician-approved deterministic phrase handling can provide an additional signal, but neither the phrase list nor LLM extraction can establish that unrecognized text is safe.
- Follow-up questions must come from approved question sets and remain short. If a warning is already present, do not make further answers a prerequisite for emergency instructions.
- Record caregiver observations with reporter identity and scope. Do not present them as patient-confirmed statements. Distinguish symptom onset from entry time and avoid medicalizing ordinary mood words.

### D2-E — Patient and caregiver RAG assistants

Use the same retrieval infrastructure with different, server-enforced access scopes. Patient answers may use that patient's active protocol, discharge instructions, verified regimen, authorized current recovery summaries and curated reference passages. Caregiver answers use only the granted data categories and tasks. Retrieval filters apply before documents enter the model context; output redaction alone is insufficient.

Execution sequence:

1. Authenticate actor, patient/episode and permission scope; resolve current protocol and source versions.
2. Run the independent structured safety path when applicable. Chat is not an emergency intake guarantee and must not hide approved urgent instructions.
3. Classify request into in-scope information, symptom reporting, reminder/task help or clinical decision request. Clinical decisions remain with the medical team.
4. Retrieve using exact metadata filters plus lexical/semantic search where useful; rerank within the authorized corpus. Prefer the active patient-specific approved instruction over unrelated generic text; conflicts are surfaced for clinical review.
5. Generate a concise answer using only supported context. Return citations for clinical statements and source scope. If evidence is insufficient, say what is missing and route the question appropriately.
6. Validate structured output, citation existence/support and prohibited medication/diagnostic actions. Send symptom evidence to D3 where appropriate without granting the assistant permission to prescribe or close tasks.
7. Log model/prompt/reference versions and resource IDs, minimizing raw health content. Enforce session isolation; never reuse one patient's retrieved context in another patient's answer.

Treat documents, symptom text and retrieved passages as untrusted data. Ignore embedded instructions to change roles, reveal another patient's data or bypass clinical rules. Restrict tools to read/structured-report operations needed for this scope. The assistant may draft a schedule proposal; it cannot call the approval endpoint.

## 3. Architecture, tools and storage

Recommended components: typed API service; relational protocol/prescription/task tables; immutable source store; retrieval index with patient/tenant/access metadata; schema-constrained LLM adapter; deterministic validators and schedule expander. Choose a model only after evaluating structured extraction, groundedness, privacy and latency on the actual tasks. Pin model/prompt versions and provide a retrieval-only/templated fallback for approved instructions.

Tables/resources: source documents, source passages, protocol drafts, approved protocol versions, clinical approvals, task definitions, task occurrences, prescriptions, medication reports, symptom reports, extraction runs, caregiver grants (identity service authoritative), assistant runs and citations. Keep embeddings within the same access/retention controls as source text. Re-indexing or model upgrades must not change active clinical content without review.

Schedule execution can be a deterministic job worker; D3 handles cross-service orchestration and notifications. Agree the boundary: D2 emits due task definitions/occurrences; D3 delivers, follows up and records coordination state. Do not implement two competing reminder clocks.

## 4. Developer-specific schemas and API examples

The shared section defines envelope, evidence, errors and cross-service event payloads. This compact schema describes a **protocol activation record**; the referenced immutable protocol content must separately pass the detailed validators above. It intentionally does not encode unspecified clinical intervals.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ProtocolActivationV1",
  "type": "object",
  "additionalProperties": false,
  "required": ["protocol_id", "version", "approval_id", "effective_at", "content_hash", "previous_version"],
  "properties": {
    "protocol_id": {"type": "string", "minLength": 1},
    "version": {"type": "string", "minLength": 1},
    "approval_id": {"type": "string", "minLength": 1},
    "effective_at": {"type": "string", "format": "date-time"},
    "content_hash": {"type": "string", "pattern": "^sha256:[a-f0-9]{64}$"},
    "previous_version": {"type": ["string", "null"]}
  }
}
```

| Endpoint | Request | Response and enforced boundary |
|---|---|---|
| `POST /v1/episodes/{episode_id}/protocol-drafts` | `source_ids[]`, `procedure_ref`, `template_version` (nullable) | `201`: draft ID/version, unresolved fields, evidence and review diff |
| `POST /v1/episodes/{episode_id}/protocol-drafts/{id}/approve` | `expected_version`, `content_hash`, `review_note` | Authorized clinician only; `201` approval record or `409` stale content; service role denied |
| `POST /v1/episodes/{episode_id}/protocol-drafts/{id}/activate` | `approval_id`, `effective_at` | `201` activation; validate approval/hash and schedule invariants; publish exact version |
| `GET /v1/episodes/{episode_id}/tasks?from=...&to=...` | Time-bounded query | Approved task occurrences with timezone, due windows and protocol version |
| `POST /v1/episodes/{episode_id}/medication-reports` | Shared `medication.reported` payload | `201` report/event IDs; source remains patient/caregiver reported |
| `POST /v1/episodes/{episode_id}/medication-evidence` | `prescription_id`, `symptom_report_id` | Internal service; grounded evidence or explicit unavailable/ambiguous status |
| `POST /v1/episodes/{episode_id}/assistant-messages` | `message`, `conversation_id` | `200`: answer/status, evidence, limitations and structured routing result; role resolved by server |

A structured symptom event, with synthetic content:

```json
{
  "schema_version": "1.0",
  "event_id": "ev_sym_001",
  "event_type": "symptoms.structured",
  "patient_id": "pt_demo_001",
  "episode_id": "ep_demo_001",
  "occurred_at": "2026-10-10T08:05:00Z",
  "received_at": "2026-10-10T08:05:01Z",
  "producer": "developer2",
  "trace_id": "trace_demo_001",
  "protocol_version": "protocol_demo_v1",
  "payload": {
    "report_id": "sym_demo_001",
    "original_report_ref": "raw_sym_demo_001",
    "mood_label": "unwell",
    "pain_score": null,
    "items": [{"code": "dizziness", "assertion": "present", "onset_at": null, "severity": null, "source_span": "I feel dizzy"}],
    "warning_answers": [],
    "extraction_status": "needs_clarification",
    "confirmed_by_patient": false
  }
}
```

An empty warning-answer array means no answers were supplied; it does not mean no warning signs. D3 must retain that uncertainty and follow the approved pathway.

Medication evidence response shape:

```json
{
  "result_id": "medev_demo_001",
  "patient_id": "pt_demo_001",
  "episode_id": "ep_demo_001",
  "prescription_id": "rx_demo_001",
  "symptom_report_id": "sym_demo_001",
  "status": "unavailable",
  "possible_associations": [],
  "evidence": [],
  "limitations": ["No verified product-specific reference is available in this synthetic fixture."],
  "clinical_action": "review_by_medical_team"
}
```

For `status=available`, each `possible_associations` item requires `symptom_code`, `statement`, `evidence_ids[]` and `causality=not_established`. Allowed statuses are `available/unavailable/ambiguous`. Never fabricate a reference to make this response appear complete.

Assistant response contract: `{answer_id, status, answer_text, evidence[], limitations[], route}` where status is `answered/needs_clarification/insufficient_evidence/safety_routed`; route is `none/symptom_report/clinical_review/emergency_policy`. `route` does not itself prove that D3 completed delivery; use a linked D3 event/decision record when routing occurs. Emergency text comes from the approved template, not a newly generated instruction.

## 5. Data and evaluation plan

Build a clinician-reviewed fixture corpus from de-identified or synthetic discharge instructions, prescriptions, symptom expressions and caregiver permissions. Obtain permission for real documents and annotate provenance. Include supported languages and locally relevant terminology only after agreeing actual deployment languages; do not claim multilingual coverage from a multilingual model alone.

| Capability | Evaluation design | Report |
|---|---|---|
| Compiler | Compare structured drafts with clinician-authored expected fields; hold out templates/procedures where feasible | Field correctness, omissions, invented instructions, contradiction detection, source-span coverage, reviewer edits and approval time |
| Scheduling | Deterministic reference schedules including timezone changes, late activation, pause and replacement | Occurrence correctness, duplicates, off-window photos, missed reminder handling and version attribution |
| Symptom extraction | Clinician-labeled negation, timing, emojis, colloquial text, spelling variations, uncertainty and mixed reports | Per-field precision/recall, critical omission counts, clarification rate, disagreement and error examples |
| Medication evidence | Verified exact-product reference cases plus ambiguous/missing/stale references | Product match, citation support, unsupported association rate and incorrect treatment suggestion count |
| RAG | Clinician-scored answer tasks and adversarial access/prompt-injection cases | Retrieval relevance, citation entailment, abstention appropriateness, harmful unsupported statements and permission leakage |

Split by patient/document source rather than random near-duplicate chunks. Record source/model/prompt versions, sample sizes, annotation agreement and uncertainty. Keep synthetic engineering results separate from clinical validation. Set clinical acceptance thresholds with the medical team before reviewing the held-out test results. No claimed accuracy or safety rate appears without an actual study and its limitations.

Use regression suites for every prompt, model, retrieval-index or reference change. Evaluate cases where a normal recent reading conflicts with a new symptom, where the caregiver lacks medication access, and where a possible adverse effect coexists with an urgent warning. Safety-critical scenario failures block release even if average extraction quality is high.

## 6. Dependencies, privacy and safety controls

Clinical owners provide approved source templates, prescription verification, schedule rules, tests/restrictions, escalation instructions and supported language wording. D1 provides evidence-based trends and compatible measurement definitions. D3 supplies safety ingress, notification/follow-up APIs and investigation evidence requirements. Identity/app services supply verified actor context and caregiver grant checks.

No LLM gets broad database access. Filter retrieval by episode, source state, effective version and permissions. Delete or invalidate cached contexts when a caregiver grant is revoked. A chat history must not preserve a new route to documents after access is removed; retention and any previously disclosed content need explicit handling. Do not use patient chat for training by default.

If the LLM is unavailable, patients can still submit structured symptoms, view approved instructions and report adherence. Schedule execution and the D3 emergency lane remain operational. If references are unavailable, stop unsupported medication explanations; do not stop the patient's ability to request clinical help.

## 7. Acceptance criteria and tests

| ID | Pass condition | Required test |
|---|---|---|
| D2-01 | Draft cannot become active without authorized approval of exact content | Service approval attempt, stale hash, missing fields and superseded draft |
| D2-02 | No generated clinical interval, exercise or threshold reaches active content without approval | Deliberately incomplete source and conflicting restriction fixtures |
| D2-03 | Wound prompts stay bound to permitted dressing changes | Replacement schedule, missed photo and no-permission scenarios |
| D2-04 | Verified prescriptions are the only source of reminder regimens | Ambiguous brand/strength and unverified source cases |
| D2-05 | Mood, pain and clinical symptoms remain distinct | Every emoji, missing pain score, negation and uncertainty fixtures |
| D2-06 | Medication association never suppresses emergency routing | Possible side-effect evidence plus structured warning sign |
| D2-07 | All clinical assistant statements have support or explicit abstention | Clinician review and invalid-citation injection |
| D2-08 | Caregiver retrieval respects exact active grants | Cross-patient request, hidden wound image, revoked access and queued answer |
| D2-09 | Model outages do not prevent safety handling or routine structured reporting | LLM/retrieval failure injection |
| D2-10 | Task timing is deterministic, versioned and duplicate-free | Timezone, daylight-saving, offline replay and protocol replacement |

## 8. Phased plan and integration demonstration

1. **Sources and contracts:** agree procedure input, prescription verification, symptom vocabulary, permission scopes and approval schema. Deliver clinician review checklist and source registry.
2. **Compiler baseline:** build deterministic extraction validators, draft review and immutable activation using manually prepared approved templates. Demonstrate unsupported-operation refusal and correction workflow.
3. **Scheduling and medication:** generate approved occurrences, record adherence and retrieve verified product evidence. Deliver timezone/replacement tests and missing-reference fallbacks.
4. **Symptom and assistant services:** implement structured check-ins, constrained extraction, scoped retrieval and citations. Evaluate safety and leakage cases before enabling generative responses.
5. **Integrated three-role demo:** execute the shared scenario. Show the clinician approving a plan, patient receiving approved tasks, authorized caregiver seeing a limited support task and unauthorized caregiver denied. Submit ambiguous dizziness text, preserve uncertainty and provide only verified medication context.
6. **Failure and release gate:** disable the LLM during an emergency fixture, revoke caregiver access during retrieval, replay a schedule activation and show no duplicate reminders. Deliver evaluation report and signed clinical content decisions.

**Done means:** plans are reviewable and versioned, clinical changes remain clinician-controlled, reported symptoms and medication evidence carry provenance, and the assistants never acquire authority beyond their users' permissions.

## 9. Supporting primary reference

[National Library of Medicine: About DailyMed](https://dailymed.nlm.nih.gov/dailymed/about-dailymed.cfm) and [DailyMed](https://www.dailymed.nlm.nih.gov/dailymed/) describe the labeling service and its in-use labeling content. Verified 10 October 2026. Source selection must still match the actual product and jurisdiction; the source does not authorize treatment changes or replace clinician verification.

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
