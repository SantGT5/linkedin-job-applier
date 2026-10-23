import { useQuery } from "@tanstack/react-query";
import { useState, type KeyboardEvent } from "react";
import { api, errorMessage } from "../api/client";
import type { SchemaField, SettingsValues } from "../api/types";
import ResumeUpload from "../components/settings/ResumeUpload";
import SecretsPanel from "../components/settings/SecretsPanel";
import SectionForm from "../components/settings/SectionForm";
import SettingsTransfer from "../components/settings/SettingsTransfer";
import { SECTION_LABELS } from "../components/settings/labels";

const TABS = [...Object.keys(SECTION_LABELS), "secrets"];
const tabLabel = (tab: string) => (tab === "secrets" ? "Secrets & resume" : SECTION_LABELS[tab]);

export default function Settings() {
  const [tab, setTab] = useState("personals");
  const schema = useQuery({ queryKey: ["settings-schema"], queryFn: () => api<SchemaField[]>("/api/settings/schema"), staleTime: Infinity });
  const values = useQuery({ queryKey: ["settings"], queryFn: () => api<SettingsValues>("/api/settings") });

  function onKey(event: KeyboardEvent) {
    const i = TABS.indexOf(tab);
    const next = event.key === "ArrowRight" ? TABS[(i + 1) % TABS.length] : event.key === "ArrowLeft" ? TABS[(i - 1 + TABS.length) % TABS.length] : null;
    if (next) {
      setTab(next);
      document.getElementById(`tab-${next}`)?.focus();
    }
  }

  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
          <p className="mt-1 text-sm text-muted">
            Everything the bot uses. Saved changes apply to the next run. Export and import copy every setting except secrets.
          </p>
        </div>
        <SettingsTransfer />
      </div>
      <div role="tablist" aria-label="Settings sections" className="mt-5 flex flex-wrap gap-1 border-b border-line" onKeyDown={onKey}>
        {TABS.map((t) => (
          <button
            key={t}
            id={`tab-${t}`}
            role="tab"
            type="button"
            aria-selected={tab === t}
            aria-controls={`panel-${t}`}
            tabIndex={tab === t ? 0 : -1}
            onClick={() => setTab(t)}
            className={`-mb-px min-h-[40px] border-b-2 px-4 text-sm transition-colors duration-150 ${
              tab === t ? "border-pine font-semibold text-ink" : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {tabLabel(t)}
          </button>
        ))}
      </div>
      <div id={`panel-${tab}`} role="tabpanel" aria-labelledby={`tab-${tab}`} className="mt-5">
        {tab === "secrets" ? (
          <div className="grid gap-5 lg:grid-cols-2">
            <SecretsPanel />
            <ResumeUpload />
          </div>
        ) : schema.isPending || values.isPending ? (
          <p className="panel px-5 py-10 text-muted" role="status">
            Loading settings…
          </p>
        ) : schema.isError || values.isError ? (
          <p role="alert" className="panel p-5 text-danger">
            Couldn't load settings. {errorMessage(schema.error ?? values.error)}
          </p>
        ) : (
          <SectionForm
            key={tab}
            section={tab}
            fields={schema.data.filter((f) => f.section === tab)}
            saved={values.data[tab] ?? {}}
          />
        )}
      </div>
    </div>
  );
}
