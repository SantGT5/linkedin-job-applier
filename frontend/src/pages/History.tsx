import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api, errorMessage } from "../api/client";
import type { AppliedJob, FailedJob, Page } from "../api/types";
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
          rows={list.data?.items as AppliedJob[] | undefined}
          rowKey={(r) => r.job_id}
          empty={filtered ? "No applications match these filters." : "No applications yet. Start the bot from the dashboard."}
        />
      ) : (
        <DataTable
          {...common}
          label="Failed or skipped jobs"
          columns={FAILED}
          rows={list.data?.items as FailedJob[] | undefined}
          rowKey={(r) => r.id}
          empty={filtered ? "Nothing matches these filters." : "Nothing failed or was skipped yet."}
        />
      )}
    </div>
  );
}
