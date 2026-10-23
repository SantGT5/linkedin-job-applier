export default function Pagination({ page, pageSize, total, onPage }: { page: number; pageSize: number; total: number; onPage: (page: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (total === 0) return null;
  return (
    <nav aria-label="Pagination" className="flex items-center justify-between gap-3 border-t border-line px-4 py-3 text-sm">
      <p className="text-muted tabular-nums">
        {total} {total === 1 ? "result" : "results"}
      </p>
      <div className="flex items-center gap-2">
        <button type="button" className="btn-secondary min-h-[36px]" aria-label="Previous page" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          Previous
        </button>
        <span className="tabular-nums" aria-current="page">{`Page ${page} of ${pages}`}</span>
        <button type="button" className="btn-secondary min-h-[36px]" aria-label="Next page" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          Next
        </button>
      </div>
    </nav>
  );
}
