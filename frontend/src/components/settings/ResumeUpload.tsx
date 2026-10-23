import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { api, errorMessage } from "../../api/client";
import type { ResumeInfo } from "../../api/types";
import { formatSize } from "../format";
import { useToast } from "../Toast";

export default function ResumeUpload() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const input = useRef<HTMLInputElement>(null);
  const resume = useQuery({ queryKey: ["resume"], queryFn: () => api<ResumeInfo>("/api/resume") });
  const upload = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api<ResumeInfo>("/api/resume", { method: "POST", body: form });
    },
    onSuccess: (data) => {
      queryClient.setQueryData(["resume"], data);
      toast("Resume uploaded. Used on the next run.");
    },
    onSettled: () => {
      if (input.current) input.current.value = "";
    },
  });

  return (
    <section className="panel p-5" aria-labelledby="resume-heading">
      <h2 id="resume-heading" className="text-lg font-semibold">
        Resume
      </h2>
      <p className="mt-1 text-sm text-muted">Uploaded to every Easy Apply. Recruiters see its file name.</p>
      <p className="mt-3 text-sm" role="status">
        {resume.isPending && "Loading…"}
        {resume.data?.exists &&
          `${resume.data.filename} · ${formatSize(resume.data.size ?? 0)} · uploaded ${new Date(resume.data.uploaded_at ?? "").toLocaleDateString()}`}
        {resume.data && !resume.data.exists && "No resume yet: the bot keeps whatever you last uploaded on LinkedIn."}
      </p>
      <label htmlFor="resume-file" className="label mt-4">
        Upload a new resume (PDF, DOC or DOCX, up to 2 MB)
      </label>
      <input
        ref={input}
        id="resume-file"
        type="file"
        accept=".pdf,.doc,.docx"
        disabled={upload.isPending}
        aria-describedby={upload.isError ? "resume-error" : undefined}
        className="block text-sm file:mr-3 file:rounded file:border file:border-control file:bg-surface file:px-3 file:py-2 file:text-sm file:text-ink hover:file:bg-ground"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) upload.mutate(file);
        }}
      />
      {upload.isPending && <p className="mt-2 text-sm text-muted">Uploading…</p>}
      {upload.isError && (
        <p id="resume-error" role="alert" className="mt-2 text-sm text-danger">
          {errorMessage(upload.error)}
        </p>
      )}
    </section>
  );
}
