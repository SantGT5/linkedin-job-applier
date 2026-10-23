"""HR email addresses found in job descriptions (saved to the HR email list)."""

import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
TRAILING = ".,;:)>]"
ASSET_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")


def extract_emails(text: str | None) -> list[str]:
    """Lowercased addresses in order of appearance, without duplicates or image names like logo@2x.png."""
    found: list[str] = []
    for match in EMAIL_RE.findall(text or ""):
        email = match.rstrip(TRAILING).lower()
        if email.endswith(ASSET_SUFFIXES) or email in found:
            continue
        found.append(email)
    return found


def should_collect_emails(ai_filter_jobs: bool, match_score: int | None, min_score: int) -> bool:
    """Emails are saved for every job the bot applies to; only a real score below the threshold excludes one."""
    return not (ai_filter_jobs and match_score is not None and min_score > 0 and match_score < min_score)
