import { useCallback, useEffect, useId, useMemo, useState, type FormEvent } from "react";
import {
  CATEGORY_COLOURS,
  CATEGORY_KINDS,
  getJson,
  send,
  type Category,
  type CategoryKind,
  type Member,
} from "../api";
import { CategoryIcon } from "../components/CategoryIcon";
import { Modal, inputClass, primaryButton, secondaryButton } from "../components/Modal";
import { searchIcons } from "../lib/categoryIcons";

type Dialog =
  | { kind: "edit"; category?: Category; parentId?: number | null }
  | { kind: "merge"; category: Category }
  | null;

export function Categories({ me }: { me: Member }) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [showArchived, setShowArchived] = useState(false);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [error, setError] = useState("");
  const canEdit = me.access === "household";

  const load = useCallback(async () => {
    try {
      setCategories(await getJson<Category[]>(`/api/categories${showArchived ? "?include_archived=true" : ""}`));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }, [showArchived]);

  useEffect(() => {
    load();
  }, [load]);

  const groups = categories.filter((c) => c.parent_id === null);
  const childrenOf = (id: number) => categories.filter((c) => c.parent_id === id);
  const saved = async () => {
    setDialog(null);
    await load();
  };

  return (
    <div className="flex max-w-5xl flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="m-0 max-w-xl text-sm leading-relaxed text-muted">
          Every transaction gets one of these. Groups hold subcategories, for example Food › Groceries.
          {!canEdit && " Only an adult with whole-household access can change them."}
        </p>
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
          {canEdit && (
            <button type="button" className={primaryButton} onClick={() => setDialog({ kind: "edit", parentId: null })}>
              Add group
            </button>
          )}
        </div>
      </div>

      {error && (
        <p role="alert" className="m-0 rounded-lg border border-over/30 bg-surface px-4 py-3 text-sm text-over">
          {error}
        </p>
      )}

      {CATEGORY_KINDS.map((kind) => {
        const inKind = groups.filter((g) => g.kind === kind.id);
        if (inKind.length === 0) return null;
        return (
          <section key={kind.id} aria-labelledby={`kind-${kind.id}`} className="flex flex-col gap-3">
            <div>
              <h2 id={`kind-${kind.id}`} className="m-0 text-lg font-semibold">
                {kind.label}
              </h2>
              <p className="m-0 text-[13px] text-muted">{kind.hint}</p>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {inKind.map((group) => (
                <article
                  key={group.id}
                  className={"flex flex-col rounded-xl border border-border bg-surface " + (group.is_archived ? "opacity-70" : "")}
                >
                  <header className="flex items-center gap-2 border-b border-border px-3 py-2.5">
                    <Row category={group} canEdit={canEdit} strong onOpen={() => setDialog({ kind: "edit", category: group })} />
                    {canEdit && !group.is_archived && (
                      <button
                        type="button"
                        className={secondaryButton + " shrink-0"}
                        onClick={() => setDialog({ kind: "edit", parentId: group.id })}
                        aria-label={`Add a subcategory to ${group.name}`}
                      >
                        Add
                      </button>
                    )}
                  </header>
                  <ul className="m-0 flex list-none flex-col p-1.5">
                    {childrenOf(group.id).map((c) => (
                      <li key={c.id} className={c.is_archived ? "opacity-70" : ""}>
                        <Row category={c} canEdit={canEdit} onOpen={() => setDialog({ kind: "edit", category: c })} />
                      </li>
                    ))}
                    {childrenOf(group.id).length === 0 && (
                      <li className="px-2 py-2 text-[13px] text-muted">No subcategories.</li>
                    )}
                  </ul>
                </article>
              ))}
            </div>
          </section>
        );
      })}

      {dialog?.kind === "edit" && (
        <CategoryDialog
          category={dialog.category}
          parentId={dialog.category ? dialog.category.parent_id : (dialog.parentId ?? null)}
          categories={categories}
          onClose={() => setDialog(null)}
          onSaved={saved}
          onMerge={(c) => setDialog({ kind: "merge", category: c })}
        />
      )}
      {dialog?.kind === "merge" && (
        <MergeDialog category={dialog.category} categories={categories} onClose={() => setDialog(null)} onSaved={saved} />
      )}
    </div>
  );
}

function Row({
  category,
  canEdit,
  strong,
  onOpen,
}: {
  category: Category;
  canEdit: boolean;
  strong?: boolean;
  onOpen: () => void;
}) {
  const content = (
    <>
      <CategoryIcon icon={category.icon} colour={category.colour} size={strong ? 34 : 28} />
      <span className={"truncate " + (strong ? "font-semibold" : "")}>{category.name}</span>
      {category.is_archived && <span className="text-[12px] text-muted">Archived</span>}
    </>
  );
  const cls = "flex min-h-[40px] w-full min-w-0 items-center gap-2.5 rounded-lg px-1.5 text-left text-sm";
  if (!canEdit) return <div className={cls}>{content}</div>;
  return (
    <button
      type="button"
      onClick={onOpen}
      aria-label={`Edit ${category.name}`}
      className={cls + " cursor-pointer transition-colors duration-200 hover:bg-page"}
    >
      {content}
    </button>
  );
}

// ---- dialogs ------------------------------------------------------------------
function CategoryDialog({
  category,
  parentId: startParent,
  categories,
  onClose,
  onSaved,
  onMerge,
}: {
  category?: Category;
  parentId: number | null;
  categories: Category[];
  onClose: () => void;
  onSaved: () => void;
  onMerge: (c: Category) => void;
}) {
  const groups = categories.filter((c) => c.parent_id === null && !c.is_archived && c.id !== category?.id);
  const hasChildren = !!category && categories.some((c) => c.parent_id === category.id);
  const [name, setName] = useState(category?.name ?? "");
  const [parentId, setParentId] = useState<number | null>(startParent);
  const [kind, setKind] = useState<CategoryKind>(category?.kind ?? "expense");
  const parent = categories.find((c) => c.id === parentId);
  const [icon, setIcon] = useState(category?.icon ?? "tag");
  // A new subcategory takes its group's colour until another one is picked.
  const [colour, setColour] = useState<string | null>(category?.colour ?? (startParent === null ? CATEGORY_COLOURS[0] : null));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const ids = { name: useId(), parent: useId(), error: useId() };
  const isGroup = parentId === null;
  const shownColour = colour ?? parent?.colour ?? CATEGORY_COLOURS[0];

  async function run(action: () => Promise<unknown>) {
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

  function save(e: FormEvent) {
    e.preventDefault();
    const body = { name, icon, parent_id: parentId, ...(isGroup ? { kind } : {}), ...(colour ? { colour } : {}) };
    run(() => (category ? send("PATCH", `/api/categories/${category.id}`, body) : send("POST", "/api/categories", body)));
  }

  const title = category ? `Edit ${category.name}` : isGroup ? "Add a group" : `Add a subcategory to ${parent?.name ?? ""}`;
  return (
    <Modal title={title} onClose={onClose}>
      <form onSubmit={save} className="flex flex-col gap-4" aria-describedby={error ? ids.error : undefined}>
        <div className="flex items-end gap-3">
          <CategoryIcon icon={icon} colour={shownColour} size={44} />
          <label htmlFor={ids.name} className="flex flex-1 flex-col gap-1.5 text-sm font-medium">
            Name
            <input id={ids.name} required maxLength={40} value={name} onChange={(e) => setName(e.target.value)}
              className={inputClass} autoFocus />
          </label>
        </div>

        {category && !hasChildren && (
          <label htmlFor={ids.parent} className="flex flex-col gap-1.5 text-sm font-medium">
            Group
            <select id={ids.parent} value={parentId ?? ""} className={inputClass}
              onChange={(e) => setParentId(e.target.value === "" ? null : Number(e.target.value))}>
              <option value="">None: make it a group of its own</option>
              {groups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          </label>
        )}

        {isGroup ? (
          <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
            <legend className="mb-1.5 p-0 text-sm font-medium">Kind</legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {CATEGORY_KINDS.map((k) => (
                <label key={k.id}
                  className={"flex cursor-pointer items-start gap-2.5 rounded-lg border px-3 py-2.5 text-sm font-medium " +
                    (kind === k.id ? "border-primary bg-primary-soft" : "border-border")}>
                  <input type="radio" name="kind" checked={kind === k.id} onChange={() => setKind(k.id)} className="mt-0.5 h-4 w-4 accent-primary" />
                  <span>
                    {k.label}
                    <span className="block text-[12px] font-normal text-muted">{k.hint}</span>
                  </span>
                </label>
              ))}
            </div>
            {category && hasChildren && <span className="text-[13px] text-muted">Its subcategories change kind with it.</span>}
          </fieldset>
        ) : (
          <p className="m-0 text-[13px] text-muted">
            Kind: {CATEGORY_KINDS.find((k) => k.id === (parent?.kind ?? kind))?.label}, the same as its group.
          </p>
        )}

        <IconPicker value={icon} colour={shownColour} onChange={setIcon} />

        <fieldset className="m-0 border-0 p-0">
          <legend className="mb-1.5 p-0 text-sm font-medium">Colour</legend>
          <div className="flex flex-wrap gap-2">
            {CATEGORY_COLOURS.map((c, i) => (
              <label key={c} className="cursor-pointer">
                <input type="radio" name="category-colour" className="peer sr-only" checked={shownColour === c} onChange={() => setColour(c)} />
                <span className="sr-only">Colour {i + 1}</span>
                <span aria-hidden="true"
                  className="block h-7 w-7 rounded-full ring-offset-2 peer-checked:ring-2 peer-checked:ring-ink peer-focus-visible:outline-2 peer-focus-visible:outline-primary"
                  style={{ background: c }} />
              </label>
            ))}
          </div>
        </fieldset>

        {error && (
          <p id={ids.error} role="alert" className="m-0 text-[13px] font-medium text-over">
            {error}
          </p>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
          <div className="flex gap-2">
            {category && !category.is_archived && (
              <>
                <button type="button" className={secondaryButton} onClick={() => onMerge(category)}>
                  Merge…
                </button>
                <button type="button" className={secondaryButton} disabled={busy}
                  onClick={() => run(() => send("PATCH", `/api/categories/${category.id}`, { is_archived: true }))}>
                  Archive
                </button>
              </>
            )}
            {category?.is_archived && (
              <button type="button" className={secondaryButton} disabled={busy}
                onClick={() => run(() => send("PATCH", `/api/categories/${category.id}`, { is_archived: false }))}>
                Restore
              </button>
            )}
          </div>
          <div className="flex gap-2">
            <button type="button" className={secondaryButton} onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className={primaryButton} disabled={busy}>
              {busy ? "Saving…" : category ? "Save" : "Add"}
            </button>
          </div>
        </div>
        {category && hasChildren && !category.is_archived && (
          <p className="m-0 text-[12px] text-muted">Archiving a group archives its subcategories too.</p>
        )}
      </form>
    </Modal>
  );
}

function IconPicker({ value, colour, onChange }: { value: string; colour: string; onChange: (name: string) => void }) {
  const [query, setQuery] = useState("");
  const results = useMemo(() => searchIcons(query), [query]);
  const searchId = useId();

  return (
    <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
      <legend className="mb-1.5 p-0 text-sm font-medium">Icon</legend>
      <label htmlFor={searchId} className="sr-only">
        Search icons
      </label>
      <input id={searchId} type="search" placeholder="Search icons, e.g. pet, gym, rent" value={query}
        onChange={(e) => setQuery(e.target.value)} className={inputClass} />
      <div className="grid max-h-48 grid-cols-[repeat(auto-fill,minmax(40px,1fr))] gap-1 overflow-y-auto rounded-lg border border-border p-1.5">
        {results.map(({ name, Icon }) => (
          <label key={name} title={name.replaceAll("-", " ")} className="cursor-pointer">
            <input type="radio" name="category-icon" className="peer sr-only" checked={value === name} onChange={() => onChange(name)} />
            <span className="sr-only">{name.replaceAll("-", " ")}</span>
            <span aria-hidden="true"
              className="flex h-10 items-center justify-center rounded-md text-muted transition-colors duration-200 hover:bg-page peer-checked:ring-2 peer-checked:ring-primary peer-focus-visible:outline-2 peer-focus-visible:outline-primary"
              style={value === name ? { background: `${colour}1F`, color: colour } : undefined}>
              <Icon size={20} strokeWidth={1.8} />
            </span>
          </label>
        ))}
        {results.length === 0 && <p className="col-span-full m-0 p-2 text-[13px] text-muted">No icons match “{query}”.</p>}
      </div>
    </fieldset>
  );
}

function MergeDialog({
  category,
  categories,
  onClose,
  onSaved,
}: {
  category: Category;
  categories: Category[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const hasChildren = categories.some((c) => c.parent_id === category.id);
  const nameOf = (c: Category) => {
    const parent = categories.find((p) => p.id === c.parent_id);
    return parent ? `${parent.name} › ${c.name}` : c.name;
  };
  const targets = categories.filter(
    (c) =>
      c.id !== category.id &&
      !c.is_archived &&
      c.kind === category.kind &&
      c.parent_id !== category.id &&
      (!hasChildren || c.parent_id === null),
  );
  const [into, setInto] = useState<number | "">("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const selectId = useId();

  async function merge(e: FormEvent) {
    e.preventDefault();
    if (into === "") return setError("Choose where to merge it.");
    setBusy(true);
    try {
      await send("POST", `/api/categories/${category.id}/merge`, { into_id: into });
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title={`Merge ${category.name}`} onClose={onClose}>
      <p className="m-0 text-sm leading-relaxed text-muted">
        Everything in {category.name} moves to the category you choose, and {category.name} is removed.
        {hasChildren && " Its subcategories move too; any with the same name are combined."} This cannot be undone.
      </p>
      <form onSubmit={merge} className="flex flex-col gap-4">
        <label htmlFor={selectId} className="flex flex-col gap-1.5 text-sm font-medium">
          Merge into
          <select id={selectId} value={into} onChange={(e) => setInto(e.target.value === "" ? "" : Number(e.target.value))} className={inputClass}>
            <option value="">Choose a category…</option>
            {targets.map((c) => (
              <option key={c.id} value={c.id}>
                {nameOf(c)}
              </option>
            ))}
          </select>
        </label>
        {error && (
          <p role="alert" className="m-0 text-[13px] font-medium text-over">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <button type="button" className={secondaryButton} onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className={primaryButton} disabled={busy}>
            {busy ? "Merging…" : "Merge"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
