import type { SchemaField } from "../../api/types";
import AnswersEditor, { type Answer } from "./AnswersEditor";
import { fieldLabel } from "./labels";

interface Props {
  field: SchemaField;
  value: unknown;
  error?: string;
  onChange: (value: unknown) => void;
}

export default function FieldInput({ field, value, error, onChange }: Props) {
  const id = `field-${field.section}-${field.key}`;
  const helpId = `${id}-help`;
  const errorId = `${id}-error`;
  const describedBy = [error ? errorId : null, field.help ? helpId : null].filter(Boolean).join(" ") || undefined;
  const label = fieldLabel(field.key);
  const common = { id, "aria-invalid": error ? ("true" as const) : ("false" as const), "aria-describedby": describedBy };

  const help = field.help ? (
    <p id={helpId} className="help">
      {field.help}
    </p>
  ) : null;
  const errorText = error ? (
    <p id={errorId} className="mt-1 text-sm font-medium text-danger">
      {error}
    </p>
  ) : null;

  if (field.type === "bool") {
    return (
      <div className="flex items-start justify-between gap-6 py-1">
        <div>
          <label htmlFor={id} className="text-sm font-medium">
            {label}
          </label>
          {help}
          {errorText}
        </div>
        <input
          {...common}
          type="checkbox"
          role="switch"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
          className="mt-0.5 h-5 w-9 shrink-0 cursor-pointer appearance-none rounded-full bg-control transition-colors duration-150 before:block before:h-4 before:w-4 before:translate-x-0.5 before:translate-y-0.5 before:rounded-full before:bg-white before:transition-transform before:duration-150 checked:bg-pine checked:before:translate-x-[18px]"
        />
      </div>
    );
  }

  if (field.type === "multi_enum") {
    const selected = Array.isArray(value) ? (value as string[]) : [];
    return (
      <fieldset aria-describedby={describedBy}>
        <legend className="label">{label}</legend>
        <div className="flex flex-wrap gap-x-5 gap-y-2">
          {(field.options ?? []).map((option) => (
            <label key={option} className="inline-flex min-h-[32px] cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="h-4 w-4 accent-[var(--pine)]"
                checked={selected.includes(option)}
                onChange={(e) => onChange(e.target.checked ? [...selected, option] : selected.filter((s) => s !== option))}
              />
              {option}
            </label>
          ))}
        </div>
        {help}
        {errorText}
      </fieldset>
    );
  }

  if (field.type === "answers") {
    return (
      <div>
        <p className="label">{label}</p>
        {help}
        <div className="mt-2">
          <AnswersEditor id={id} value={(value as Answer[]) ?? []} onChange={onChange} />
        </div>
        {errorText}
      </div>
    );
  }

  let control;
  if (field.type === "enum") {
    control = (
      <select {...common} className="field" value={String(value ?? "")} onChange={(e) => onChange(e.target.value)}>
        {(field.options ?? []).map((option) => (
          <option key={option} value={option}>
            {option === "" ? "Not set" : option}
          </option>
        ))}
      </select>
    );
  } else if (field.type === "text" || field.type === "list") {
    const text = field.type === "list" ? ((value as string[]) ?? []).join("\n") : String(value ?? "");
    const rows = Math.min(14, Math.max(field.type === "list" ? 3 : 4, text.split("\n").length + 1));
    control = (
      <textarea
        {...common}
        className="field resize-y"
        rows={rows}
        value={text}
        onChange={(e) => onChange(field.type === "list" ? e.target.value.split("\n") : e.target.value)}
      />
    );
  } else {
    control = (
      <input
        {...common}
        className={`field ${field.type === "int" ? "max-w-[14rem] tabular-nums" : ""}`}
        type="text"
        inputMode={field.type === "int" ? "numeric" : undefined}
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }

  return (
    <div>
      <label htmlFor={id} className="label">
        {label}
      </label>
      {control}
      {field.type === "list" && !field.help.includes("one per") && <p className="help">One per line.</p>}
      {help}
      {errorText}
    </div>
  );
}
