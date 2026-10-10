# SurgiGuard AI — project brief

## Vision

SurgiGuard AI is a proposed postoperative recovery and care coordination platform for the HackCure healthcare hackathon. It links the patient at home, an optional trusted caregiver, and the clinical team. Its central idea is **evidence-to-action recovery intelligence**: connect observations to accountable follow-up rather than stopping at data collection or alert delivery.

This document distills the supplied project concept into a buildable hackathon brief. The features below describe intended behavior, not completed software or clinically validated performance.

## Users and responsibilities

### Patient

- Reviews a clinician-approved recovery timeline, objectives, milestones, and appointments.
- Records daily symptoms such as pain, fatigue, wound concerns, and mobility difficulties.
- Sees available heart-rate, temperature, and activity trends where supported.
- Receives approved medication and rehabilitation reminders and can request help.
- Chooses what an invited caregiver can see.

### Trusted caregiver

- Uses a separate account linked by invitation.
- Sees only authorized updates, appointments, reminders, and assistance requests.
- Helps with practical tasks and can report observed difficulties.
- Does not make medical decisions. The product must work without a caregiver.

### Medical professional

- Reviews assigned patients and their postoperative context.
- Checks measurements, symptom reports, trajectory comparisons, and alert evidence.
- Approves or edits proposed recovery plans before activation.
- Acknowledges alerts, records decisions, sends updated instructions, and verifies follow-up.

## Core workflow

```text
Monitor → Detect → Investigate → Escalate → Act → Verify → Continue recovery
```

An abnormal observation is evaluated alongside recent trends, patient reports, sensor quality, the approved plan, and missing or conflicting information. If approved escalation criteria are met, the clinical team receives an explainable alert. The alert is a starting point: its acknowledgment, clinical decision, communication to the patient, and completed follow-up are tracked separately.

## Proposed components

### Recovery Twin

A patient-specific view of expected recovery based on surgery type, time since surgery, relevant history, clinician-approved milestones, symptoms, measurements, mobility, and adherence. It compares expected and observed progress. For the MVP, approved example pathways, transparent rules or simple statistical models, and fictional scenarios are sufficient; a predictive clinical model is not required.

### Uncertainty-aware investigation

An alert summary shows the measurements and symptoms involved, recent history, possible sensor errors, missing data, and the approved criterion that triggered escalation. It expresses uncertainty instead of presenting a diagnosis. Collecting extra information must never delay an urgent escalation.

### Recovery Protocol Compiler

The clinician uploads a sample discharge report or prescription. The system proposes structured monitoring, medication reminders, check-ins, rehabilitation tasks, milestones, appointments, and warning signs. Nothing becomes an active patient plan until a clinician reviews and approves it.

### Closed-loop follow-up

Track distinct states: **observation → alert sent → acknowledged → clinical decision recorded → instructions delivered → follow-up verified**. Each transition should have an owner and timestamp in the prototype so the demo can show where care is pending.

## Hackathon MVP: demonstrable outcomes

| Outcome | Demo acceptance criterion |
| --- | --- |
| Patient experience | Display an approved plan, daily check-in, measurements, and recovery milestones for a fictional patient. |
| Caregiver experience | Show a separate invited account with limited, patient-authorized information. |
| Clinician experience | Show a dashboard with the same patient's trend, plan, and alert state. |
| IoT integration | Transmit and display live ESP32 sensor data if hardware is available; distinguish it from simulated values. |
| Plan compilation | Extract a draft plan from a sample document and require clinician approval before activation. |
| Recovery comparison | Visualize expected versus observed progress for the demo patient. |
| Investigation | Explain a simulated concerning change using symptoms, trend, sensor quality, and uncertainty. |
| Follow-up | Show alert notification, acknowledgment, recorded action, and verified completion as separate steps. |

### Suggested demo story

1. **Discharge:** a clinician uploads a fictional discharge document and approves the proposed plan.
2. **Home recovery:** the patient reviews tasks; a caregiver sees only permitted information.
3. **New concern:** the patient reports worsening pain and fatigue, and a simulated temperature rises.
4. **Review:** the dashboard compares the change with the expected pathway and shows an alert with evidence and uncertainty.
5. **Follow-up:** the clinician acknowledges the alert, records instructions, and marks follow-up complete after verification.

## Suggested architecture, pending team choice

- **Mobile:** Flutter or React Native.
- **Clinical dashboard:** React or Next.js.
- **API:** Python and FastAPI.
- **Data:** PostgreSQL.
- **AI assistance:** document extraction, retrieval from verified references, trajectory comparison, reliability checks, and structured escalation rules.
- **IoT:** ESP32 with compatible temperature and heart-rate sensors; movement sensing is optional.
- **Security design:** authentication, role-based authorization, patient-controlled caregiver permissions, encrypted communication, and audit logs.

The team should choose one concrete stack before implementation. For the hackathon, an auditable rule-based escalation path and a narrow, reviewed demo scenario are preferable to unsupported clinical claims.

## Safety and data requirements

- Use fictional patient records and sample clinical documents in the demonstration.
- Clearly label simulated measurements and keep hobby-grade sensor output separate from clinical evidence.
- Keep clinicians responsible for plan approval, alert assessment, and medical decisions.
- Do not let AI independently diagnose, prescribe, or postpone urgent escalation.
- Limit caregiver access to patient-authorized information and record important workflow actions.
- Treat any medication interaction, duplication, or allergy screening as unvalidated until it uses trusted references and clinician review.

## Open decisions for the team

1. Which surgery and recovery pathway will the first demo cover?
2. Which mobile, dashboard, API, and database options will the team implement?
3. Which sensors are actually available and reliable enough for a technical demo?
4. What sample discharge document and approved escalation rules will be used?
5. How will the team demonstrate notification and follow-up verification end to end?

## Later possibilities

Validated prediction models, hospital record integration, broader surgery coverage, rehabilitation analytics, multilingual support, and assistive communication are longer-term ideas. They are outside the initial hackathon MVP.
