import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { api, errorMessage } from "../api/client";
import type { Page, UnansweredQuestion } from "../api/types";
import { FilterBar, TextFilter } from "../components/FilterBar";
import Pagination from "../components/Pagination";
import { useToast } from "../components/Toast";
import { formatDate } from "../components/format";
import { useUrlFilters } from "../components/useUrlFilters";

function QuestionRow({ question }: { question: UnansweredQuestion }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [answer, setAnswer] = useState("");
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["questions"] });
    void queryClient.invalidateQueries({ queryKey: ["nav-count"] });
    void queryClient.invalidateQueries({ queryKey: ["settings"] });
  };
  const save = useMutation({
    mutationFn: () => api(`/api/questions/unanswered/${question.id}/answer`, { method: "POST", body: { answer } }),
    onSuccess: () => {
      toast("Saved to your answers. Used on the next run.");
      refresh();
    },
    onError: (e) => toast(errorMessage(e), "error"),
  });
  const dismiss = useMutation({
    mutationFn: () => api(`/api/questions/unanswered/${question.id}`, { method: "DELETE" }),
    onSuccess: refresh,
    onError: (e) => toast(errorMessage(e), "error"),
  });
  const inputId = `answer-${question.id}`;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (answer.trim()) save.mutate();
  }

  return (
    <li className="border-t border-line px-5 py-4 first:border-t-0">
      <p className="font-medium">{question.label}</p>
      <p className="mt-0.5 text-[13px] text-muted">
        {question.question_type} question · seen {question.seen_count} {question.seen_count === 1 ? "time" : "times"} · last {formatDate(question.last_seen)}
      </p>
      {question.options && question.options.length > 0 && (
        <p className="mt-1 text-sm">
          <span className="text-muted">Options: </span>
          {question.options.join(", ")}
        </p>
      )}
      <form onSubmit={submit} className="mt-3 flex flex-wrap items-end gap-2">
        <div className="min-w-[16rem] flex-1">
          <label htmlFor={inputId} className="sr-only">
            Answer for {question.label}
          </label>
          <input
            id={inputId}
            className="field"
            list={question.options?.length ? `${inputId}-options` : undefined}
            placeholder="Your answer"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
          />
          {question.options && (
            <datalist id={`${inputId}-options`}>
              {question.options.map((o) => (
                <option key={o} value={o} />
              ))}
            </datalist>
          )}
        </div>
        <button type="submit" className="btn-primary" disabled={!answer.trim() || save.isPending}>
          Save answer
        </button>
        <button type="button" className="btn-ghost" disabled={dismiss.isPending} onClick={() => dismiss.mutate()}>
          Dismiss
        </button>
      </form>
    </li>
  );
}

export default function Questions() {
  const filters = useUrlFilters(["q"] as const);
  const list = useQuery({
    queryKey: ["questions", filters.query()],
    queryFn: () => api<Page<UnansweredQuestion>>(`/api/questions/unanswered?${filters.query()}`),
    placeholderData: keepPreviousData,
  });
  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-2xl font-semibold tracking-tight">Unanswered questions</h1>
      <p className="mt-1 max-w-[70ch] text-sm text-muted">
        Questions the bot couldn't answer. Add an answer and it's used for any question containing the same text, so the bot stops pausing on it.
      </p>
      <div className="mt-5">
        <FilterBar label="Filter questions">
          <TextFilter id="q-search" label="Search" value={filters.values.q} onChange={(v) => filters.setFilter("q", v)} width="w-64" />
        </FilterBar>
      </div>
      <div className="panel mt-4">
        {list.isPending && <p className="px-5 py-8 text-muted" role="status">Loading…</p>}
        {list.isError && (
          <p role="alert" className="px-5 py-8 text-danger">
            Couldn't load questions. {errorMessage(list.error)}
          </p>
        )}
        {list.data && list.data.items.length === 0 && (
          <p className="px-5 py-10 text-center text-muted">
            {filters.values.q ? "No questions match this search." : "No unanswered questions. The bot answered everything it saw."}
          </p>
        )}
        {list.data && list.data.items.length > 0 && (
          <ul>
            {list.data.items.map((q) => (
              <QuestionRow key={q.id} question={q} />
            ))}
          </ul>
        )}
        {list.data && <Pagination page={list.data.page} pageSize={list.data.page_size} total={list.data.total} onPage={filters.setPage} />}
      </div>
    </div>
  );
}
