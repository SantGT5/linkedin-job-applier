"""
Selectors and parsers for LinkedIn's AI-powered jobs search page (/jobs/search-results/).

CSS class names on this page are randomized per build, so everything here keys off
stable attributes instead: `componentkey`, `data-testid`, `aria-label`, and element
ids that embed the job id. Covered by tests/test_linkedin_ui.py.
"""

import re

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

# < Job list
# Login page. LinkedIn serves it in the visitor's local language and with random input ids,
# so match by input type / classic names, never by visible text.
LOGIN_EMAIL_INPUT_XPATH = (
    "//input[@type='email' or @id='username' or @name='session_key']"
)
LOGIN_PASSWORD_INPUT_XPATH = (
    "//input[@type='password' or @id='password' or @name='session_password']"
)

JOB_CARD_KEY_PREFIX = "job-card-component-ref-"
# Below this note LinkedIn lists "related" jobs that ignore the search filters.
RELATED_RESULTS_MARKER_XPATH = "//p[contains(normalize-space(.), 'more results related to your search')]"
JOB_CARDS_XPATH = (
    f"//div[@role='button' and starts-with(@componentkey, '{JOB_CARD_KEY_PREFIX}')]"
    "[not(preceding::p[contains(normalize-space(.), 'more results related to your search')])]"
)


def job_card_xpath(job_id: str) -> str:
    return f"//div[@role='button' and @componentkey='{JOB_CARD_KEY_PREFIX}{job_id}']"


def job_id_from_card_key(componentkey: str) -> str:
    return componentkey.removeprefix(JOB_CARD_KEY_PREFIX)


# Relative to a job card. The title <p> also holds a screen-reader-only copy, so take the visible span.
CARD_TITLE_XPATH = "(.//div[@data-display-contents='true']/p/span[@aria-hidden='true'])[1]"
CARD_COMPANY_XPATH = (
    "(.//div[@data-display-contents='true'][p])[1]/following-sibling::div[1]/p"
)
CARD_LOCATION_XPATH = (
    "(.//div[@data-display-contents='true'][p])[1]/following-sibling::p[1]"
)
CARD_APPLIED_XPATH = ".//p[normalize-space()='Applied']"


def split_work_location(text: str) -> tuple[str, str]:
    """
    "United States (Remote)" -> ("United States", "Remote"); "Toronto, ON" -> ("Toronto, ON", "")
    """
    text = text.strip()
    match = re.fullmatch(r"(.*?)\s*\(([^()]*)\)", text)
    if match:
        return match.group(1), match.group(2)
    return text, ""


# >


# < Job details panel
JOB_DETAILS_XPATH = (
    "//div[@data-sdui-screen='com.linkedin.sdui.flagshipnav.jobs.SemanticJobDetails']"
)
# Relative to the job details panel. The first "... ago" text is the posted date in the header.
TIME_POSTED_XPATH = "(.//*[contains(text(), ' ago')])[1]"
EASY_APPLY_BUTTON_XPATH = "//button[@aria-label='Easy Apply to this job']"
# Relative to the hiring team link.
HIRER_NAME_XPATH = "(.//p)[1]"


def job_details_loaded_xpath(job_id: str) -> str:
    return f"{JOB_DETAILS_XPATH}//a[contains(@href, '/jobs/view/{job_id}/')]"


def about_job_xpath(job_id: str) -> str:
    # The whole section, since the description isn't always in an expandable text box.
    # Its "About the job" heading is removed by `clean_description`.
    return f"//div[@id='JobDetails_AboutTheJob_{job_id}']"


def about_company_xpath(job_id: str) -> str:
    return f"//div[@id='JobDetails_AboutTheCompany_{job_id}']"


def hiring_team_link_xpath(job_id: str) -> str:
    # The same slot also lists "People you can reach out to"; only take people after the hiring team heading.
    return (
        f"(//div[@id='JobDetailsPeopleWhoCanHelpSlot_{job_id}']"
        "//a[contains(@href, '/in/')][preceding::*[normalize-space()='Meet the hiring team']])[1]"
    )


def clean_description(text: str) -> str:
    """
    Removes the "About the job" heading and the trailing "… more" expand button text.
    """
    text = re.sub(r"^\s*About the job(?![a-z])\s*", "", text)
    return re.sub(r"\s*…\s*more\s*$", "", text).strip()


# >


# < Easy Apply dialog
EASY_APPLY_MODAL_XPATH = (
    "//dialog[.//*[@data-sdui-screen='com.linkedin.sdui.flagshipnav.jobs.easyapply.EasyApply']]"
)
# LinkedIn sometimes shows "This job may not be the best fit" before the Easy Apply form.
APPLY_INTERCEPT_CONTINUE_XPATH = (
    "//dialog[.//*[@data-sdui-screen='com.linkedin.sdui.flagshipnav.jobs.ApplyInterceptModal']]"
    "//a[normalize-space()='Continue applying']"
)
# Relative to the dialog. A question is a <fieldset> (option groups), a <div> holding a
# <label for> (contact fields), or an "easyApplyFieldFocus" wrapper without a label
# (screening questions). Some fields carry that marker themselves, so take their parent.
FORM_QUESTIONS_XPATH = (
    ".//fieldset[not(ancestor::fieldset)]"
    " | .//div[label[@for]][not(ancestor::fieldset)]"
    " | .//div[starts-with(@componentkey, 'easyApplyFieldFocus')]"
    "[not(.//label[@for])][not(ancestor::fieldset)]"
    " | .//*[self::input or self::select or self::textarea]"
    "[starts-with(@componentkey, 'easyApplyFieldFocus')][not(ancestor::fieldset)]/.."
)
# Relative to a question.
FORM_TEXT_INPUT_XPATH = (
    ".//input[not(@type) or @type='text' or @type='tel' or @type='email' or @type='number' or @type='url']"
)
EASY_APPLY_PROGRESS_XPATH = ".//*[@role='progressbar']"
# Relative to the dialog. The form page's title, e.g. "Contact info".
EASY_APPLY_PAGE_TITLE_XPATH = "(.//div[@data-testid='lazy-column']//p)[1]"

# Relative to a radio question. Each option is a role="radio" element whose aria-label is the
# question and whose text is the option; its <label> is empty.
RADIO_OPTIONS_XPATH = ".//*[@role='radio']"
# Relative to a radio <input>.
RADIO_OPTION_OF_INPUT_XPATH = "ancestor::*[@role='radio'][1]"


def radio_option_xpath(answer: str) -> str:
    return f".//*[@role='radio'][normalize-space()='{answer}']"


def form_page_key(modal: WebElement) -> tuple[str | None, str | None]:
    """
    Identifies the Easy Apply form page shown, by its progress and title, to tell whether
    clicking Next or Review moved on. Unanswered required fields keep the form on its page.
    """

    def read(get_value):
        try:
            return get_value()
        except (NoSuchElementException, StaleElementReferenceException):
            return None

    return (
        read(
            lambda: modal.find_element(By.XPATH, EASY_APPLY_PROGRESS_XPATH).get_attribute(
                "aria-valuenow"
            )
        ),
        read(lambda: modal.find_element(By.XPATH, EASY_APPLY_PAGE_TITLE_XPATH).text),
    )


def question_label_text(text: str) -> str:
    """
    "Email address*" -> "Email address". Required fields end with "*".
    """
    return text.strip().removesuffix("*").strip()


def question_label(question: WebElement, control: WebElement) -> str:
    """
    A form question's text: its <label>, else the field's aria-label (screening questions),
    else the question's first paragraph (e.g. the location typeahead).
    """
    for get_text in (
        lambda: question.find_element(By.XPATH, ".//label[@for]").text,
        lambda: control.get_attribute("aria-label"),
        lambda: question.find_element(By.XPATH, ".//p").text,
    ):
        try:
            text = question_label_text(get_text() or "")
        except NoSuchElementException:
            continue
        if text:
            return text
    return "Unknown"


# >


# < Pagination
PAGINATION_XPATH = "//ul[@data-testid='pagination-controls-list']"
# Relative to the pagination list.
CURRENT_PAGE_XPATH = ".//button[@aria-current='true']"
NEXT_PAGE_BUTTON_XPATH = "//button[@data-testid='pagination-controls-next-button-visible']"


def page_button_xpath(page: int) -> str:
    return f"{PAGINATION_XPATH}//button[@aria-label='Page {page}']"


# >


# < Search filters on /jobs/search-results/
# Pills carry aria-label="Filter by <name>": toggles are role="radio" with aria-checked, dropdowns
# are role="button" and show the chosen value ("Filter by Contract") once set. The location sits
# in the results header as aria-label="Location <name>".
JOB_TYPES = ["Full-time", "Part-time", "Contract", "Temporary", "Volunteer", "Internship", "Other"]
ON_SITE_TYPES = ["On-site", "Remote", "Hybrid"]
SEARCH_HEADER_XPATH = "//*[@componentkey='searchResultsHeaderComponent']"
LOCATION_LABEL_XPATH = SEARCH_HEADER_XPATH + "//*[starts-with(@aria-label, 'Location ')]"
LOCATION_BUTTON_XPATH = LOCATION_LABEL_XPATH + "/ancestor-or-self::*[@role='button'][1]"
LOCATION_INPUT_XPATH = "//*[@componentkey='LocationTypeahead_TextEditor']"
LOCATION_OPTIONS_XPATH = "//*[@id='semanticSearchBoxLocationList']//a"
FILTER_SHOW_RESULTS_XPATH = "//a[normalize-space()='Show results']"


def _xpath_literal(text: str) -> str:
    if "'" not in text:
        return f"'{text}'"
    return "concat('" + "', \"'\", '".join(text.split("'")) + "')"


def filter_pill_xpath(name: str) -> str:
    """The clickable pill (role radio/button) labelled "Filter by <name>"."""
    label = _xpath_literal(f"Filter by {name}")
    return f"//*[@aria-label={label}]/ancestor-or-self::*[@role='radio' or @role='button'][1]"


# "Filter by Employment type" (none chosen), "Filter by Employment type, 2 filters are selected"
# (several) or "Filter by Contract" (one: the pill shows the chosen type).
_EMPLOYMENT_LABELS = "starts-with(@aria-label, 'Filter by Employment type') or " + " or ".join(
    f"@aria-label={_xpath_literal('Filter by ' + n)} or starts-with(@aria-label, {_xpath_literal('Filter by ' + n + ' ')})"
    for n in JOB_TYPES
)
# The "Employment type" dropdown, whether nothing, one or several types are chosen.
EMPLOYMENT_TYPE_PILL_XPATH = f"//*[{_EMPLOYMENT_LABELS}]/ancestor-or-self::*[@role='button'][1]"


def _find(page, xpath: str) -> list:
    """XPath on an lxml tree (tests) or a Selenium driver / element (bot)."""
    if hasattr(page, "xpath"):
        return page.xpath(xpath)
    return page.find_elements(By.XPATH, xpath)


def _attr(element, name: str) -> str | None:
    getter = getattr(element, "get_attribute", None)
    return getter(name) if getter else element.get(name)


def read_employment_options(page) -> dict[str, bool]:
    """Employment types offered in the open dropdown, and whether each is ticked."""
    options: dict[str, bool] = {}
    for box in _find(page, "//*[@role='checkbox'][@aria-label]"):
        label = _attr(box, "aria-label")
        if label in JOB_TYPES and label not in options:
            options[label] = _attr(box, "aria-checked") == "true"
    return options


def read_applied_filters(page) -> dict:
    """The filters LinkedIn actually applied, read from the results page."""
    on_site = []
    for name in ON_SITE_TYPES:
        for pill in _find(page, filter_pill_xpath(name)):
            if _attr(pill, "role") == "button" or _attr(pill, "aria-checked") == "true":
                on_site.append(name)
                break
    job_type = []
    for pill in _find(page, EMPLOYMENT_TYPE_PILL_XPATH):
        labels = [_attr(pill, "aria-label") or ""] + [
            _attr(e, "aria-label") or "" for e in _find(pill, ".//*[@aria-label]")
        ]
        text = " ".join(labels)
        job_type = [name for name in JOB_TYPES if f"Filter by {name}" in text]
        if not job_type and "selected" in text:
            # Several types: the pill only shows a count; the open dropdown has the ticks.
            job_type = [name for name, ticked in read_employment_options(page).items() if ticked]
        break
    locations = _find(page, LOCATION_LABEL_XPATH)
    location = (_attr(locations[0], "aria-label") or "")[len("Location "):] if locations else ""
    easy_apply = any(
        _attr(p, "aria-checked") == "true" for p in _find(page, filter_pill_xpath("Easy Apply"))
    )
    return {"job_type": job_type, "on_site": on_site, "location": location, "easy_apply": easy_apply}


def missing_filters(expected: dict, applied: dict) -> list[str]:
    """Names of the expected filters LinkedIn didn't apply."""
    missing = []
    if set(expected.get("job_type") or []) - set(applied.get("job_type") or []):
        missing.append("job_type")
    if set(expected.get("on_site") or []) - set(applied.get("on_site") or []):
        missing.append("on_site")
    want = (expected.get("location") or "").strip().lower()
    if want and want != (applied.get("location") or "").strip().lower():
        missing.append("location")
    if expected.get("easy_apply") and not applied.get("easy_apply"):
        missing.append("easy_apply")
    return missing
# >


# < Follow company (last step of Easy Apply)
# LinkedIn replaced `input#follow-company-checkbox` with a role="checkbox" div labelled
# "Follow <Company> to stay up to date with their page" (hidden input inside, random id).
FOLLOW_COMPANY_LABEL_XPATH = (
    ".//*[@role='checkbox'][contains(@aria-label, 'to stay up to date')]"
    " | .//label[@for='follow-company-checkbox']"
)
FOLLOW_COMPANY_CHECKBOX_XPATH = (
    ".//*[@role='checkbox'][contains(@aria-label, 'to stay up to date')]//input[@type='checkbox']"
    " | .//input[@id='follow-company-checkbox' and @type='checkbox']"
)


def follow_checked(target, checkbox=None) -> bool:
    """Whether "Follow <Company>" is ticked: aria-checked on the new control, else the input."""
    if _attr(target, "role") == "checkbox":
        return _attr(target, "aria-checked") == "true"
    if checkbox is None:
        return False
    is_selected = getattr(checkbox, "is_selected", None)
    return is_selected() if is_selected else checkbox.get("checked") is not None
# >
