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

export async function getJson<T>(path: string): Promise<T> {
  const response = await api(path);
  if (!response.ok) throw new ApiError(response.status, await detail(response));
  return response.json();
}

export async function send<T>(method: "POST" | "PATCH" | "DELETE", path: string, body?: unknown): Promise<T> {
  const response = await api(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });
  if (!response.ok) throw new ApiError(response.status, await detail(response));
  return response.status === 204 ? (undefined as T) : response.json();
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function detail(response: Response): Promise<string> {
  const body = await response.json().catch(() => ({}));
  // FastAPI field errors come as a list; show the first one in plain words.
  if (Array.isArray(body.detail)) return body.detail[0]?.msg ?? "Please check the form.";
  return body.detail ?? "Something went wrong. Try again.";
}

// ---- household ----------------------------------------------------------------
export type Role = "adult" | "teen" | "child";
export type Access = "household" | "own";
export type AccountType = "checking" | "savings" | "credit_card" | "brokerage" | "retirement" | "loan";

export type Member = {
  id: number;
  name: string;
  colour: string;
  role: Role;
  access: Access;
  can_sign_in: boolean;
  is_archived: boolean;
  is_me: boolean;
  account_count: number;
};

export type Account = {
  id: number;
  name: string;
  institution: string;
  nickname: string | null;
  display_name: string;
  last4: string | null;
  type: AccountType;
  is_liability: boolean;
  currency: string;
  opening_balance_cents: number;
  opening_date: string | null;
  is_active: boolean;
  owner_ids: number[];
};

export const MEMBER_COLOURS = ["#2563EB", "#059669", "#D97706", "#DB2777", "#7C3AED", "#0891B2", "#DC2626", "#4B5563"];

export const ACCOUNT_TYPES: { id: AccountType; label: string }[] = [
  { id: "checking", label: "Checking" },
  { id: "savings", label: "Savings" },
  { id: "credit_card", label: "Credit card" },
  { id: "brokerage", label: "Brokerage" },
  { id: "retirement", label: "Retirement" },
  { id: "loan", label: "Loan" },
];
export const LIABILITY_TYPES: AccountType[] = ["credit_card", "loan"];
