import { useCallback, useEffect, useRef, useState } from 'react';
import { useAppState } from '../context/AppState';

export type ChatMessage = { role: 'user' | 'assistant'; content: string };

export type ChatReply = { reply: string; escalate: boolean };

/** Demo identities (fictional) used by the backend seed. */
export const PATIENT_ID = 'sarah';
export const CAREGIVER_ID = 'ahmed';

async function call<T>(apiUrl: string, path: string, init?: { method?: string; body?: unknown }, timeoutMs = 15000): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${apiUrl.replace(/\/$/, '')}${path}`, {
      method: init?.method ?? 'GET',
      headers: { 'Content-Type': 'application/json' },
      body: init?.body === undefined ? undefined : JSON.stringify(init.body),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
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
  pending_requests: PatientRequest[];
  open_alerts: number;
  next_step: Notification | null;
};

export type CheckinResult =
  | { status: 'urgent'; checkin_id: string; reason: string; message: string }
  | { status: 'ok'; checkin_id: string; worsened: { item: string; before: number; now: number }[]; clarification: PatientRequest | null; investigation_id: string | null };

/** Stable chip keys, in the same order as the translated chip labels on the check-in screen. */
export const WOUND_CHIP_KEYS = ['redness', 'swelling', 'warmth', 'drainage', 'bad_smell'];
export const OTHER_CHIP_KEYS = ['chills', 'fever', 'nausea', 'dizziness', 'shortness_of_breath', 'calf_pain'];

export const getToday = (apiUrl: string) => call<Today>(apiUrl, `/patients/${PATIENT_ID}/today`);

export const getRequests = (apiUrl: string) => call<PatientRequest[]>(apiUrl, `/patients/${PATIENT_ID}/requests`);

export const submitCheckin = (apiUrl: string, body: { pain: number; fatigue: number; mobility: number; chips: string[]; comment?: string }) =>
  call<CheckinResult>(apiUrl, '/checkin', { method: 'POST', body: { patient_id: PATIENT_ID, ...body } }, 30000);

export type AnswerBody = { option_index?: number; text?: string; value?: number; photo_asset?: string; photo_base64?: string };

export const answerRequest = (apiUrl: string, id: string, body: AnswerBody) =>
  call<{ status: 'answered' | 'urgent'; message?: string }>(apiUrl, `/requests/${id}/answer`, { method: 'POST', body }, 30000);

export type Twin = { vitals?: Record<string, { status: string; value: { value?: number } | null; baseline: number | null }> };

export const getTwin = (apiUrl: string) => call<Twin>(apiUrl, `/patients/${PATIENT_ID}/twin`);

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
  const { apiUrl } = useAppState();
  const [data, setData] = useState<T | null>(null);
  const [online, setOnline] = useState<boolean | null>(null);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  const refresh = useCallback(async () => {
    try {
      setData(await fnRef.current(apiUrl));
      setOnline(true);
    } catch {
      setOnline(false);
    }
  }, [apiUrl]);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, ms);
    return () => clearInterval(id);
  }, [refresh, ms]);

  return { data, online, refresh };
}
