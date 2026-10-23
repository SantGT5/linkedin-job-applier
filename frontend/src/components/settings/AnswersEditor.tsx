export interface Answer {
  match: string;
  answer: string;
}

export default function AnswersEditor({ id, value, onChange }: { id: string; value: Answer[]; onChange: (value: Answer[]) => void }) {
  const update = (i: number, patch: Partial<Answer>) => onChange(value.map((row, j) => (j === i ? { ...row, ...patch } : row)));
  return (
    <div id={id} className="flex flex-col gap-2">
      {value.length === 0 && <p className="text-sm text-muted">No answers yet. Questions the bot couldn't answer show up under Questions.</p>}
      {value.map((row, i) => (
        <div key={i} className="grid grid-cols-[1fr_1fr_auto] items-end gap-2">
          <div>
            <label className="label" htmlFor={`${id}-match-${i}`}>
              When the question contains
            </label>
            <input id={`${id}-match-${i}`} className="field" value={row.match} onChange={(e) => update(i, { match: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor={`${id}-answer-${i}`}>
              Answer
            </label>
            <input id={`${id}-answer-${i}`} className="field" value={row.answer} onChange={(e) => update(i, { answer: e.target.value })} />
          </div>
          <button
            type="button"
            className="btn-ghost"
            aria-label={`Remove answer for ${row.match || "empty row"}`}
            onClick={() => onChange(value.filter((_, j) => j !== i))}
          >
            Remove
          </button>
        </div>
      ))}
      <div>
        <button type="button" className="btn-secondary" onClick={() => onChange([...value, { match: "", answer: "" }])}>
          Add answer
        </button>
      </div>
    </div>
  );
}
