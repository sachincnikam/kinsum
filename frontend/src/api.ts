// Small fetch helpers for the Kinsum API. Any "locked" (423) answer sends the app back to the lock screen.

export type LockState = "setup" | "locked" | "unlocked";
export type LockStatus = { state: LockState; idle_lock_minutes: number; retry_after_seconds: number };

let onLocked: () => void = () => {};

export function setLockedHandler(handler: () => void) {
  onLocked = handler;
}

export async function api(path: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(path, {
    ...init,
    headers: init?.body ? { "Content-Type": "application/json", ...init.headers } : init?.headers,
  });
  if (response.status === 423) onLocked();
  return response;
}

export async function getLockStatus(): Promise<LockStatus> {
  const response = await fetch("/api/lock/status");
  if (!response.ok) throw new Error(`Status check failed (${response.status})`);
  return response.json();
}

export function postJson(path: string, body: unknown): Promise<Response> {
  return api(path, { method: "POST", body: JSON.stringify(body) });
}
