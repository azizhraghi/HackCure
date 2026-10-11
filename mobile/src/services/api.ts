import { useCallback, useEffect, useRef, useState } from 'react';
import { useAppState } from '../context/AppState';
import { aiRequest } from './aiIdentity';

export type ChatMessage = { role: 'user' | 'assistant'; content: string };

export type ChatReply = { reply: string; escalate: boolean };

/** Demo identities (fictional) used by the backend seed. */
export const PATIENT_ID = 'sarah';
export const CAREGIVER_ID = 'ahmed';

async function call<T>(apiUrl: string, path: string, init?: { method?: string; body?: unknown }, timeoutMs = 15000): Promise<T> {
  const scoped = await aiRequest(path, init?.body);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${apiUrl.replace(/\/$/, '')}${scoped.path}`, {
      method: init?.method ?? 'GET',
      headers: { 'Content-Type': 'application/json', ...scoped.headers },
      body: scoped.body === undefined ? undefined : JSON.stringify(scoped.body),
      signal: controller.signal,
    });
    if (!res.ok) {
      const error = await res.json().catch(() => null);
      throw new Error(typeof error?.detail === 'string' ? error.detail : `HTTP ${res.status}`);
    }
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

/** Calls the FastAPI backend, which holds the LLM keys. */
export async function sendChat(apiUrl: string, messages: ChatMessage[], lang: string): Promise<ChatReply> {
  return call<ChatReply>(apiUrl, '/chat', { method: 'POST', body: { messages, lang } }, 30000);
}

// ---------------------------------------------------------------- patient

export type PatientRequest = {
  id: string;
  kind: 'question' | 'photo' | 'measurement';
  prompt: string;
  reason: string;
  options: string[];
  metric: string | null;
  status: string;
  expires_at: string;
};

export type Notification = { id: string; kind: string; title: string; body: string; created_at: string };

export type Today = {
  patient: { id: string; name: string; first_name: string; day: number };
  appointments: { title: string; at: string }[];
  pending_requests: PatientRequest[];
  open_alerts: number;
  next_step: Notification | null;
  investigation_progress?: InvestigationProgress | null;
  wound_photo: { status: 'due' | 'completed' | 'not_due' | 'unconfigured' | 'blocked'; permitted: boolean;
    reason: string; next_window?: { starts_at: string; ends_at: string } | null };
};

export type InvestigationProgress = {
  id: string; phase: 'context' | 'evidence' | 'followup' | 'closed' | 'urgent';
  context_collected: boolean; report_ready: boolean; report_incomplete: boolean;
  followup_state: string | null; closed: boolean;
};

export type CheckinResult =
  | { status: 'urgent'; checkin_id: string; reason: string; message: string }
  | { status: 'ok'; checkin_id: string; worsened: { item: string; before: number; now: number }[]; clarification: PatientRequest | null; investigation_id: string | null };

/** Stable chip keys, in the same order as the translated chip labels on the check-in screen. */
export const WOUND_CHIP_KEYS = ['redness', 'swelling', 'warmth', 'drainage', 'bad_smell'];
export const OTHER_CHIP_KEYS = ['chills', 'fever', 'nausea', 'dizziness', 'shortness_of_breath', 'calf_pain'];

export const getToday = (apiUrl: string) => call<Today>(apiUrl, `/patients/${PATIENT_ID}/today`);

export const getRequests = (apiUrl: string) => call<PatientRequest[]>(apiUrl, `/patients/${PATIENT_ID}/requests`);

export type Mood = 'very_good' | 'good' | 'okay' | 'unwell' | 'very_unwell';
export type NeuroAnswer = 'normal' | 'different' | 'skipped';

export const submitCheckin = (apiUrl: string, body: { pain: number; fatigue: number; mobility: number; chips: string[]; comment?: string; mood?: Mood; neuro?: Record<string, NeuroAnswer>; rehab_done?: string[] }) =>
  call<CheckinResult>(apiUrl, '/checkin', { method: 'POST', body: { patient_id: PATIENT_ID, ...body } }, 30000);

export type AnswerBody = { option_index?: number; text?: string; value?: number; photo_asset?: string; photo_base64?: string; dressing_change_confirmed?: boolean };

export const answerRequest = (apiUrl: string, id: string, body: AnswerBody) =>
  call<{ status: 'answered' | 'urgent'; message?: string }>(apiUrl, `/requests/${id}/answer`, { method: 'POST', body }, 30000);

export type Twin = { vitals?: Record<string, { status: string; value: { value?: number } | null; baseline: number | null }> };

export const getTwin = (apiUrl: string) => call<Twin>(apiUrl, `/patients/${PATIENT_ID}/twin`);

// ---------------------------------------------------------------- wound photos (measured by code on the server)

export type WoundComparison = {
  available: boolean; reason?: string; trend?: 'up' | 'down' | 'stable'; summary?: string;
  redness_area_ref_pct?: number; redness_area_now_pct?: number; redness_area_change_pct?: number | null;
};
export type WoundPhoto = {
  observation_id: string; at: string; url: string; label: string; simulated: boolean; quality: string;
  analysis?: { quality: string; problems?: string[]; redness_area_pct?: number };
  comparison?: WoundComparison; reference_url?: string | null; answered_request_id?: string | null;
};

export const getWoundPhotos = (apiUrl: string) =>
  call<{ reference: WoundPhoto | null; photos: WoundPhoto[] }>(apiUrl, `/patients/${PATIENT_ID}/wound-photos`);

/** Uploads a wound photo (a camera file URI on the phone, a Blob in the browser). Only accepted inside a dressing
 * change permitted by the care plan, confirmed by the patient; it answers that window's photo request. */
export async function uploadWoundPhoto(apiUrl: string, file: string | Blob, dressingChangeConfirmed: boolean): Promise<WoundPhoto> {
  const form = new FormData();
  if (typeof file === 'string') form.append('file', { uri: file, type: 'image/jpeg', name: 'wound.jpg' } as unknown as Blob);
  else form.append('file', file); // a browser File keeps its own name
  form.append('dressing_change_confirmed', dressingChangeConfirmed ? 'true' : 'false');
  return postForm<WoundPhoto>(apiUrl, `/patients/${PATIENT_ID}/wound-photos`, form, 60000);
}

async function postForm<T>(apiUrl: string, path: string, form: FormData, timeoutMs: number): Promise<T> {
  const scoped = await aiRequest(path);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${apiUrl.replace(/\/$/, '')}${scoped.path}`, { method: 'POST', headers: scoped.headers, body: form, signal: controller.signal });
    if (!res.ok) {
      const error = await res.json().catch(() => null);
      throw new Error(typeof error?.detail === 'string' ? error.detail : `HTTP ${res.status}`);
    }
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

// ---------------------------------------------------------------- documents -> care plan (Developer 2 compiler)

export type UploadedDocument = { id: string; filename: string; status: 'ready' | 'unreadable'; error: string | null; size: number; chars: number };
export type DraftWarning = { level: 'high' | 'medium' | 'low'; item: string; message: string };
export type PlanMedication = { id: string; name: string; dose: string; route: string; purpose: string; times: string[]; as_needed: boolean; duration_days: number | null; times_inferred: boolean };
export type PlanDraft = {
  id: string; status: 'analyzing' | 'ready' | 'failed' | 'confirmed'; mode: string; error: string | null; warnings: DraftWarning[];
  clarifications?: { id: string; question: string; reason: string; sources: { document_id: string; filename: string }[]; status: string }[];
  plan: null | {
    pathway: string; medications: PlanMedication[]; rehab: { name: string; times: string[] }[];
    appointments: { title: string; day_offset?: number; time: string; date?: string }[];
    document_info?: { surgery: string; side: string; surgery_date: string | null; surgeon: string; allergies: string[]; activity_restrictions: string[]; warning_signs: string[] };
    clinical_profile?: Record<string, unknown>;
  };
};

export const getDocuments = (apiUrl: string) => call<UploadedDocument[]>(apiUrl, `/patients/${PATIENT_ID}/documents`);

export const addSampleDocument = (apiUrl: string) =>
  call<UploadedDocument>(apiUrl, `/patients/${PATIENT_ID}/documents/sample`, { method: 'POST' });

/** One document from the phone (file URI + name + type) or the browser (File). */
export function uploadDocument(apiUrl: string, file: { uri: string; name: string; type: string } | File) {
  const form = new FormData();
  form.append('files', file as unknown as Blob);
  return postForm<UploadedDocument[]>(apiUrl, `/patients/${PATIENT_ID}/documents`, form, 60000);
}

export const startPlanDraft = (apiUrl: string, documentIds: string[] = []) =>
  call<PlanDraft>(apiUrl, `/patients/${PATIENT_ID}/plan-drafts`, { method: 'POST', body: { document_ids: documentIds, engine: 'd2' } }, 30000);

export const getPlanDraft = (apiUrl: string, id: string) => call<PlanDraft>(apiUrl, `/plan-drafts/${id}`);

export const confirmPlanDraft = (apiUrl: string, id: string) =>
  call<{ ok: boolean; plan_id: string }>(apiUrl, `/plan-drafts/${id}/confirm`, { method: 'POST', body: { actor: PATIENT_ID } });

export const requestPlanClarification = (apiUrl: string, id: string) =>
  call<{ status: string; delivery: string; notification_ids: string[] }>(apiUrl, `/plan-drafts/${id}/clarification-request`, { method: 'POST', body: { actor: PATIENT_ID } });

export type MedicationPhoto = { url: string; at: string; note: string };
export type ScheduledDose = { med_id: string; name: string; dose: string; purpose: string; scheduled_for: string;
  status: 'taken' | 'not_taken' | 'postponed' | 'unknown' | 'due' | 'upcoming'; photo: MedicationPhoto | null };
export const getMedications = (apiUrl: string) => call<{ today: ScheduledDose[]; now: string; plan: PlanMedication[] }>(apiUrl, `/patients/${PATIENT_ID}/medications`);
export const recordDose = (apiUrl: string, dose: ScheduledDose, status: 'taken' | 'not_taken' | 'postponed') =>
  call<{ status: string; missed_dose_text?: string }>(apiUrl, '/medications/dose', { method: 'POST', body: {
    patient_id: PATIENT_ID, actor: PATIENT_ID, med_id: dose.med_id, scheduled_for: dose.scheduled_for, status,
  } });
export const uploadMedicationPhoto = (apiUrl: string, medId: string, file: File) => {
  const form = new FormData(); form.append('file', file);
  return postForm<MedicationPhoto>(apiUrl, `/patients/${PATIENT_ID}/medications/${medId}/photo`, form, 30000);
};
export type FollowupTask = { id: string; instruction: string; due_at: string; status: string; evidence_types: string[]; observation_ids: string[] };
export const getFollowupTasks = (apiUrl: string) => call<FollowupTask[]>(apiUrl, `/patients/${PATIENT_ID}/followup-tasks`);
export type SharedMember = { id: string; name: string; relation: string; categories: Record<string, boolean> };
export const getSharing = (apiUrl: string) => call<SharedMember[]>(apiUrl, `/patients/${PATIENT_ID}/sharing`);
export const updateSharing = (apiUrl: string, member: SharedMember, category: string) => call(apiUrl,
  `/patients/${PATIENT_ID}/sharing/${member.id}`, { method: 'PUT', body: { categories: { ...member.categories, [category]: !member.categories[category] } } });

// ---------------------------------------------------------------- Developer 1: expected recovery + Patient Twin

export type ExpectedRecovery =
  | { status: 'ready'; card: null | { day: number; surgery: string; message: string; normal_today: string[]; normal_pain: { low: number; high: number }; today: string[] }; note: string }
  | { status: 'computing'; since: string }
  | { status: 'unavailable' | 'failed' | 'not_started' | 'unknown_patient'; reason?: string; error?: string };

export const getExpectedRecovery = (apiUrl: string) => call<ExpectedRecovery>(apiUrl, `/patients/${PATIENT_ID}/expected-recovery`);

// ---------------------------------------------------------------- caregiver

export type CaregiverTask = { id: string; text: string; category: string; status: string };
export type Digest = { digest: { text: string; created_at: string }; tasks: CaregiverTask[] };
export type AlertSummary = { id: string; level: 'info' | 'attention' | 'urgent'; state: string; title: string; created_at: string };

export const getDigest = (apiUrl: string, refresh = false) =>
  call<Digest>(apiUrl, `/caregiver/${CAREGIVER_ID}/digest${refresh ? '?refresh=true' : ''}`, undefined, 30000);

export const getCaregiverTasks = (apiUrl: string) => call<CaregiverTask[]>(apiUrl, `/caregiver/${CAREGIVER_ID}/tasks`);

export const markTaskDone = (apiUrl: string, id: string) =>
  call<CaregiverTask>(apiUrl, `/caregiver/tasks/${id}/done`, { method: 'POST', body: { actor: CAREGIVER_ID } });

export const getCaregiverAlerts = (apiUrl: string) =>
  call<AlertSummary[]>(apiUrl, `/alerts?role=caregiver&member_id=${CAREGIVER_ID}&open_only=true`);

// ---------------------------------------------------------------- polling hook

/** Polls `fn` every `ms` while mounted. `data` stays null (=> screens keep their mock content) if the backend is unreachable. */
export function usePoll<T>(fn: (apiUrl: string) => Promise<T>, ms = 4000) {
  const { apiUrl, session, demo } = useAppState();
  const [data, setData] = useState<T | null>(null);
  const [online, setOnline] = useState<boolean | null>(null);
  const fnRef = useRef(fn);
  const dataIdentity = useRef('');
  const identityKey = `${apiUrl}:${session?.user.id ?? ''}:${demo}`;
  const identityRef = useRef(identityKey);
  identityRef.current = identityKey;
  fnRef.current = fn;

  const refresh = useCallback(async () => {
    const requestedIdentity = identityKey;
    try {
      const result = await fnRef.current(apiUrl);
      if (identityRef.current !== requestedIdentity) return;
      dataIdentity.current = requestedIdentity;
      setData(result);
      setOnline(true);
    } catch {
      if (identityRef.current !== requestedIdentity) return;
      setData(null);
      setOnline(false);
    }
  }, [apiUrl, session?.token, demo, identityKey]);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, ms);
    return () => clearInterval(id);
  }, [refresh, ms]);

  return { data: dataIdentity.current === identityKey ? data : null, online, refresh };
}

export type DemoEventResponse = {
  event_id: string;
  episode_id: string;
  alert_id: string | null;
  followup_id: string | null;
  safety_decision: {
    decision_id: string;
    outcome: 'emergency' | 'clinical_review' | 'no_match' | 'indeterminate';
    policy_version: string;
    matched_rule_ids: string[];
    instruction: string | null;
    limitations: string[];
  };
};

export type DemoInvestigation = {
  investigation_id: string;
  state: 'complete' | 'partial' | 'failed';
  findings: { statement: string; evidence_ids: string[]; limitations: string[] }[];
  evidence: { evidence_id: string; kind: string }[];
  missing_data: string[];
  uncertainty: string[];
};

export type DemoFollowup = {
  followup_id: string;
  stage: string;
  version: number;
  acknowledged_by: string | null;
  clinician_decision_id: string | null;
  verification_evidence_id: string | null;
};

const DEMO_EPISODE = 'ep_demo_001';

async function demoRequest<T>(apiUrl: string, path: string, method: 'GET' | 'POST', body?: object): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/demo${path}`, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return (await response.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

/** Synthetic warning fixture, separate from the patient's actual check-in answers. */
export function createDemoSafetyEvent(apiUrl: string): Promise<DemoEventResponse> {
  return demoRequest(apiUrl, `/episodes/${DEMO_EPISODE}/events`, 'POST', {
    event_id: `ev_mobile_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    patient_id: 'pt_demo_001',
    kind: 'structured_warning',
    code: 'demo_urgent_warning',
    answer: 'yes',
    quality: 'unknown',
    source: 'patient',
    occurred_at: new Date().toISOString(),
  });
}

export function createDemoInvestigation(apiUrl: string, eventId: string): Promise<DemoInvestigation> {
  return demoRequest(apiUrl, `/episodes/${DEMO_EPISODE}/investigations?event_id=${encodeURIComponent(eventId)}`, 'POST');
}

export function getDemoFollowup(apiUrl: string, followupId: string): Promise<DemoFollowup> {
  return demoRequest(apiUrl, `/followups/${encodeURIComponent(followupId)}`, 'GET');
}

export function acknowledgeDemoFollowup(apiUrl: string, followupId: string, version: number): Promise<DemoFollowup> {
  return demoRequest(apiUrl, `/followups/${encodeURIComponent(followupId)}/acknowledgements`, 'POST', {
    actor_id: 'pt_demo_001', expected_version: version,
  });
}

// ---------------------------------------------------------------- medicines: what you may notice today

export type MedicationGuide = {
  items: { medication: string; times: string[]; known: boolean; common: string[]; call_if: string[] }[];
  reassurance: string; note: string; source: string;
};

export const getMedicationGuide = (apiUrl: string, lang: string) =>
  call<MedicationGuide>(apiUrl, `/patients/${PATIENT_ID}/medication-guide?lang=${lang}`);

// ---------------------------------------------------------------- Developer 1: rehab exercises + guided movement tests

export type RehabExercise = {
  exercise_id: string; name: string; category: string; target_side: string; target_reps: number; target_sets: number;
  target_rom_deg: number | null; min_hold_duration_sec: number; precautions: string[]; forbidden_movements: string[];
};
export type RehabPlan = { postop_day: number; daily_sessions: number; exercises: RehabExercise[]; general_guardrails: string[] };

export const getRehabPlan = (apiUrl: string) => call<RehabPlan>(apiUrl, `/patients/${PATIENT_ID}/rehab/plan`);

export type MotorTestInfo = { id: string; name: string; instructions: string; seconds: number; demo_variants: string[] };
export type MotorTests = { consent: boolean; blocked: string | null; tests: MotorTestInfo[]; note: string };
export type MotorMeasurement = { code: string; value: number | null; unit: string; side: 'left' | 'right' | 'both' | null };
export type MotorOutcome = {
  result: { test: string; status: 'complete' | 'limited' | 'not_interpretable'; measurements: MotorMeasurement[];
    observations: string[]; review_suggested: boolean; limitations: string[] };
  changes_since_previous: { code: string; side: string | null; previous: number; current: number; change: number }[];
  compared_with_previous: boolean; alert_id: string | null; note: string; synthetic: boolean;
};

export const getMotorTests = (apiUrl: string) => call<MotorTests>(apiUrl, `/patients/${PATIENT_ID}/motor/tests`);

export const setMotorConsent = (apiUrl: string, granted: boolean) =>
  call<{ consent: boolean }>(apiUrl, `/patients/${PATIENT_ID}/motor/consent`, { method: 'POST', body: { granted } });

/** frames from the on-device capture, or `demo` = a named sample recording (clearly synthetic). */
export const runMotorTest = (apiUrl: string, test: string, body: { frames?: object[]; demo?: string }) =>
  call<MotorOutcome>(apiUrl, `/patients/${PATIENT_ID}/motor/${test}`, { method: 'POST', body }, 60000);
