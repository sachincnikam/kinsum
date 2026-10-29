import { useCallback, useEffect, useId, useState, type FormEvent, type ReactNode } from "react";
import {
  ACCOUNT_TYPES,
  LIABILITY_TYPES,
  MEMBER_COLOURS,
  getJson,
  send,
  type Access,
  type Account,
  type AccountType,
  type Member,
  type Role,
} from "../api";
import { Modal, inputClass, primaryButton, secondaryButton } from "../components/Modal";
import { centsToInput, formatCents, parseDollars } from "../lib/money";

const ROLE_LABEL: Record<Role, string> = { adult: "Adult", teen: "Teen", child: "Child" };
const ACCESS_LABEL: Record<Access, string> = { household: "Whole household", own: "Own and shared accounts" };
const TYPE_LABEL = Object.fromEntries(ACCOUNT_TYPES.map((t) => [t.id, t.label])) as Record<AccountType, string>;

type Dialog =
  | { kind: "member"; member?: Member }
  | { kind: "sign-in"; member: Member }
  | { kind: "account"; account?: Account }
  | null;

export function Household({ me }: { me: Member }) {
  const [members, setMembers] = useState<Member[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [showArchived, setShowArchived] = useState(false);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [error, setError] = useState("");
  const manager = me.access === "household";

  const load = useCallback(async () => {
    try {
      const q = showArchived ? "?include_archived=true" : "";
      const [m, a] = await Promise.all([
        getJson<Member[]>(`/api/members${q}`),
        getJson<Account[]>(`/api/accounts${q}`),
      ]);
      setMembers(m);
      setAccounts(a);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }, [showArchived]);

  useEffect(() => {
    load();
  }, [load]);

  async function act(action: () => Promise<unknown>) {
    try {
      await action();
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const close = () => setDialog(null);
  const saved = async () => {
    setDialog(null);
    await load();
  };

  return (
    <div className="flex max-w-5xl flex-col gap-6">
      {error && (
        <p role="alert" className="m-0 rounded-lg border border-over/30 bg-surface px-4 py-3 text-sm text-over">
          {error}
        </p>
      )}

      <section aria-labelledby="members-heading" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="members-heading" className="m-0 text-lg font-semibold">
            Members
          </h2>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-muted">
              <input
                type="checkbox"
                checked={showArchived}
                onChange={(e) => setShowArchived(e.target.checked)}
                className="h-4 w-4 accent-primary"
              />
              Show archived
            </label>
            {manager && (
              <button type="button" className={primaryButton} onClick={() => setDialog({ kind: "member" })}>
                Add member
              </button>
            )}
          </div>
        </div>
        <ul className="m-0 grid list-none gap-3 p-0 sm:grid-cols-2 lg:grid-cols-3">
          {members.map((m) => (
            <li
              key={m.id}
              className={
                "flex flex-col gap-3 rounded-xl border border-border bg-surface p-4 " + (m.is_archived ? "opacity-70" : "")
              }
            >
              <div className="flex items-center gap-3">
                <Avatar member={m} />
                <div className="flex min-w-0 flex-col">
                  <span className="truncate font-semibold">
                    {m.name}
                    {m.is_me && <span className="font-normal text-muted"> (you)</span>}
                  </span>
                  <span className="text-[13px] text-muted">
                    {ROLE_LABEL[m.role]}
                    {m.is_archived && " · Archived"}
                  </span>
                </div>
              </div>
              <dl className="m-0 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[13px]">
                <dt className="text-muted">Sign-in</dt>
                <dd className="m-0">{m.can_sign_in ? "Own passcode" : "Does not sign in"}</dd>
                {m.can_sign_in && (
                  <>
                    <dt className="text-muted">Sees</dt>
                    <dd className="m-0">{ACCESS_LABEL[m.access]}</dd>
                  </>
                )}
                <dt className="text-muted">Accounts</dt>
                <dd className="amount m-0">{m.account_count}</dd>
              </dl>
              {manager && (
                <div className="mt-auto flex flex-wrap gap-2">
                  {m.is_archived ? (
                    <button
                      type="button"
                      className={secondaryButton}
                      onClick={() => act(() => send("PATCH", `/api/members/${m.id}`, { is_archived: false }))}
                    >
                      Restore
                    </button>
                  ) : (
                    <>
                      <button type="button" className={secondaryButton} onClick={() => setDialog({ kind: "member", member: m })}>
                        Edit
                      </button>
                      {m.role === "adult" && !m.can_sign_in && (
                        <button type="button" className={secondaryButton} onClick={() => setDialog({ kind: "sign-in", member: m })}>
                          Set up sign-in
                        </button>
                      )}
                      {m.can_sign_in && !m.is_me && (
                        <button
                          type="button"
                          className={secondaryButton}
                          onClick={() =>
                            confirm(`Remove ${m.name}'s passcode? They will no longer be able to open Kinsum.`) &&
                            act(() => send("DELETE", `/api/members/${m.id}/sign-in`))
                          }
                        >
                          Remove sign-in
                        </button>
                      )}
                      {!m.is_me && (
                        <button
                          type="button"
                          className={secondaryButton}
                          onClick={() =>
                            confirm(`Archive ${m.name}? Their history stays, and you can restore them later.`) &&
                            act(() => send("PATCH", `/api/members/${m.id}`, { is_archived: true }))
                          }
                        >
                          Archive
                        </button>
                      )}
                    </>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="accounts-heading" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="accounts-heading" className="m-0 text-lg font-semibold">
            Accounts
          </h2>
          <button type="button" className={primaryButton} onClick={() => setDialog({ kind: "account" })}>
            Add account
          </button>
        </div>
        {accounts.length === 0 ? (
          <p className="m-0 rounded-xl border border-dashed border-border bg-surface p-6 text-sm text-muted">
            No accounts yet. Add each bank account, credit card and investment account you'll import statements for.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-border bg-surface">
            <table className="w-full min-w-[640px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-border text-left text-[12px] uppercase tracking-wider text-muted">
                  <th scope="col" className="px-4 py-2.5 font-semibold">Account</th>
                  <th scope="col" className="px-4 py-2.5 font-semibold">Type</th>
                  <th scope="col" className="px-4 py-2.5 font-semibold">Owners</th>
                  <th scope="col" className="px-4 py-2.5 text-right font-semibold">Opening balance</th>
                  <th scope="col" className="px-4 py-2.5"><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((a) => (
                  <tr key={a.id} className={"border-b border-border last:border-0 " + (a.is_active ? "" : "opacity-70")}>
                    <td className="px-4 py-3">
                      <div className="font-medium">
                        {a.display_name}
                        {!a.is_active && <span className="font-normal text-muted"> · Archived</span>}
                      </div>
                      <div className="text-[13px] text-muted">
                        {a.institution} · {a.name}
                        {a.last4 && <span className="amount"> ··{a.last4}</span>}
                      </div>
                    </td>
                    <td className="px-4 py-3">{TYPE_LABEL[a.type]}</td>
                    <td className="px-4 py-3">
                      <Owners ids={a.owner_ids} members={members} />
                    </td>
                    <td className="amount px-4 py-3 text-right">
                      {a.is_liability ? (
                        <>
                          {formatCents(-a.opening_balance_cents)} <span className="text-[12px] text-muted">owed</span>
                        </>
                      ) : (
                        formatCents(a.opening_balance_cents)
                      )}
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <button
                        type="button"
                        className={secondaryButton}
                        onClick={() => setDialog({ kind: "account", account: a })}
                        aria-label={`Edit ${a.display_name}`}
                      >
                        Edit
                      </button>{" "}
                      <button
                        type="button"
                        className={secondaryButton}
                        onClick={() => act(() => send("PATCH", `/api/accounts/${a.id}`, { is_active: !a.is_active }))}
                        aria-label={`${a.is_active ? "Archive" : "Restore"} ${a.display_name}`}
                      >
                        {a.is_active ? "Archive" : "Restore"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {dialog?.kind === "member" && <MemberDialog member={dialog.member} onClose={close} onSaved={saved} />}
      {dialog?.kind === "sign-in" && <SignInDialog member={dialog.member} onClose={close} onSaved={saved} />}
      {dialog?.kind === "account" && (
        <AccountDialog account={dialog.account} me={me} members={members} onClose={close} onSaved={saved} />
      )}
    </div>
  );
}

function Avatar({ member }: { member: Member }) {
  return (
    <span
      aria-hidden="true"
      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-base font-semibold text-white"
      style={{ background: member.colour }}
    >
      {member.name.trim().charAt(0).toUpperCase()}
    </span>
  );
}

function Owners({ ids, members }: { ids: number[]; members: Member[] }) {
  return (
    <span className="flex flex-wrap items-center gap-1.5">
      {ids.map((id) => {
        const m = members.find((x) => x.id === id);
        return (
          <span key={id} className="inline-flex items-center gap-1.5 rounded-full bg-page px-2 py-0.5 text-[13px]">
            <span aria-hidden="true" className="h-2 w-2 rounded-full" style={{ background: m?.colour ?? "#94A3B8" }} />
            {m?.name ?? "Archived member"}
          </span>
        );
      })}
      {ids.length > 1 && <span className="text-[12px] text-muted">Shared</span>}
    </span>
  );
}

// ---- dialogs --------------------------------------------------------------------
type DialogProps = { onClose: () => void; onSaved: () => void };

function FormError({ id, message }: { id: string; message: string }) {
  if (!message) return null;
  return (
    <p id={id} role="alert" className="m-0 text-[13px] font-medium text-over">
      {message}
    </p>
  );
}

function Buttons({ busy, label, onClose }: { busy: boolean; label: string; onClose: () => void }) {
  return (
    <div className="flex justify-end gap-2 pt-1">
      <button type="button" className={secondaryButton} onClick={onClose}>
        Cancel
      </button>
      <button type="submit" className={primaryButton} disabled={busy}>
        {busy ? "Saving…" : label}
      </button>
    </div>
  );
}

function useSubmit(onSaved: () => void) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function run(e: FormEvent, action: () => Promise<unknown>) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await action();
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return { busy, error, setError, run };
}

function MemberDialog({ member, onClose, onSaved }: DialogProps & { member?: Member }) {
  const [name, setName] = useState(member?.name ?? "");
  const [role, setRole] = useState<Role>(member?.role ?? "adult");
  const [access, setAccess] = useState<Access>(member?.access ?? "household");
  const [colour, setColour] = useState<string | null>(member?.colour ?? null);
  const { busy, error, run } = useSubmit(onSaved);
  const ids = { name: useId(), error: useId() };

  const save = (e: FormEvent) =>
    run(e, () => {
      const body = { name, role, access, ...(colour ? { colour } : {}) };
      return member ? send("PATCH", `/api/members/${member.id}`, body) : send("POST", "/api/members", body);
    });

  return (
    <Modal title={member ? `Edit ${member.name}` : "Add a family member"} onClose={onClose}>
      <form onSubmit={save} className="flex flex-col gap-4" aria-describedby={error ? ids.error : undefined}>
        <label htmlFor={ids.name} className="flex flex-col gap-1.5 text-sm font-medium">
          Name
          <input id={ids.name} required maxLength={60} value={name} onChange={(e) => setName(e.target.value)} className={inputClass} autoFocus />
        </label>
        <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
          <legend className="mb-1.5 p-0 text-sm font-medium">Role</legend>
          <div className="flex flex-wrap gap-2">
            {(Object.keys(ROLE_LABEL) as Role[]).map((r) => (
              <Choice key={r} name="role" checked={role === r} onChange={() => setRole(r)} disabled={member?.can_sign_in && r !== "adult"}>
                {ROLE_LABEL[r]}
              </Choice>
            ))}
          </div>
          {member?.can_sign_in && <span className="text-[13px] text-muted">Only adults sign in, so remove their sign-in to change the role.</span>}
        </fieldset>
        {role === "adult" && (
          <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
            <legend className="mb-1.5 p-0 text-sm font-medium">When they sign in, they see</legend>
            {(Object.keys(ACCESS_LABEL) as Access[]).map((a) => (
              <Choice key={a} name="access" checked={access === a} onChange={() => setAccess(a)}>
                {ACCESS_LABEL[a]}
                <span className="block text-[13px] font-normal text-muted">
                  {a === "household"
                    ? "Every account, and can change members, sign-ins and the recovery key."
                    : "Only accounts they own, alone or shared with others."}
                </span>
              </Choice>
            ))}
          </fieldset>
        )}
        <fieldset className="m-0 border-0 p-0">
          <legend className="mb-1.5 p-0 text-sm font-medium">Colour</legend>
          <div className="flex flex-wrap gap-2">
            {MEMBER_COLOURS.map((c, i) => (
              <label key={c} className="cursor-pointer">
                <input type="radio" name="colour" className="peer sr-only" checked={colour === c} onChange={() => setColour(c)} />
                <span className="sr-only">Colour {i + 1}</span>
                <span
                  aria-hidden="true"
                  className="block h-8 w-8 rounded-full ring-offset-2 peer-checked:ring-2 peer-checked:ring-ink peer-focus-visible:outline-2 peer-focus-visible:outline-primary"
                  style={{ background: c }}
                />
              </label>
            ))}
          </div>
          {!member && !colour && <span className="mt-1.5 block text-[13px] text-muted">Leave unpicked to get an unused colour.</span>}
        </fieldset>
        <FormError id={ids.error} message={error} />
        <Buttons busy={busy} label={member ? "Save" : "Add member"} onClose={onClose} />
      </form>
    </Modal>
  );
}

function Choice({
  name,
  checked,
  onChange,
  disabled,
  children,
}: {
  name: string;
  checked: boolean;
  onChange: () => void;
  disabled?: boolean;
  children: ReactNode;
}) {
  return (
    <label
      className={
        "flex cursor-pointer items-start gap-2.5 rounded-lg border px-3 py-2.5 text-sm font-medium " +
        (checked ? "border-primary bg-primary-soft" : "border-border") +
        (disabled ? " cursor-not-allowed opacity-50" : "")
      }
    >
      <input type="radio" name={name} checked={checked} onChange={onChange} disabled={disabled} className="mt-0.5 h-4 w-4 accent-primary" />
      <span>{children}</span>
    </label>
  );
}

function SignInDialog({ member, onClose, onSaved }: DialogProps & { member: Member }) {
  const [passcode, setPasscode] = useState("");
  const [confirm, setConfirm] = useState("");
  const { busy, error, setError, run } = useSubmit(onSaved);
  const ids = { passcode: useId(), confirm: useId(), error: useId() };

  const save = (e: FormEvent) => {
    if (passcode !== confirm) {
      e.preventDefault();
      return setError("The two passcodes do not match.");
    }
    return run(e, () => send("POST", `/api/members/${member.id}/sign-in`, { passcode }));
  };

  return (
    <Modal title={`Set up sign-in for ${member.name}`} onClose={onClose}>
      <p className="m-0 text-sm leading-relaxed text-muted">
        Hand the laptop to {member.name} so they can type their own passcode, at least 6 characters. It must be different
        from everyone else's: the passcode is how Kinsum knows who is signing in.
      </p>
      <form onSubmit={save} className="flex flex-col gap-4" aria-describedby={error ? ids.error : undefined}>
        <label htmlFor={ids.passcode} className="flex flex-col gap-1.5 text-sm font-medium">
          {member.name}'s passcode
          <input id={ids.passcode} type="password" autoComplete="new-password" required minLength={6} value={passcode}
            onChange={(e) => setPasscode(e.target.value)} className={inputClass} autoFocus />
        </label>
        <label htmlFor={ids.confirm} className="flex flex-col gap-1.5 text-sm font-medium">
          Type it again
          <input id={ids.confirm} type="password" autoComplete="new-password" required value={confirm}
            onChange={(e) => setConfirm(e.target.value)} className={inputClass} />
        </label>
        <FormError id={ids.error} message={error} />
        <Buttons busy={busy} label="Set passcode" onClose={onClose} />
      </form>
    </Modal>
  );
}

function AccountDialog({
  account,
  me,
  members,
  onClose,
  onSaved,
}: DialogProps & { account?: Account; me: Member; members: Member[] }) {
  const [institution, setInstitution] = useState(account?.institution ?? "");
  const [name, setName] = useState(account?.name ?? "");
  const [nickname, setNickname] = useState(account?.nickname ?? "");
  const [last4, setLast4] = useState(account?.last4 ?? "");
  const [trimmed, setTrimmed] = useState(false);
  const [type, setType] = useState<AccountType>(account?.type ?? "checking");
  const [owners, setOwners] = useState<number[]>(account?.owner_ids ?? [me.id]);
  const liability = LIABILITY_TYPES.includes(type);
  // Liabilities are typed as the amount owed (positive) and stored negative.
  const startCents = account ? (account.is_liability ? -account.opening_balance_cents : account.opening_balance_cents) : 0;
  const [balance, setBalance] = useState(account ? centsToInput(startCents) : "");
  const [openingDate, setOpeningDate] = useState(account?.opening_date ?? "");
  const { busy, error, setError, run } = useSubmit(onSaved);
  const ids = { institution: useId(), name: useId(), nickname: useId(), last4: useId(), last4Help: useId(),
    type: useId(), balance: useId(), date: useId(), error: useId() };
  const choosable = members.filter((m) => !m.is_archived || owners.includes(m.id));

  const save = (e: FormEvent) => {
    const cents = parseDollars(balance);
    if (cents === null) {
      e.preventDefault();
      return setError("Enter the balance as an amount, for example 1250.00.");
    }
    if (owners.length === 0) {
      e.preventDefault();
      return setError("Pick at least one owner.");
    }
    const body = {
      institution,
      name,
      nickname,
      last4,
      type,
      owner_ids: owners,
      opening_balance_cents: liability ? -cents : cents,
      opening_date: openingDate || null,
    };
    return run(e, () => (account ? send("PATCH", `/api/accounts/${account.id}`, body) : send("POST", "/api/accounts", body)));
  };

  return (
    <Modal title={account ? `Edit ${account.display_name}` : "Add an account"} onClose={onClose}>
      <form onSubmit={save} className="flex flex-col gap-4" aria-describedby={error ? ids.error : undefined}>
        <div className="grid gap-4 sm:grid-cols-2">
          <label htmlFor={ids.institution} className="flex flex-col gap-1.5 text-sm font-medium">
            Bank or institution
            <input id={ids.institution} required maxLength={80} value={institution} onChange={(e) => setInstitution(e.target.value)}
              className={inputClass} autoFocus />
          </label>
          <label htmlFor={ids.type} className="flex flex-col gap-1.5 text-sm font-medium">
            Type
            <select id={ids.type} value={type} onChange={(e) => setType(e.target.value as AccountType)} className={inputClass}>
              {ACCOUNT_TYPES.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label htmlFor={ids.name} className="flex flex-col gap-1.5 text-sm font-medium">
          Account name, as the bank shows it
          <input id={ids.name} required maxLength={80} placeholder="e.g. Total Checking" value={name}
            onChange={(e) => setName(e.target.value)} className={inputClass} />
        </label>
        <div className="grid gap-4 sm:grid-cols-[1fr_auto]">
          <label htmlFor={ids.nickname} className="flex flex-col gap-1.5 text-sm font-medium">
            Nickname (optional)
            <input id={ids.nickname} maxLength={60} placeholder="e.g. Grocery card" value={nickname}
              onChange={(e) => setNickname(e.target.value)} className={inputClass} />
          </label>
          <label htmlFor={ids.last4} className="flex flex-col gap-1.5 text-sm font-medium">
            Last 4 digits
            <input id={ids.last4} inputMode="numeric" pattern="\d{4}" autoComplete="off" value={last4} aria-describedby={ids.last4Help}
              onChange={(e) => {
                // A pasted full number keeps only its last 4 digits; the rest is never stored or sent.
                const digits = e.target.value.replace(/\D/g, "");
                setTrimmed(digits.length > 4);
                setLast4(digits.slice(-4));
              }}
              className={inputClass + " amount w-28"} />
          </label>
        </div>
        <p id={ids.last4Help} className="-mt-2 m-0 text-[13px] text-muted">
          {trimmed && <strong className="font-medium text-ink">Kept only the last 4 digits. </strong>}
          Kinsum only keeps the last 4 digits, never the full account number. A nickname is shown everywhere in place of
          the bank's name.
        </p>
        <fieldset className="m-0 border-0 p-0">
          <legend className="mb-1.5 p-0 text-sm font-medium">Owners</legend>
          <div className="flex flex-wrap gap-2">
            {choosable.map((m) => (
              <label key={m.id}
                className={"flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm " +
                  (owners.includes(m.id) ? "border-primary bg-primary-soft" : "border-border")}>
                <input type="checkbox" className="h-4 w-4 accent-primary" checked={owners.includes(m.id)}
                  onChange={(e) => setOwners(e.target.checked ? [...owners, m.id] : owners.filter((x) => x !== m.id))} />
                <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full" style={{ background: m.colour }} />
                {m.name}
              </label>
            ))}
          </div>
          <span className="mt-1.5 block text-[13px] text-muted">Pick several people for a shared account.</span>
        </fieldset>
        <div className="grid gap-4 sm:grid-cols-2">
          <label htmlFor={ids.balance} className="flex flex-col gap-1.5 text-sm font-medium">
            {liability ? "Amount owed at the start" : "Balance at the start"}
            <input id={ids.balance} inputMode="decimal" placeholder="0.00" value={balance}
              onChange={(e) => setBalance(e.target.value)} className={inputClass + " amount"} />
          </label>
          <label htmlFor={ids.date} className="flex flex-col gap-1.5 text-sm font-medium">
            On this date
            <input id={ids.date} type="date" value={openingDate} onChange={(e) => setOpeningDate(e.target.value)} className={inputClass} />
          </label>
        </div>
        <p className="-mt-2 m-0 text-[13px] text-muted">
          Use the balance on the day before your first statement starts. Statement balances will correct it later.
        </p>
        <FormError id={ids.error} message={error} />
        <Buttons busy={busy} label={account ? "Save" : "Add account"} onClose={onClose} />
      </form>
    </Modal>
  );
}
