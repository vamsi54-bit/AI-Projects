export interface SessionDraft {
  durationSeconds: number;
  samples: number;
  averageConfidence: number;
  dominantEmotion: string;
  distribution: Record<string, number>;
}

export interface SessionRecord extends SessionDraft {
  id: string;
  createdAt: string;
}

const STORAGE_KEY = "emora.sessions.v1";
const MAX_SESSIONS = 100;

export function getSessions(): SessionRecord[] {
  if (typeof window === "undefined") return [];
  try {
    const value: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
    return Array.isArray(value)
      ? value.filter(
          (item): item is SessionRecord =>
            typeof item === "object" && item !== null &&
            typeof (item as SessionRecord).id === "string" &&
            typeof (item as SessionRecord).createdAt === "string",
        )
      : [];
  } catch {
    return [];
  }
}

export function saveSession(session: SessionRecord) {
  const sessions = [session, ...getSessions().filter((item) => item.id !== session.id)];
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions.slice(0, MAX_SESSIONS)));
}

export async function createSession(draft: SessionDraft): Promise<SessionRecord> {
  try {
    const response = await fetch("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(draft),
    });
    if (!response.ok) throw new Error("Session API rejected the record.");
    const data = (await response.json()) as { session: SessionRecord };
    saveSession(data.session);
    return data.session;
  } catch {
    const fallback: SessionRecord = {
      ...draft,
      id: crypto.randomUUID(),
      createdAt: new Date().toISOString(),
    };
    saveSession(fallback);
    return fallback;
  }
}

export function deleteSession(id: string) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(getSessions().filter((item) => item.id !== id)));
}

export function clearSessions() {
  localStorage.removeItem(STORAGE_KEY);
}
