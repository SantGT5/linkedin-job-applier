import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { Composed } from "../../api/types";

/** Preview of the follow-up email with the unsaved templates, on a sample job. */
export default function EmailPreview({ values }: { values: Record<string, unknown> }) {
  const [debounced, setDebounced] = useState(values);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(values), 400);
    return () => clearTimeout(timer);
  }, [values]);
  const preview = useQuery({
    queryKey: ["email-preview", debounced],
    queryFn: () =>
      api<Composed>("/api/emails/preview", {
        method: "POST",
        body: {
          subject_template: debounced.subject_template ?? "",
          body_template: debounced.body_template ?? "",
          my_name: debounced.my_name ?? "",
          phone_number: debounced.phone_number ?? "",
          linkedin_profile: debounced.linkedin_profile ?? "",
        },
      }),
    placeholderData: (previous) => previous,
  });
  return (
    <aside aria-label="Email preview" className="rounded-lg border border-line bg-ground p-4">
      <h3 className="text-sm font-semibold">Preview with a sample job</h3>
      {preview.data && (
        <div className="mt-3 text-sm">
          <p>
            <span className="text-muted">To </span>
            {preview.data.to}
          </p>
          <p className="mt-1">
            <span className="text-muted">Subject </span>
            {preview.data.subject}
          </p>
          {/* body_html is built server-side from escaped text; only <a> and <br> are produced. */}
          <div className="mt-3 max-w-[70ch] leading-relaxed [&_a]:text-pine [&_a]:underline" dangerouslySetInnerHTML={{ __html: preview.data.body_html }} />
        </div>
      )}
      {preview.isError && <p className="mt-2 text-sm text-danger">Preview unavailable.</p>}
    </aside>
  );
}
