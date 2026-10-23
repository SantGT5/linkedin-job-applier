import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { ApiError, api, errorMessage } from "../../api/client";
import type { SettingsValues } from "../../api/types";
import Icon from "../Icon";
import { useToast } from "../Toast";
import { SECTION_LABELS, fieldLabel } from "./labels";

const EXPORT_FILENAME = "applier-settings.json";
const FILE_KEYS: Record<string, string> = { file: "File", version: "File version" };

/** "questions.desired_salary" -> "Questions › Desired salary". */
function errorLabel(key: string) {
  const [section, field] = key.split(".", 2);
  if (field && SECTION_LABELS[section]) return `${SECTION_LABELS[section]} › ${fieldLabel(field)}`;
  return FILE_KEYS[key] ?? (SECTION_LABELS[key] ? `${SECTION_LABELS[key]} section` : `“${key}”`);
}

function download(data: unknown) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2) + "\n"], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = EXPORT_FILENAME;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

/** Export every non-secret setting to a file, or import one (all or nothing). */
export default function SettingsTransfer() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const input = useRef<HTMLInputElement>(null);
  const [errors, setErrors] = useState<Record<string, string> | null>(null);

  const exportFile = useMutation({
    mutationFn: () => api<unknown>("/api/settings/export"),
    onSuccess: (data) => {
      download(data);
      toast(`Exported ${EXPORT_FILENAME}. Secrets stay in .env.`);
    },
    onError: (error) => toast(errorMessage(error), "error"),
  });

  const importFile = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api<SettingsValues>("/api/settings/import", { method: "POST", body: form });
    },
    onMutate: () => setErrors(null),
    onSuccess: (data) => {
      queryClient.setQueryData(["settings"], data);
      toast("Imported. Used on the next run.");
    },
    onError: (error) => {
      if (error instanceof ApiError && Object.keys(error.fieldErrors).length) setErrors(error.fieldErrors);
      else toast(errorMessage(error), "error");
    },
    onSettled: () => {
      if (input.current) input.current.value = "";
    },
  });

  return (
    <>
      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn-secondary" disabled={exportFile.isPending} onClick={() => exportFile.mutate()}>
          <Icon name="download" className="h-4 w-4" />
          {exportFile.isPending ? "Exporting…" : "Export settings"}
        </button>
        <label
          className={`btn-secondary cursor-pointer focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-pine ${
            importFile.isPending ? "pointer-events-none opacity-50" : ""
          }`}
        >
          <Icon name="upload" className="h-4 w-4" />
          {importFile.isPending ? "Importing…" : "Import settings"}
          <input
            ref={input}
            type="file"
            accept="application/json,.json"
            className="sr-only"
            disabled={importFile.isPending}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) importFile.mutate(file);
            }}
          />
        </label>
      </div>
      {errors && (
        <div role="alert" className="w-full rounded-lg border border-danger bg-danger-soft p-4 text-sm text-danger">
          <div className="flex items-start justify-between gap-3">
            <p className="font-semibold">Nothing was imported. Fix these in the file, then import it again:</p>
            <button type="button" className="btn-ghost -my-2 -mr-2 text-danger" onClick={() => setErrors(null)}>
              <Icon name="close" className="h-4 w-4" />
              Dismiss
            </button>
          </div>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {Object.entries(errors).map(([key, message]) => (
              <li key={key}>{`${errorLabel(key)}: ${message}`}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
