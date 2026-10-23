import { useMutation, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { useState } from "react";
import { api, errorMessage } from "../api/client";
import Icon from "./Icon";
import Modal from "./Modal";
import { useToast } from "./Toast";

/** "1 email", "3 emails". */
function count(n: number, [one, many]: [string, string]) {
  return `${n} ${n === 1 ? one : many}`;
}

/**
 * Selected rows and their deletion: `bar` goes in DataTable's `toolbar`, `dialog` anywhere.
 * Deleting asks first, then posts `{ids}` to `endpoint` and refreshes `invalidate`.
 */
export function useBulkDelete<K extends string | number>({ endpoint, noun, note, invalidate, onDeleted }: {
  endpoint: string;
  noun: [string, string];
  /** What deleting means beyond losing the rows, shown in the confirmation. */
  note?: string;
  invalidate: QueryKey[];
  /** After a delete, with how many rows went (e.g. to step back from an emptied last page). */
  onDeleted?: (deleted: number) => void;
}) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [selected, setSelected] = useState<Set<K>>(new Set());
  const [confirming, setConfirming] = useState(false);

  const remove = useMutation({
    mutationFn: (ids: K[]) => api<{ deleted: number }>(endpoint, { method: "POST", body: { ids } }),
    onSuccess: ({ deleted }) => {
      setConfirming(false);
      setSelected(new Set());
      toast(`Deleted ${count(deleted, noun)}.`);
      for (const key of invalidate) void queryClient.invalidateQueries({ queryKey: key });
      onDeleted?.(deleted);
    },
    onError: (e) => toast(`Couldn't delete. ${errorMessage(e)}`, "error"),
  });

  const n = selected.size;
  const bar =
    n > 0 ? (
      <div role="toolbar" aria-label="Selected rows" className="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-pine-soft px-4 py-2 text-sm">
        <span className="font-medium tabular-nums">{count(n, noun)} selected</span>
        <div className="flex gap-2">
          <button type="button" className="btn-ghost min-h-[36px]" onClick={() => setSelected(new Set())}>
            Clear selection
          </button>
          <button type="button" className="btn-danger min-h-[36px]" onClick={() => setConfirming(true)}>
            <Icon name="trash" className="h-4 w-4" />
            Delete selected
          </button>
        </div>
      </div>
    ) : null;

  const dialog = confirming ? (
    <Modal title={`Delete ${count(n, noun)}?`} role="alertdialog" onClose={() => !remove.isPending && setConfirming(false)} width="max-w-md">
      <div className="px-5 py-5">
        <p className="text-lg font-semibold" aria-hidden="true">
          Delete {count(n, noun)}?
        </p>
        <p className="mt-1 text-sm text-muted">This can't be undone.{note ? ` ${note}` : ""}</p>
        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={() => setConfirming(false)} disabled={remove.isPending}>
            Cancel
          </button>
          <button type="button" className="btn-danger" onClick={() => remove.mutate([...selected])} disabled={remove.isPending}>
            {remove.isPending ? "Deleting…" : `Delete ${count(n, noun)}`}
          </button>
        </div>
      </div>
    </Modal>
  ) : null;

  return { selection: { selected, onChange: setSelected }, clear: () => setSelected(new Set()), bar, dialog };
}
