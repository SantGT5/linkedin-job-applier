import type { ReactNode } from "react";

export interface Column<T> {
  header: string;
  cell: (row: T) => ReactNode;
  className?: string;
}

/** A table with its loading, error and empty states; `footer` is usually Pagination. */
export default function DataTable<T>({ label, columns, rows, rowKey, loading, error, empty, footer }: {
  label: string;
  columns: Column<T>[];
  rows: T[] | undefined;
  rowKey: (row: T) => string | number;
  loading: boolean;
  error: string | null;
  empty: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="panel mt-4 overflow-hidden">
      <div className="overflow-x-auto">
        <table aria-label={label} aria-busy={loading} className="w-full text-left text-sm">
          <thead className="border-b border-line bg-ground text-muted">
            <tr>
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
                  <td colSpan={columns.length} className="px-4 py-3">
                    <div className="h-4 w-2/3 animate-pulse rounded bg-ground" />
                  </td>
                </tr>
              ))}
            {rows?.map((row) => (
              <tr key={rowKey(row)} className="border-t border-line align-top first:border-t-0 hover:bg-[#f5f6f3]">
                {columns.map((c) => (
                  <td key={c.header} className={`px-4 py-3 ${c.className ?? ""}`}>
                    {c.cell(row)}
                  </td>
                ))}
              </tr>
            ))}
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
