import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { ApiError, api, errorMessage } from "../../api/client";
import type { SchemaField } from "../../api/types";
import { useToast } from "../Toast";
import EmailPreview from "./EmailPreview";
import FieldInput from "./FieldInput";
import { SECTION_LABELS } from "./labels";

interface Props {
  section: string;
  fields: SchemaField[];
  saved: Record<string, unknown>;
}

function same(a: unknown, b: unknown) {
  return JSON.stringify(a) === JSON.stringify(b);
}

function clean(field: SchemaField, value: unknown) {
  if (field.type === "list") return (value as string[]).map((v) => v.trim()).filter(Boolean);
  // Whole numbers typed in a text box compare equal to the saved number.
  if (field.type === "int" && typeof value === "string" && /^-?\d+$/.test(value.trim())) return Number(value.trim());
  return value;
}

export default function SectionForm({ section, fields, saved }: Props) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [draft, setDraft] = useState<Record<string, unknown>>(saved);
  const [errors, setErrors] = useState<Record<string, string>>({});
  useEffect(() => setDraft(saved), [saved]);

  const changed = useMemo(() => {
    const out: Record<string, unknown> = {};
    for (const field of fields) {
      const value = clean(field, draft[field.key]);
      if (!same(value, saved[field.key])) out[field.key] = value;
    }
    return out;
  }, [draft, saved, fields]);
  const dirty = Object.keys(changed).length > 0;
  const name = SECTION_LABELS[section] ?? section;

  const save = useMutation({
    mutationFn: () => api<Record<string, unknown>>(`/api/settings/${section}`, { method: "PUT", body: changed }),
    onSuccess: (data) => {
      setErrors({});
      queryClient.setQueryData(["settings"], (old: Record<string, unknown> | undefined) => (old ? { ...old, [section]: data } : old));
      toast("Saved. Used on the next run.");
    },
    onError: (error) => {
      if (error instanceof ApiError && Object.keys(error.fieldErrors).length) {
        setErrors(error.fieldErrors);
        const first = Object.keys(error.fieldErrors)[0];
        document.getElementById(`field-${section}-${first}`)?.focus();
      } else {
        toast(errorMessage(error), "error");
      }
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (dirty) save.mutate();
  }

  return (
    <form onSubmit={submit} className="panel" aria-label={`${name} settings`} noValidate>
      <div className={section === "email" ? "grid gap-6 p-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]" : "p-5"}>
        <div className="flex max-w-3xl flex-col gap-5">
          {fields.map((field) => (
            <FieldInput
              key={field.key}
              field={field}
              value={draft[field.key]}
              error={errors[field.key]}
              onChange={(value) => {
                setDraft((d) => ({ ...d, [field.key]: value }));
                if (errors[field.key]) setErrors(({ [field.key]: _, ...rest }) => rest);
              }}
            />
          ))}
        </div>
        {section === "email" && <EmailPreview values={draft} />}
      </div>
      <div className="sticky bottom-0 flex items-center gap-3 rounded-b-lg border-t border-line bg-surface px-5 py-3">
        <button type="submit" className="btn-primary" disabled={!dirty || save.isPending}>
          {save.isPending ? "Saving…" : `Save ${name.toLowerCase()}`}
        </button>
        <button type="button" className="btn-ghost" disabled={!dirty || save.isPending} onClick={() => { setDraft(saved); setErrors({}); }}>
          Discard changes
        </button>
        <p className="text-sm text-muted" aria-live="polite">
          {dirty ? "Unsaved changes" : "Changes apply to the next run."}
        </p>
      </div>
    </form>
  );
}
