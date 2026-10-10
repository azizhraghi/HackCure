export type ChatMessage = { role: 'user' | 'assistant'; content: string };

export type ChatReply = { reply: string; escalate: boolean };

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

/** Calls the FastAPI proxy (backend/main.py), which holds the Mistral key. */
export async function sendChat(apiUrl: string, messages: ChatMessage[], lang: string): Promise<ChatReply> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 30000);
  try {
    const res = await fetch(`${apiUrl.replace(/\/$/, '')}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages, lang }),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as ChatReply;
  } finally {
    clearTimeout(timer);
  }
}
