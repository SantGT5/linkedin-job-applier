// Plain-language names for setting keys (the keys keep the bot's original variable names).
const LABELS: Record<string, string> = {
  linkedIn: "LinkedIn profile URL",
  us_citizenship: "US citizenship / work authorization",
  current_ctc: "Current CTC",
  linkedin_headline: "LinkedIn headline",
  linkedin_summary: "LinkedIn summary",
  user_information_all: "About you (for the AI)",
  custom_answers: "Your answers",
  easy_apply_only: "Easy Apply only",
  under_10_applicants: "Under 10 applicants only",
  about_company_bad_words: "Skip companies mentioning",
  about_company_good_words: "Unless the company mentions",
  bad_words: "Skip jobs mentioning",
  did_masters: "I have a Master's degree",
  security_clearance: "I have a security clearance",
  current_experience: "Max years of experience required",
  ai_filter_jobs: "Let the AI skip poor fits",
  ai_min_match_score: "Minimum AI match score",
  connect_hr: "Connect with HR",
  run_non_stop: "Run non-stop",
  showAiErrorAlerts: "Pause on AI errors",
  use_AI: "Use AI",
  ai_provider: "AI provider",
  claude_model: "Claude model",
  glm_model: "GLM model",
  glm_reasoning_effort: "GLM reasoning effort",
  glm_api_url: "GLM API URL",
  my_name: "Your name",
  linkedin_profile: "LinkedIn profile",
  subject_template: "Subject",
  body_template: "Body",
  click_gap: "Max seconds between clicks",
  post_submit_timeout: "Seconds to wait after submitting",
};

export function fieldLabel(key: string): string {
  if (LABELS[key]) return LABELS[key];
  const words = key.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/_/g, " ").toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export const SECTION_LABELS: Record<string, string> = {
  personals: "Personal",
  questions: "Questions",
  search: "Search",
  settings: "Bot",
  ai: "AI",
  email: "Email",
};
