import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, errorMessage } from "../api/client";
import type { Composed, HrEmail } from "../api/types";
import { copyRich, copyText } from "./clipboard";
import Icon from "./Icon";
import Modal from "./Modal";

function CopyButton({ label, onCopy }: { label: string; onCopy: () => Promise<void> }) {
  const [state, setState] = useState<"idle" | "done" | "failed">("idle");
  return (
    <button
      type="button"
      className="btn-secondary min-h-[36px] shrink-0"
      aria-label={label}
      onClick={() =>
        onCopy()
          .then(() => setState("done"))
          .catch(() => setState("failed"))
      }
    >
      <Icon name={state === "done" ? "check" : "copy"} className="h-4 w-4" />
      {state === "done" ? "Copied" : state === "failed" ? "Copy failed" : "Copy"}
    </button>
  );
}

export default function CopyEmailModal({ email, onClose }: { email: HrEmail; onClose: () => void }) {
  const composed = useQuery({ queryKey: ["compose", email.id], queryFn: () => api<Composed>(`/api/emails/${email.id}/compose`) });
  const c = composed.data;
  return (
    <Modal title={`Email to ${email.email}`} onClose={onClose}>
      <div className="flex items-center justify-between border-b border-line px-5 py-3">
        <p className="font-semibold" aria-hidden="true">
          Email for {email.title ?? "this job"}
        </p>
        <button type="button" className="btn-ghost" aria-label="Close" onClick={onClose}>
          <Icon name="close" />
        </button>
      </div>
      {composed.isPending && <p className="px-5 py-8 text-muted">Composing…</p>}
      {composed.isError && (
        <p role="alert" className="px-5 py-8 text-danger">
          Couldn't compose the email. {errorMessage(composed.error)}
        </p>
      )}
      {c && (
        <dl className="divide-y divide-line">
          <div className="flex items-start gap-4 px-5 py-3">
            <dt className="w-16 shrink-0 pt-2 text-sm text-muted">To</dt>
            <dd className="min-w-0 flex-1 pt-2 [overflow-wrap:anywhere]">{c.to}</dd>
            <CopyButton label="Copy recipient" onCopy={() => copyText(c.to)} />
          </div>
          <div className="flex items-start gap-4 px-5 py-3">
            <dt className="w-16 shrink-0 pt-2 text-sm text-muted">Subject</dt>
            <dd className="min-w-0 flex-1 pt-2">{c.subject}</dd>
            <CopyButton label="Copy subject" onCopy={() => copyText(c.subject)} />
          </div>
          <div className="flex items-start gap-4 px-5 py-3">
            <dt className="w-16 shrink-0 pt-2 text-sm text-muted">Body</dt>
            {/* body_html is escaped server-side; it only contains <a> and <br>. */}
            <dd className="min-w-0 flex-1 pt-2 leading-relaxed [&_a]:text-pine [&_a]:underline" dangerouslySetInnerHTML={{ __html: c.body_html }} />
            <CopyButton label="Copy body" onCopy={() => copyRich(c.body_html, c.body_text)} />
          </div>
        </dl>
      )}
      <div className="flex justify-end border-t border-line px-5 py-3">
        <button type="button" className="btn-primary" onClick={onClose}>
          Done
        </button>
      </div>
    </Modal>
  );
}
