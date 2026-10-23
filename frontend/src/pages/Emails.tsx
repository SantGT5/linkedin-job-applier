import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, errorMessage } from "../api/client";
import type { HrEmail, Page } from "../api/types";
import ConfirmSentDialog from "../components/ConfirmSentDialog";
import CopyEmailModal from "../components/CopyEmailModal";
import DataTable, { type Column } from "../components/DataTable";
import { DateFilter, FilterBar, SelectFilter, TextFilter } from "../components/FilterBar";
import Icon from "../components/Icon";
import Pagination from "../components/Pagination";
import { useToast } from "../components/Toast";
import { copyText } from "../components/clipboard";
import { formatDate } from "../components/format";
import { useUrlFilters } from "../components/useUrlFilters";

const FILTERS = ["status", "company", "role", "q", "date_from", "date_to"] as const;

function StatusChip({ status }: { status: HrEmail["status"] }) {
  return status === "emailed" ? (
    <span className="inline-flex items-center gap-1 rounded-full bg-pine-soft px-2.5 py-0.5 text-xs font-medium text-pine-dark">
      <Icon name="check" className="h-3.5 w-3.5" />
      Emailed
    </span>
  ) : (
    <span className="inline-flex rounded-full border border-line px-2.5 py-0.5 text-xs font-medium">New</span>
  );
}

export default function Emails() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const filters = useUrlFilters(FILTERS);
  const [composing, setComposing] = useState<HrEmail | null>(null);
  const [confirming, setConfirming] = useState<HrEmail | null>(null);

  const list = useQuery({
    queryKey: ["emails", filters.query()],
    queryFn: () => api<Page<HrEmail>>(`/api/emails?${filters.query()}`),
    placeholderData: keepPreviousData,
  });
  const markEmailed = useMutation({
    mutationFn: (email: HrEmail) => api<HrEmail>(`/api/emails/${email.id}/mark-emailed`, { method: "POST" }),
    onSuccess: (_, email) => {
      setConfirming(null);
      toast(`Marked ${email.email} as emailed.`);
      void queryClient.invalidateQueries({ queryKey: ["emails"] });
      void queryClient.invalidateQueries({ queryKey: ["nav-count"] });
    },
    onError: (e) => toast(errorMessage(e), "error"),
  });

  const columns: Column<HrEmail>[] = [
    {
      header: "HR email",
      cell: (row) => (
        <div className="flex items-center gap-1">
          <span className="[overflow-wrap:anywhere]">{row.email}</span>
          <button
            type="button"
            className="btn-ghost min-h-[32px] px-1.5"
            aria-label={`Copy address ${row.email}`}
            title="Copy address"
            onClick={() => copyText(row.email).then(() => toast(`Copied ${row.email}`), () => toast("Couldn't copy. Copy it by hand.", "error"))}
          >
            <Icon name="copy" className="h-4 w-4" />
          </button>
        </div>
      ),
    },
    {
      header: "Role",
      cell: (row) =>
        row.job_link ? (
          <a href={row.job_link} target="_blank" rel="noreferrer" className="text-pine underline-offset-2 hover:underline">
            {row.title ?? row.job_id}
          </a>
        ) : (
          row.title ?? row.job_id
        ),
    },
    { header: "Company", cell: (row) => row.company ?? "—" },
    { header: "Found", cell: (row) => <span className="whitespace-nowrap">{formatDate(row.found_at)}</span> },
    { header: "Status", cell: (row) => <StatusChip status={row.status} /> },
    {
      header: "Email",
      className: "text-right",
      cell: (row) => (
        <button type="button" className="btn-secondary min-h-[36px]" aria-label={`Copy email to ${row.email}`} onClick={() => setComposing(row)}>
          Copy
        </button>
      ),
    },
  ];

  const { values, setFilter } = filters;
  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">HR emails</h1>
          <p className="mt-1 max-w-[70ch] text-sm text-muted">
            Addresses found in jobs the bot applied to. Copy the follow-up email, send it yourself, then mark it as emailed.
          </p>
        </div>
        <a href="/api/export/emails.csv" className="btn-secondary" aria-label="Export CSV of HR emails">
          <Icon name="download" className="h-4 w-4" />
          Export CSV
        </a>
      </div>
      <div className="mt-5">
        <FilterBar label="Filter emails">
          <SelectFilter id="f-status" label="Status" value={values.status} onChange={(v) => setFilter("status", v)} options={[["", "All"], ["new", "New"], ["emailed", "Emailed"]]} />
          <TextFilter id="f-company" label="Company" value={values.company} onChange={(v) => setFilter("company", v)} />
          <TextFilter id="f-role" label="Role" value={values.role} onChange={(v) => setFilter("role", v)} />
          <DateFilter id="f-from" label="Found from" value={values.date_from} onChange={(v) => setFilter("date_from", v)} />
          <DateFilter id="f-to" label="Found until" value={values.date_to} onChange={(v) => setFilter("date_to", v)} />
          <TextFilter id="f-q" label="Search" value={values.q} onChange={(v) => setFilter("q", v)} width="w-56" />
        </FilterBar>
      </div>
      <DataTable
        label="HR emails"
        columns={columns}
        rows={list.data?.items}
        rowKey={(row) => row.id}
        loading={list.isFetching && !list.data}
        error={list.isError ? `Couldn't load emails. ${errorMessage(list.error)}` : null}
        empty={
          FILTERS.some((k) => values[k])
            ? "No emails match these filters."
            : "No HR emails yet. They're collected from job descriptions while the bot applies."
        }
        footer={list.data && <Pagination page={list.data.page} pageSize={list.data.page_size} total={list.data.total} onPage={filters.setPage} />}
      />
      {composing && (
        <CopyEmailModal
          email={composing}
          onClose={() => {
            const closed = composing;
            setComposing(null);
            if (closed.status === "new") setConfirming(closed);
          }}
        />
      )}
      {confirming && (
        <ConfirmSentDialog
          email={confirming.email}
          busy={markEmailed.isPending}
          onYes={() => markEmailed.mutate(confirming)}
          onNo={() => setConfirming(null)}
        />
      )}
    </div>
  );
}
