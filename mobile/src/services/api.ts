export type ChatMessage = { role: 'user' | 'assistant'; content: string };

export type ChatReply = { reply: string; escalate: boolean };

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
