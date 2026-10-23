import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { api, errorMessage } from "../api/client";
import type { AppliedJob, FailedJob, Page } from "../api/types";
import { useBulkDelete } from "../components/BulkDelete";
import DataTable, { type Column } from "../components/DataTable";
import { DateFilter, FilterBar, TextFilter } from "../components/FilterBar";
import Icon from "../components/Icon";
import Pagination from "../components/Pagination";
import { formatDate } from "../components/format";
import { useUrlFilters } from "../components/useUrlFilters";

const FILTERS = ["q", "company", "date_from", "date_to"] as const;
type Tab = "applied" | "failed";

function JobLink({ href, text }: { href: string | null; text: string }) {
  return href ? (
    <a href={href} target="_blank" rel="noreferrer" className="text-pine underline-offset-2 hover:underline">
      {text}
    </a>
  ) : (
    <>{text}</>
  );
}

const APPLIED: Column<AppliedJob>[] = [
  { header: "Role", cell: (r) => <JobLink href={r.job_link} text={r.title ?? r.job_id} /> },
  { header: "Company", cell: (r) => r.company ?? "—" },
  { header: "Location", cell: (r) => [r.work_location, r.work_style].filter(Boolean).join(" · ") || "—" },
  { header: "Applied", cell: (r) => <span className="whitespace-nowrap">{formatDate(r.date_applied)}</span> },
  { header: "How", className: "whitespace-nowrap", cell: (r) => (r.external_job_link === "Easy Applied" ? "Easy Apply" : <JobLink href={r.external_job_link} text="External" />) },
];

const FAILED: Column<FailedJob>[] = [
  { header: "Job", cell: (r) => <JobLink href={r.job_link} text={r.job_id} /> },
  { header: "Reason", cell: (r) => <span className="block max-w-[60ch]">{r.assumed_reason ?? "—"}</span> },
  { header: "Tried", cell: (r) => <span className="whitespace-nowrap">{formatDate(r.date_tried)}</span> },
];

export default function History() {
  const filters = useUrlFilters(FILTERS);
  const tab: Tab = filters.params.get("tab") === "failed" ? "failed" : "applied";
  const query = filters.query();
  const list = useQuery({
    queryKey: ["history", tab, query],
    queryFn: () => api<Page<AppliedJob | FailedJob>>(`/api/history/${tab}?${query}`),
    placeholderData: keepPreviousData,
  });
  const rows = list.data?.items;
  const byKey = new Map<string | number, AppliedJob | FailedJob>(
    rows?.map((r) => [tab === "applied" ? (r as AppliedJob).job_id : (r as FailedJob).id, r]) ?? [],
  );
  // Deleting a whole page steps back to the one before, which still has rows.
  const onDeleted = (deleted: number) => {
    if (rows && deleted >= rows.length && filters.page > 1) filters.setPage(filters.page - 1);
  };
  const deleteApplied = useBulkDelete<string>({
    endpoint: "/api/history/applied/delete",
    noun: ["application", "applications"],
    note: "The bot may come back to these jobs in a later run if LinkedIn doesn't show them as applied.",
    invalidate: [["history", "applied"]],
    onDeleted,
  });
  const deleteFailed = useBulkDelete<number>({
    endpoint: "/api/history/failed/delete",
    noun: ["entry", "entries"],
    invalidate: [["history", "failed"]],
    onDeleted,
  });
  // A selection belongs to the rows on screen: a new tab, page or filter clears it.
  useEffect(() => {
    deleteApplied.clear();
    deleteFailed.clear();
  }, [tab, query]);

  function selectTab(next: Tab) {
    filters.setParams((current) => {
      const p = new URLSearchParams(current);
      p.delete("page");
      if (next === "failed") p.set("tab", "failed");
      else p.delete("tab");
      return p;
    });
  }

  const { values, setFilter } = filters;
  const common = {
    loading: list.isFetching && !list.data,
    error: list.isError ? `Couldn't load history. ${errorMessage(list.error)}` : null,
    footer: list.data && <Pagination page={list.data.page} pageSize={list.data.page_size} total={list.data.total} onPage={filters.setPage} />,
  };
  const filtered = FILTERS.some((k) => values[k]);

  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">History</h1>
          <p className="mt-1 text-sm text-muted">Every application the bot sent, and every job it skipped or couldn't finish.</p>
        </div>
        <a href={`/api/export/${tab}.csv`} className="btn-secondary" aria-label={`Export CSV of ${tab === "applied" ? "applied" : "failed or skipped"} jobs`}>
          <Icon name="download" className="h-4 w-4" />
          Export CSV
        </a>
      </div>
      <div role="tablist" aria-label="History" className="mt-5 flex gap-1 border-b border-line">
        {(["applied", "failed"] as Tab[]).map((t) => (
          <button
            key={t}
            role="tab"
            type="button"
            aria-selected={tab === t}
            onClick={() => selectTab(t)}
            className={`-mb-px min-h-[40px] border-b-2 px-4 text-sm ${tab === t ? "border-pine font-semibold" : "border-transparent text-muted hover:text-ink"}`}
          >
            {t === "applied" ? "Applied" : "Failed or skipped"}
          </button>
        ))}
      </div>
      <div className="mt-4">
        <FilterBar label="Filter history">
          <TextFilter id="h-q" label="Search" value={values.q} onChange={(v) => setFilter("q", v)} width="w-56" />
          {tab === "applied" && <TextFilter id="h-company" label="Company" value={values.company} onChange={(v) => setFilter("company", v)} />}
          <DateFilter id="h-from" label="From" value={values.date_from} onChange={(v) => setFilter("date_from", v)} />
          <DateFilter id="h-to" label="Until" value={values.date_to} onChange={(v) => setFilter("date_to", v)} />
        </FilterBar>
      </div>
      {tab === "applied" ? (
        <DataTable
          {...common}
          label="Applied jobs"
          columns={APPLIED}
          rows={rows as AppliedJob[] | undefined}
          rowKey={(r) => r.job_id}
          selection={{ ...deleteApplied.selection, rowLabel: (k) => `Select ${(byKey.get(k) as AppliedJob | undefined)?.title ?? k}` }}
          toolbar={deleteApplied.bar}
          empty={filtered ? "No applications match these filters." : "No applications yet. Start the bot from the dashboard."}
        />
      ) : (
        <DataTable
          {...common}
          label="Failed or skipped jobs"
          columns={FAILED}
          rows={rows as FailedJob[] | undefined}
          rowKey={(r) => r.id}
          selection={{ ...deleteFailed.selection, rowLabel: (k) => `Select job ${(byKey.get(k) as FailedJob | undefined)?.job_id ?? k}` }}
          toolbar={deleteFailed.bar}
          empty={filtered ? "Nothing matches these filters." : "Nothing failed or was skipped yet."}
        />
      )}
      {deleteApplied.dialog}
      {deleteFailed.dialog}
    </div>
  );
}
