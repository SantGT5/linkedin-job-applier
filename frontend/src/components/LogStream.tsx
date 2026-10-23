import { useEffect, useRef, useState } from "react";
import { LOG_STYLE, logKind } from "./logLine";

const MAX_LINES = 2000;

export default function LogStream({ runId }: { runId: number | null }) {
  const [lines, setLines] = useState<{ id: string; text: string }[]>([]);
  const [follow, setFollow] = useState(true);
  const [ended, setEnded] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLines([]);
    setEnded(false);
    if (runId === null) return;
    const source = new EventSource(`/api/runs/${runId}/logs/stream`);
    let counter = 0;
    source.onmessage = (event) => {
      const id = event.lastEventId || `l${counter++}`;
      setLines((current) => {
        const next = [...current, { id, text: event.data }];
        return next.length > MAX_LINES ? next.slice(next.length - MAX_LINES) : next;
      });
    };
    const onEnd = () => {
      setEnded(true);
      source.close();
    };
    source.addEventListener("end", onEnd);
    return () => {
      source.removeEventListener("end", onEnd);
      source.close();
    };
  }, [runId]);

  useEffect(() => {
    if (follow && box.current) box.current.scrollTop = box.current.scrollHeight;
  }, [lines, follow]);

  return (
    // Absolutely positioned content: the panel takes the row height set by the live browser
    // (and a fixed height when stacked), however long the log gets.
    <section aria-label="Run log" className="panel relative h-[420px] min-w-0 xl:h-auto">
      <div className="absolute inset-0 flex flex-col">
      <div className="flex items-center justify-between border-b border-line px-4 py-2">
        <h2 className="text-sm font-semibold">Log{runId !== null ? ` · run ${runId}` : ""}</h2>
        <button type="button" className="btn-ghost min-h-[32px] text-sm" aria-pressed={!follow} onClick={() => setFollow((f) => !f)}>
          {follow ? "Pause scroll" : "Follow log"}
        </button>
      </div>
      <div ref={box} role="log" aria-live="off" className="min-h-0 flex-1 overflow-auto rounded-b-lg bg-[#f6f7f5] px-4 py-3 font-mono text-[12.5px] leading-relaxed">
        {runId === null && <p className="font-sans text-sm text-muted">No runs yet. Press Start to begin; the log shows up here.</p>}
        {runId !== null && lines.length === 0 && !ended && <p className="font-sans text-sm text-muted">Waiting for output…</p>}
        {lines.map((line, i) => {
          // One blank line is enough between blocks.
          if (!line.text.trim()) return i > 0 && lines[i - 1].text.trim() ? <div key={line.id} className="h-2" /> : null;
          const kind = logKind(line.text);
          if (kind === "divider") return <hr key={line.id} className="my-2 border-line" />;
          return (
            <div key={line.id} data-kind={kind} className={`whitespace-pre-wrap break-words [overflow-wrap:anywhere] ${LOG_STYLE[kind]}`}>
              {line.text}
            </div>
          );
        })}
        {ended && <p className="mt-2 font-sans text-sm text-muted">End of this run's log.</p>}
      </div>
      </div>
    </section>
  );
}
