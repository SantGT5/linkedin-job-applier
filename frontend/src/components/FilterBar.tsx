import { useEffect, useState, type ReactNode } from "react";

export function FilterBar({ children, label = "Filters" }: { children: ReactNode; label?: string }) {
  return (
    <div role="search" aria-label={label} className="flex flex-wrap items-end gap-3">
      {children}
    </div>
  );
}

/** Text filter that updates the list 300 ms after you stop typing. */
export function TextFilter({ id, label, value, onChange, placeholder, width = "w-48" }: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  width?: string;
}) {
  const [text, setText] = useState(value);
  useEffect(() => setText(value), [value]);
  useEffect(() => {
    if (text === value) return;
    const timer = setTimeout(() => onChange(text.trim()), 300);
    return () => clearTimeout(timer);
  }, [text, value, onChange]);
  return (
    <div>
      <label htmlFor={id} className="label">
        {label}
      </label>
      <input id={id} type="search" className={`field h-10 ${width}`} value={text} placeholder={placeholder} onChange={(e) => setText(e.target.value)} />
    </div>
  );
}

export function DateFilter({ id, label, value, onChange }: { id: string; label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label htmlFor={id} className="label">
        {label}
      </label>
      <input id={id} type="date" className="field h-10 w-40" value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

export function SelectFilter({ id, label, value, onChange, options }: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: [string, string][];
}) {
  return (
    <div>
      <label htmlFor={id} className="label">
        {label}
      </label>
      <select id={id} className="field h-10 w-36" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map(([v, text]) => (
          <option key={v} value={v}>
            {text}
          </option>
        ))}
      </select>
    </div>
  );
}
