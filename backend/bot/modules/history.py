"""Application history, saved to the app database through the bridge (was CSV files)."""

from datetime import datetime
from typing import Literal

from modules import bridge
from modules.helpers import print_lg, truncate_text


DISCARDED_BY_USER = "Job application discarded by user!"


def easy_apply_failure_reason(error: Exception) -> str:
    """The reason shown in History for an Easy Apply that didn't go through."""
    return "Discarded by user" if str(error) == DISCARDED_BY_USER else "Problem in Easy Applying"


def get_applied_job_ids() -> set[str]:
    """Job IDs already applied to, so they're skipped."""
    try:
        return bridge.applied_job_ids()
    except Exception as e:
        print_lg("Failed to read applied jobs history!", e)
        return set()


def failed_job(
    job_id: str,
    job_link: str,
    resume: str,
    date_listed,
    error: str,
    exception: Exception,
    application_link: str,
    screenshot_name: str,
) -> None:
    """Records a failed or skipped job."""
    try:
        bridge.save_failed(
            {
                "job_id": truncate_text(job_id),
                "job_link": truncate_text(job_link),
                "resume_tried": truncate_text(resume),
                "date_listed": date_listed,
                "date_tried": datetime.now(),
                "assumed_reason": truncate_text(error),
                "stack_trace": truncate_text(exception),
                "external_job_link": truncate_text(application_link),
                "screenshot_name": truncate_text(screenshot_name),
            }
        )
    except Exception as e:
        print_lg("Failed to save failed job to history!", e)


def submitted_jobs(
    job_id: str,
    title: str,
    company: str,
    work_location: str,
    work_style: str,
    description: str,
    experience_required: int | Literal["Unknown", "Error in extraction"],
    skills: list[str] | Literal["In Development"],
    hr_name: str | Literal["Unknown"],
    hr_link: str | Literal["Unknown"],
    resume: str,
    reposted: bool,
    date_listed: datetime | Literal["Unknown"],
    date_applied: datetime | Literal["Pending"],
    job_link: str,
    application_link: str,
    questions_list: set | None,
    connect_request: Literal["In Development"],
) -> None:
    """Records a submitted application."""
    try:
        bridge.save_applied(
            {
                "job_id": truncate_text(job_id),
                "title": truncate_text(title),
                "company": truncate_text(company),
                "work_location": truncate_text(work_location),
                "work_style": truncate_text(work_style),
                "about_job": truncate_text(description),
                "experience_required": truncate_text(experience_required),
                "skills": truncate_text(skills),
                "hr_name": truncate_text(hr_name),
                "hr_link": truncate_text(hr_link),
                "resume": truncate_text(resume),
                "reposted": truncate_text(reposted),
                "date_posted": date_listed,
                "date_applied": date_applied,
                "job_link": truncate_text(job_link),
                "external_job_link": truncate_text(application_link),
                "questions_found": truncate_text(questions_list),
                "connect_request": truncate_text(connect_request),
            }
        )
    except Exception as e:
        print_lg("Failed to save applied job to history!", e)
