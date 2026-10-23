import type { ReactNode } from "react";

export interface Column<T> {
  header: string;
  cell: (row: T) => ReactNode;
  className?: string;
}

export interface Selection<K> {
  selected: Set<K>;
  onChange: (next: Set<K>) => void;
  /** Accessible name of a row's checkbox, e.g. "Select Go Developer". */
  rowLabel: (key: K) => string;
}

/**
 * A table with its loading, error and empty states; `footer` is usually Pagination.
 * With `selection`, a checkbox column selects rows (the header one selects the whole page)
 * and `toolbar` (the bulk actions) shows above the table.
 */
export default function DataTable<T, K extends string | number>({ label, columns, rows, rowKey, loading, error, empty, footer, selection, toolbar }: {
  label: string;
  columns: Column<T>[];
  rows: T[] | undefined;
  rowKey: (row: T) => K;
  loading: boolean;
  error: string | null;
  empty: ReactNode;
  footer?: ReactNode;
  selection?: Selection<K>;
  toolbar?: ReactNode;
}) {
  const keys = rows?.map(rowKey) ?? [];
  const picked = selection ? keys.filter((k) => selection.selected.has(k)).length : 0;
  const span = columns.length + (selection ? 1 : 0);

  function toggle(key: K) {
    if (!selection) return;
    const next = new Set(selection.selected);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    selection.onChange(next);
  }

  return (
    <div className="panel mt-4 overflow-hidden">
      {toolbar}
      <div className="overflow-x-auto">
        <table aria-label={label} aria-busy={loading} className="w-full text-left text-sm">
          <thead className="border-b border-line bg-ground text-muted">
            <tr>
              {selection && (
                <th scope="col" className="w-10 py-2.5 pl-4 pr-0">
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-pine align-middle"
                    aria-label="Select all on this page"
                    disabled={keys.length === 0}
                    checked={keys.length > 0 && picked === keys.length}
                    ref={(el) => {
                      if (el) el.indeterminate = picked > 0 && picked < keys.length;
                    }}
                    onChange={() => selection.onChange(picked === keys.length ? new Set() : new Set(keys))}
                  />
                </th>
              )}
              {columns.map((c) => (
                <th key={c.header} scope="col" className={`px-4 py-2.5 font-medium ${c.className ?? ""}`}>
                  {c.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading &&
              !rows &&
              Array.from({ length: 5 }, (_, i) => (
                <tr key={i} className="border-t border-line">
                  <td colSpan={span} className="px-4 py-3">
                    <div className="h-4 w-2/3 animate-pulse rounded bg-ground" />
                  </td>
                </tr>
              ))}
            {rows?.map((row) => {
              const key = rowKey(row);
              const checked = selection?.selected.has(key) ?? false;
              return (
              <tr key={key} className={`border-t border-line align-top first:border-t-0 ${checked ? "bg-pine-soft" : "hover:bg-[#f5f6f3]"}`}>
                {selection && (
                  <td className="w-10 py-3 pl-4 pr-0">
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-pine align-middle"
                      aria-label={selection.rowLabel(key)}
                      checked={checked}
                      onChange={() => toggle(key)}
                    />
                  </td>
                )}
                {columns.map((c) => (
                  <td key={c.header} className={`px-4 py-3 ${c.className ?? ""}`}>
                    {c.cell(row)}
                  </td>
                ))}
              </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {error && (
        <p role="alert" className="px-4 py-6 text-danger">
          {error}
        </p>
      )}
      {!loading && !error && rows?.length === 0 && <div className="px-4 py-10 text-center text-muted">{empty}</div>}
      {footer}
    </div>
  );
}
