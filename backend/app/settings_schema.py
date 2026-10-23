"""Every bot setting the UI can edit: name, type, default, options and help text.

The bot's `config/*.py` modules read these values (see `bot/config/_loader.py`), so
names and sections match the original `config/*.py` files. Secrets are not here:
they live in `.env` only (see `SECRET_ENV`).
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
from typing import Any, Literal

FieldType = Literal["str", "text", "int", "bool", "list", "enum", "multi_enum", "answers"]

SECTIONS = ("personals", "questions", "search", "settings", "ai", "email")

# Bot variable name -> environment variable holding it.
SECRET_ENV: dict[str, str] = {
    "username": "LINKEDIN_USERNAME",
    "password": "LINKEDIN_PASSWORD",
    "claude_api_key": "CLAUDE_API_KEY",
    "glm_api_key": "GLM_API_KEY",
}


class SettingsError(ValueError):
    def __init__(self, field_errors: dict[str, str]):
        super().__init__("; ".join(f"{k}: {v}" for k, v in field_errors.items()))
        self.field_errors = field_errors


@dataclass(frozen=True)
class Field:
    section: str
    key: str
    type: FieldType
    default: Any
    options: list[str] | None
    help: str
    min: int | None = None
    max: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_BODY_TEMPLATE = """Hi,

Hope this message finds you well.

I came across the [{job_title}]({job_url}) role and I'd love to be considered,

I've attached my CV for your review,

Thank you for your time,

Best regards,
{my_name}
{phone_number}
{linkedin_profile}"""

EMAIL_PLACEHOLDERS = "{hr_email}, {job_title}, {job_url}, {my_name}, {phone_number}, {linkedin_profile}"

YES_NO_DECLINE = ["Yes", "No", "Decline"]
ETHNICITY = [
    "", "Decline", "Hispanic/Latino", "American Indian or Alaska Native", "Asian",
    "Black or African American", "Native Hawaiian or Other Pacific Islander", "White", "Other",
]
US_CITIZENSHIP = [
    "U.S. Citizen/Permanent Resident", "Non-citizen allowed to work for any employer",
    "Non-citizen allowed to work for current employer", "Non-citizen seeking work authorization",
    "Canadian Citizen/Permanent Resident", "Other",
]
SALARY = [
    "", "$40,000+", "$60,000+", "$80,000+", "$100,000+", "$120,000+", "$140,000+",
    "$160,000+", "$180,000+", "$200,000+",
]


def _f(section, key, type_, default, help_, options=None, min_=None, max_=None) -> Field:
    return Field(section, key, type_, default, options, help_, min_, max_)


P, Q, S, T, A, E = SECTIONS

SCHEMA: list[Field] = [
    # personals
    _f(P, "first_name", "str", "", "Your first (legal) name.", min_=1),
    _f(P, "middle_name", "str", "", "Middle name, or empty."),
    _f(P, "last_name", "str", "", "Your last name.", min_=1),
    _f(P, "phone_number", "str", "", "Phone number (required), make sure it's valid.", min_=10),
    _f(P, "current_city", "str", "", "Your current city, e.g. Los Angeles."),
    _f(P, "street", "str", "", "Street address (some applications require it)."),
    _f(P, "state", "str", "", "State / province."),
    _f(P, "zipcode", "str", "", "Zip / postal code."),
    _f(P, "country", "str", "", "Country."),
    _f(P, "ethnicity", "enum", "Decline", "Ethnicity or race (US equal opportunity). Empty = don't answer.", ETHNICITY),
    _f(P, "gender", "enum", "Decline", "How do you identify? Empty = don't answer.", ["Male", "Female", "Other", "Decline", ""]),
    _f(P, "disability_status", "enum", "Decline", "Disability status.", YES_NO_DECLINE),
    _f(P, "veteran_status", "enum", "Decline", "Veteran status.", YES_NO_DECLINE),
    # questions
    _f(Q, "years_of_experience", "str", "0", "Answer for 'years of experience' questions (a number, e.g. \"7\")."),
    _f(Q, "require_visa", "enum", "No", "Do you require visa sponsorship?", ["Yes", "No"]),
    _f(Q, "website", "str", "", "Portfolio website link, or empty to leave unanswered."),
    _f(Q, "linkedIn", "str", "", "Link to your LinkedIn profile."),
    _f(Q, "us_citizenship", "enum", "Other", "Citizenship / work authorization status.", US_CITIZENSHIP),
    _f(Q, "desired_salary", "int", 0, "Desired salary / expected CTC, numbers only. 'lakhs' and monthly variants are derived.", min_=0),
    _f(Q, "current_ctc", "int", 0, "Current CTC, numbers only.", min_=0),
    _f(Q, "hourly_rate", "int", 0, "Expected hourly rate, numbers only.", min_=0),
    _f(Q, "notice_period", "int", 0, "Notice period in days (weeks/months are derived).", min_=0),
    _f(Q, "linkedin_headline", "str", "", "Your LinkedIn headline, or empty to leave unanswered."),
    _f(Q, "linkedin_summary", "text", "", "Your LinkedIn summary, or empty to leave unanswered."),
    _f(Q, "cover_letter", "text", "", "Your cover letter, or empty to leave unanswered."),
    _f(Q, "user_information_all", "text", "", "Everything about you (resume, skills, location...). Used by the AI to answer questions and score job fit."),
    _f(Q, "recent_employer", "str", "", "Name of your most recent employer."),
    _f(Q, "confidence_level", "str", "8", "Answer for 'on a scale of 1-10' questions (1-10)."),
    _f(Q, "pause_before_submit", "bool", True, "Pause before every Submit so you can check the application in the live browser."),
    _f(Q, "pause_at_failed_question", "bool", True, "Pause when the bot can't answer a question (otherwise it answers randomly)."),
    _f(Q, "overwrite_previous_answers", "bool", False, "Overwrite answers LinkedIn pre-filled from previous applications."),
    _f(Q, "custom_answers", "answers", [], "Your own answers: when a question's label contains 'match' (case-insensitive), the bot answers 'answer'. Checked before built-in and AI answers."),
    # search
    _f(S, "search_terms", "list", ["Software Engineer"], "Job titles searched on LinkedIn, one per entry.", min_=1),
    _f(S, "search_location", "str", "United States", "Search location, e.g. United States, European Union, Worldwide. Empty = don't set."),
    _f(S, "switch_number", "int", 30, "Switch to the next search term after this many applications.", min_=1),
    _f(S, "applications_before_search_prompt", "int", 5, "After this many applications for a term, ask whether to move on. -1 or 0 disables.", min_=-1),
    _f(S, "randomize_search_order", "bool", False, "Randomize the order of search terms."),
    _f(S, "sort_by", "enum", "", "Sort results by.", ["", "Most recent", "Most relevant"]),
    _f(S, "date_posted", "enum", "Past 24 hours", "Date posted filter.", ["", "Any time", "Past month", "Past week", "Past 24 hours"]),
    _f(S, "salary", "enum", "", "Minimum salary filter.", SALARY),
    _f(S, "easy_apply_only", "bool", True, "Only show Easy Apply jobs."),
    _f(S, "experience_level", "multi_enum", [], "Experience level filter.", ["Internship", "Entry level", "Associate", "Mid-Senior level", "Director", "Executive"]),
    _f(S, "job_type", "multi_enum", [], "Job type filter.", ["Full-time", "Part-time", "Contract", "Temporary", "Volunteer", "Internship", "Other"]),
    _f(S, "on_site", "multi_enum", [], "On-site / remote / hybrid filter.", ["On-site", "Remote", "Hybrid"]),
    _f(S, "companies", "list", [], "Company filter (names must match LinkedIn exactly). Not supported by LinkedIn's new search."),
    _f(S, "location", "list", [], "Location filter. Not supported by LinkedIn's new search."),
    _f(S, "industry", "list", [], "Industry filter. Not supported by LinkedIn's new search."),
    _f(S, "job_function", "list", [], "Job function filter. Not supported by LinkedIn's new search."),
    _f(S, "job_titles", "list", [], "Job titles filter. Not supported by LinkedIn's new search."),
    _f(S, "benefits", "list", [], "Benefits filter. Not supported by LinkedIn's new search."),
    _f(S, "commitments", "list", [], "Commitments filter. Not supported by LinkedIn's new search."),
    _f(S, "under_10_applicants", "bool", False, "Only jobs with under 10 applicants."),
    _f(S, "in_your_network", "bool", False, "Only jobs in your network."),
    _f(S, "fair_chance_employer", "bool", False, "Fair chance employers only. Not supported by LinkedIn's new search."),
    _f(S, "pause_after_filters", "bool", True, "Pause after the search loads so you can check results and filters in the live browser."),
    _f(S, "about_company_bad_words", "list", [], "Skip companies whose name or 'About' section contains any of these."),
    _f(S, "about_company_good_words", "list", [], "Exceptions: don't skip companies containing these, even if a bad word matches."),
    _f(S, "bad_words", "list", [], "Skip jobs whose description contains any of these (case-insensitive)."),
    _f(S, "security_clearance", "bool", False, "Do you have an active security clearance?"),
    _f(S, "did_masters", "bool", False, "Do you have a Master's degree? Allows jobs asking for it within current_experience + 2 years."),
    _f(S, "current_experience", "int", -1, "Skip jobs requiring more years than this. -1 = apply to all.", min_=-1),
    _f(S, "ai_filter_jobs", "bool", True, "Let the AI score each job and skip those below the minimum score."),
    _f(S, "ai_min_match_score", "int", 50, "Minimum AI match score (0-100) to apply. 0 = score but never skip.", min_=0, max_=100),
    # settings
    _f(T, "close_tabs", "bool", True, "Close external application tabs."),
    _f(T, "follow_companies", "bool", False, "Follow companies you Easy Apply to (otherwise the 'Follow' box is unticked before Submit)."),
    _f(T, "connect_hr", "bool", True, "Send connection requests to HR (in development)."),
    _f(T, "connect_request_message", "text", "", "Connection request message (max 200 characters). Empty = no note."),
    _f(T, "run_non_stop", "bool", False, "Keep running until you stop it."),
    _f(T, "alternate_sortby", "bool", True, "Alternate sort order between cycles (non-stop mode)."),
    _f(T, "cycle_date_posted", "bool", True, "Cycle the date-posted filter between cycles (non-stop mode)."),
    _f(T, "stop_date_cycle_at_24hr", "bool", True, "Stop the date-posted cycle at 'Past 24 hours'."),
    _f(T, "click_gap", "int", 1, "Max seconds to wait between clicks.", min_=0),
    _f(T, "post_submit_timeout", "int", 10, "Extra seconds to wait after a successful submit.", min_=0),
    _f(T, "run_in_background", "bool", False, "Headless Chrome (the live view will be blank; disables pauses)."),
    _f(T, "disable_extensions", "bool", False, "Disable Chrome extensions."),
    _f(T, "safe_mode", "bool", False, "Use a throwaway guest profile instead of the saved Chrome profile (you'll need to log in every run)."),
    _f(T, "smooth_scroll", "bool", False, "Smooth scrolling (slower)."),
    _f(T, "stealth_mode", "bool", True, "Use undetected-chromedriver to avoid anti-bot checks."),
    _f(T, "showAiErrorAlerts", "bool", False, "Pause and show AI connection errors."),
    # ai
    _f(A, "use_AI", "bool", False, "Use AI to score jobs, extract skills and answer questions."),
    _f(A, "ai_provider", "enum", "claude", "AI provider.", ["claude", "glm"]),
    _f(A, "claude_model", "str", "claude-sonnet-4-6", "Claude model, e.g. claude-opus-4-8, claude-sonnet-4-6, claude-haiku-4-5."),
    _f(A, "glm_model", "str", "glm-4.6", "GLM model, e.g. glm-4.6, glm-4.5-air, glm-4.5-flash."),
    _f(A, "glm_reasoning_effort", "enum", "high", "How hard GLM thinks. 'none' turns thinking off (older models).", ["low", "high", "max", "none"]),
    _f(A, "glm_api_url", "str", "https://api.z.ai/api/paas/v4/", "GLM OpenAI-compatible base URL (keep the trailing slash). China: https://open.bigmodel.cn/api/paas/v4/"),
    # email
    _f(E, "my_name", "str", "", "Your name, used as {my_name} in the email templates, e.g. Jane Doe."),
    _f(E, "phone_number", "str", "", "Your phone number, used as {phone_number}, e.g. +1 555 0100. Empty = left out."),
    _f(E, "linkedin_profile", "str", "", "Your LinkedIn profile, used as {linkedin_profile}, e.g. linkedin.com/in/janedoe or [linkedin.com/in/janedoe](https://linkedin.com/in/janedoe) for a link. Empty = left out."),
    _f(E, "subject_template", "str", "{job_title} - {my_name}", f"Email subject. Placeholders: {EMAIL_PLACEHOLDERS}.", min_=1),
    _f(E, "body_template", "text", DEFAULT_BODY_TEMPLATE, f"Email body. Placeholders: {EMAIL_PLACEHOLDERS}. [text](url) becomes a link; a line left empty by its placeholders is dropped.", min_=1),
]

FIELDS: dict[tuple[str, str], Field] = {(f.section, f.key): f for f in SCHEMA}


def defaults() -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {section: {} for section in SECTIONS}
    for field in SCHEMA:
        values[field.section][field.key] = copy.deepcopy(field.default)
    return values


def _coerce(field: Field, value: Any) -> Any:
    """Returns the value converted to the field's type, or raises ValueError with a message."""
    t = field.type
    if t in ("str", "text"):
        if not isinstance(value, str):
            raise ValueError("must be text")
        if field.min and len(value.strip()) < field.min:
            raise ValueError(f"must be at least {field.min} characters")
        return value
    if t == "int":
        if isinstance(value, bool):
            raise ValueError("must be a whole number")
        if isinstance(value, str):
            text = value.strip().replace("_", "").replace(",", "")
            if not text.lstrip("-").isdigit():
                raise ValueError("must be a whole number")
            value = int(text)
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        if not isinstance(value, int):
            raise ValueError("must be a whole number")
        if field.min is not None and value < field.min:
            raise ValueError(f"must be at least {field.min}")
        if field.max is not None and value > field.max:
            raise ValueError(f"must be at most {field.max}")
        return value
    if t == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in ("true", "false"):
            return value.lower() == "true"
        raise ValueError("must be true or false")
    if t == "enum":
        if value not in (field.options or []):
            raise ValueError(f"must be one of {field.options}")
        return value
    if t in ("list", "multi_enum"):
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ValueError("must be a list of text values")
        items = [v.strip() for v in value if v.strip()]
        if t == "multi_enum":
            bad = [v for v in items if v not in (field.options or [])]
            if bad:
                raise ValueError(f"{bad} not in {field.options}")
        if field.min and len(items) < field.min:
            raise ValueError(f"needs at least {field.min} entr{'y' if field.min == 1 else 'ies'}")
        return items
    if t == "answers":
        if not isinstance(value, list):
            raise ValueError("must be a list of {match, answer}")
        out = []
        for item in value:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("match"), str)
                or not isinstance(item.get("answer"), str)
                or not item["match"].strip()
            ):
                raise ValueError("each entry needs a non-empty 'match' and an 'answer'")
            out.append({"match": item["match"].strip(), "answer": item["answer"]})
        return out
    raise ValueError(f"unknown type {t}")


def validate(section: str, values: dict) -> dict:
    """Validates (a subset of) one section's values. Returns the coerced values.

    Raises SettingsError naming every bad field; nothing is partially accepted.
    """
    if section not in SECTIONS:
        raise SettingsError({"section": f"unknown section '{section}'"})
    if not isinstance(values, dict):
        raise SettingsError({"section": "values must be an object"})
    errors: dict[str, str] = {}
    out: dict[str, Any] = {}
    for key, value in values.items():
        field = FIELDS.get((section, key))
        if field is None:
            errors[key] = f"unknown setting in '{section}'"
            continue
        try:
            out[key] = _coerce(field, value)
        except ValueError as e:
            errors[key] = str(e)
    if errors:
        raise SettingsError(errors)
    return out
