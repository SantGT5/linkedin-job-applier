export type FieldType = "str" | "text" | "int" | "bool" | "list" | "enum" | "multi_enum" | "answers";

export interface SchemaField {
  section: string;
  key: string;
  type: FieldType;
  default: unknown;
  options: string[] | null;
  help: string;
  min: number | null;
  max: number | null;
}

export type SettingsValues = Record<string, Record<string, unknown>>;

export interface Secret {
  name: string;
  env_var: string;
  set: boolean;
}

export interface Run {
  id: number;
  status: "queued" | "running" | "waiting" | "stopping" | "finished" | "failed" | "stopped";
  started_at: string;
  ended_at: string | null;
  error: string | null;
  applied_count: number;
  failed_count: number;
  skipped_count: number;
}

export interface Prompt {
  id: number;
  title: string;
  text: string;
  buttons: string[];
}

export interface BotStatus {
  state: "idle" | "queued" | "running" | "waiting" | "stopping";
  run: Run | null;
  prompt: Prompt | null;
  linkedin_session: { state: "logged_in" | "logged_out" | "unknown"; checked_at: string | null };
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface AppliedJob {
  job_id: string;
  title: string | null;
  company: string | null;
  work_location: string | null;
  work_style: string | null;
  date_applied: string | null;
  date_posted: string | null;
  job_link: string | null;
  external_job_link: string | null;
  hr_name: string | null;
  hr_link: string | null;
  resume: string | null;
}

export interface FailedJob {
  id: number;
  job_id: string;
  job_link: string | null;
  date_tried: string | null;
  assumed_reason: string | null;
  external_job_link: string | null;
}

export interface HrEmail {
  id: number;
  email: string;
  job_id: string;
  title: string | null;
  company: string | null;
  job_link: string | null;
  email_subject: string | null;
  status: "new" | "emailed";
  found_at: string;
  emailed_at: string | null;
}

export interface Composed {
  to: string;
  subject: string;
  body_text: string;
  body_html: string;
}

export interface UnansweredQuestion {
  id: number;
  label: string;
  question_type: string;
  options: string[] | null;
  job_id: string | null;
  seen_count: number;
  last_seen: string;
}

export interface ResumeInfo {
  exists: boolean;
  filename?: string;
  size?: number;
  uploaded_at?: string;
}
