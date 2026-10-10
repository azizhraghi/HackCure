# SurgiGuard AI

**Smarter Recovery. Safer Care.**

SurgiGuard AI is a HackCure hackathon project concept for supporting people after surgery. It brings patients, trusted caregivers, and medical professionals into one recovery workflow: **monitor → detect → investigate → escalate → act → verify → continue recovery**.

The goal is to make changes during recovery visible, explain why an alert was raised, and track whether the needed follow-up actually happened. Medical decisions stay with qualified professionals.

## The problem

Recovery continues at home, but clinical visits are intermittent. Patients can miss warning signs or struggle with medication and rehabilitation instructions; clinicians have limited visibility between appointments; caregivers may lack the information needed to help. An alert alone does not ensure someone reviewed it or completed follow-up.

## The proposed experience

| Participant | Proposed capabilities |
| --- | --- |
| Patient mobile app | Recovery timeline, daily symptom check-ins, available sensor trends, medication reminders, approved rehabilitation tasks, appointments, and requests for help. |
| Caregiver mobile space | Invitation-based access to the updates and practical tasks the patient chooses to share. A patient can use SurgiGuard without a caregiver. |
| Clinical web dashboard | Review assigned patients, measurements, symptoms, recovery trends, evidence behind alerts, proposed plans, and the status of follow-up tasks. |

### What makes the concept distinctive

- **Recovery Twin:** compares observed progress with a clinician-approved expected pathway, instead of relying only on fixed thresholds.
- **Uncertainty-aware investigation:** brings together symptoms, trends, sensor quality, missing information, and approved warning criteria; shows the evidence and uncertainty to clinicians.
- **Recovery Protocol Compiler:** proposes a structured plan from discharge documents for clinician review and approval before use.
- **Closed-loop follow-up:** tracks an alert through acknowledgment, clinical decision, updated instructions, and completion verification.
- **Collaborative recovery:** gives each participant an appropriate role and access level.

These are proposed product capabilities, not claims of clinical validation or completed implementation.

## Hackathon MVP target

The intended prototype demonstrates one fictional postoperative journey:

1. A clinician reviews and approves a recovery plan proposed from a **sample** discharge document.
2. The patient sees milestones, reminders, symptom check-ins, and available sensor measurements.
3. A caregiver sees only information shared through patient-controlled permissions.
4. A simulated change in symptoms and temperature is compared with the expected recovery pathway.
5. The dashboard presents an evidence-based alert, including measurement reliability and uncertainty.
6. A clinician acknowledges the alert, records a decision, and verifies completion of follow-up.

The source brief also proposes an ESP32 with low-cost temperature and heart-rate sensors for a live data demonstration. All patient records must be fictional, and simulated measurements must be labeled. Hobby-grade sensors are for demonstrating integration, not medical diagnosis.

## Suggested technical direction

The project brief suggests Flutter or React Native for mobile, React or Next.js for the clinician dashboard, FastAPI for the backend, PostgreSQL for storage, and ESP32-compatible sensors for IoT. These are **options to evaluate**, not an implemented stack. Authentication, role-based access, caregiver consent, encrypted communication, and audit logs are part of the proposed design.

## Safety boundary

SurgiGuard is a hackathon prototype concept. It must not independently diagnose complications, change treatment, or delay urgent clinical escalation while gathering more information. Clinicians approve recovery plans and remain responsible for clinical decisions. Medication safety checks would require trusted references and clinician verification before any real-world use.

## Project documents

- [Project brief](PROJECT.md): product scope, core workflows, MVP acceptance criteria, and open decisions.

## Current status

This repository currently contains project documentation. The application and hardware integration have not been implemented here yet.
