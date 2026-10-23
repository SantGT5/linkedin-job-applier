"""Composes the follow-up email for an HR address (copied by the owner, never sent by the app)."""

import html
import re
from dataclasses import asdict, dataclass

LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
SAFE_URL_RE = re.compile(r"^(https?://|mailto:)", re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


@dataclass(frozen=True)
class Composed:
    to: str
    subject: str
    body_text: str
    body_html: str

    def to_dict(self) -> dict:
        return asdict(self)


class _Values(dict):
    """Leaves unknown placeholders like {nope} untouched."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _drop_empty_lines(template: str, values: dict[str, str]) -> str:
    """Drops lines made only of placeholders that are all empty, e.g. an unfilled phone number."""
    kept = []
    for line in template.split("\n"):
        names = PLACEHOLDER_RE.findall(line)
        only_placeholders = names and not PLACEHOLDER_RE.sub("", line).strip()
        if only_placeholders and all(name in values and not values[name].strip() for name in names):
            continue
        kept.append(line)
    return "\n".join(kept)


def _fill(template: str, values: dict[str, str]) -> str:
    template = _drop_empty_lines(template, values)
    try:
        return template.format_map(_Values(values))
    except (ValueError, IndexError):
        # Stray braces in a hand-edited template: substitute what we can, literally.
        for key, value in values.items():
            template = template.replace("{" + key + "}", value)
        return template


def _to_html(text: str) -> str:
    parts, last = [], 0
    for match in LINK_RE.finditer(text):
        parts.append(html.escape(text[last:match.start()]))
        label, url = match.group(1), match.group(2)
        if SAFE_URL_RE.match(url):
            parts.append(f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>')
        else:
            parts.append(html.escape(match.group(0)))
        last = match.end()
    parts.append(html.escape(text[last:]))
    return "".join(parts).replace("\r\n", "\n").replace("\n", "<br>")


def _to_text(text: str) -> str:
    return LINK_RE.sub(lambda m: f"{m.group(1)} ({m.group(2)})" if SAFE_URL_RE.match(m.group(2)) else m.group(0), text)


def compose(email_row: dict, email_settings: dict) -> Composed:
    values = {
        "hr_email": email_row.get("email") or "",
        "job_title": email_row.get("title") or "",
        "job_url": email_row.get("job_link") or "",
        "my_name": email_settings.get("my_name") or "",
        "phone_number": email_settings.get("phone_number") or "",
        "linkedin_profile": email_settings.get("linkedin_profile") or "",
    }
    subject = _fill(email_settings.get("subject_template") or "", values)
    body = _fill(email_settings.get("body_template") or "", values)
    return Composed(to=values["hr_email"], subject=subject, body_text=_to_text(body), body_html=_to_html(body))
