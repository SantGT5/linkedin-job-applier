"""
Author:     Sai Vignesh Golla
LinkedIn:   https://www.linkedin.com/in/saivigneshgolla/

Copyright (C) 2024 Sai Vignesh Golla

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html

GitHub:     https://github.com/GodsScion/Auto_job_applier_linkedIn

Support me: https://github.com/sponsors/GodsScion

version:    26.01.20.5.08
"""

# Imports
import os
import re

import pyautogui
from datetime import datetime
from random import choice, randint, shuffle

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait

from config.personals import *
from config.questions import *
from config.search import *
from config.secrets import ai_provider, password, use_AI, username
from config.settings import *
from modules import bridge
from modules.clickers_and_finders import *
from modules.emails import extract_emails, should_collect_emails
from modules.helpers import *
from modules.history import DISCARDED_BY_USER, easy_apply_failure_reason, failed_job, get_applied_job_ids, submitted_jobs
from modules.linkedin_ui import *
from modules.open_chrome import *
from modules.validator import validate_config

if use_AI:
    # Import only the selected provider's module.
    if ai_provider == "claude":
        from modules.ai.claudeConnections import (
            claude_answer_question,
            claude_check_job_relevance,
            claude_close_client,
            claude_create_client,
            claude_extract_skills,
        )
    elif ai_provider == "glm":
        from modules.ai.glmConnections import (
            glm_answer_question,
            glm_check_job_relevance,
            glm_close_client,
            glm_create_client,
            glm_extract_skills,
        )

from typing import Literal

pyautogui.FAILSAFE = False
pyautogui.alert = safe_alert
pyautogui.confirm = safe_confirm


# < Global Variables and logics

if run_in_background == True:
    pause_at_failed_question = False
    pause_before_submit = False
    run_non_stop = False

first_name = first_name.strip()
middle_name = middle_name.strip()
last_name = last_name.strip()
full_name = (
    first_name + " " + middle_name + " " + last_name
    if middle_name
    else first_name + " " + last_name
)

useNewResume = True
randomly_answered_questions = set()

tabs_count = 1
easy_applied_count = 0
external_jobs_count = 0
failed_count = 0
skip_count = 0
dailyEasyApplyLimitReached = False

re_experience = re.compile(
    r"[(]?\s*(\d+)\s*[)]?\s*[-to]*\s*\d*[+]*\s*year[s]?", re.IGNORECASE
)

desired_salary_lakhs = str(round(desired_salary / 100000, 2))
desired_salary_monthly = str(round(desired_salary / 12, 2))
desired_salary = str(desired_salary)

current_ctc_lakhs = str(round(current_ctc / 100000, 2))
current_ctc_monthly = str(round(current_ctc / 12, 2))
current_ctc = str(current_ctc)

notice_period_months = str(notice_period // 30)
notice_period_weeks = str(notice_period // 7)
notice_period = str(notice_period)

hourly_rate = str(hourly_rate)

aiClient = None
##> ------ Dheeraj Deshwal : dheeraj9811 Email:dheeraj20194@iiitd.ac.in/dheerajdeshwal9811@gmail.com - Feature ------
about_company_for_ai = None  # TODO extract about company for AI
##<

# >


# < Login Functions
def is_logged_in_LN() -> bool:
    """
    Function to check if user is logged-in in LinkedIn
    * Returns: `True` if user is logged-in or `False` if not
    """
    # Login, 2FA and captcha pages: definitely not logged in (whatever their language).
    if any(part in driver.current_url for part in ("/login", "/checkpoint", "/uas/", "/authwall")):
        return False
    # URL alone is not reliable: LinkedIn can redirect unauthenticated sessions
    # to a feed-like page that still shows sign-in controls.
    if try_linkText(driver, "Sign in"):
        return False
    if try_xp(
        driver, '//button[@type="submit" and contains(text(), "Sign in")]', False
    ):
        return False
    if try_linkText(driver, "Join now"):
        return False
    # Authenticated shell indicators from LinkedIn top nav.
    if try_xp(driver, './/header//a[contains(@href, "/mynetwork/")]', False):
        return True
    if try_xp(driver, './/header//a[contains(@href, "/jobs/")]', False):
        return True
    if try_xp(driver, './/header//a[contains(@href, "/messaging/")]', False):
        return True
    print_lg(
        "Couldn't confirm logged-in state from page UI. Assuming not logged in and retrying."
    )
    return False


def first_displayed(xpath: str) -> WebElement | None:
    for element in driver.find_elements(By.XPATH, xpath):
        try:
            if element.is_displayed():
                return element
        except Exception:
            continue
    return None


def login_LN() -> None:
    """
    Function to login for LinkedIn
    * Tries to login using `LINKEDIN_USERNAME` and `LINKEDIN_PASSWORD` from `.env`
    * If that fails (or they aren't set), asks you to log in yourself in the live browser
    """
    driver.get("https://www.linkedin.com/login")
    if not username or not password:
        print_lg(
            "LINKEDIN_USERNAME / LINKEDIN_PASSWORD are not set in .env, hence can't login automatically! Please login manually!"
        )
        manual_login_retry(is_logged_in_LN, 2)
        return
    try:
        # The login page comes in the local language with random ids: find fields by type.
        WebDriverWait(driver, 10).until(lambda _: first_displayed(LOGIN_PASSWORD_INPUT_XPATH))
        email_input = first_displayed(LOGIN_EMAIL_INPUT_XPATH)
        if email_input:
            email_input.clear()
            email_input.send_keys(username)
        else:
            print_lg("Couldn't find username field.")
        password_input = first_displayed(LOGIN_PASSWORD_INPUT_XPATH)
        password_input.clear()
        password_input.send_keys(password)
        password_input.send_keys(Keys.ENTER)
    except Exception:
        try:
            profile_button = find_by_class(driver, "profile__details")
            profile_button.click()
        except Exception:
            print_lg("Couldn't Login!")

    try:
        # Wait to leave the login page (feed, or a captcha/2FA checkpoint).
        WebDriverWait(driver, 15).until(lambda d: "linkedin.com/login" not in d.current_url)
    except Exception:
        pass

    if is_logged_in_LN():
        return print_lg("Login successful!")

    print_lg(
        "Seems like login attempt failed! Possibly due to wrong credentials or an auth challenge. Try logging in manually!"
    )
    manual_login_retry(is_logged_in_LN, 2)


# >


saved_debug_labels: set[str] = set()


def save_debug_page(label: str) -> None:
    """
    Saves a screenshot and the page HTML to the screenshots folder, so a selector
    breakage (LinkedIn changing its page) can be diagnosed from what the browser showed.
    Saves once per `label` per run, so a repeated failure doesn't fill the disk.
    """
    if label in saved_debug_labels:
        return
    saved_debug_labels.add(label)
    try:
        debug_path = (
            logs_folder_path
            + "/screenshots/"
            + f"{label} - {datetime.now()}".replace(":", ".").replace("/", "-")
        ).replace("//", "/")
        driver.save_screenshot(debug_path + ".png")
        with open(debug_path + ".html", "w", encoding="utf-8") as file:
            file.write(driver.page_source)
        print_lg(f'Saved debug page "{label}" ({driver.current_url}).')
    except Exception as e:
        print_lg(f"Failed to save debug info for '{label}'!", e)


def wait_for_results(timeout: int = 15) -> None:
    """Waits for the results header (count + location) after a search or filter change."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, LOCATION_LABEL_XPATH))
        )
    except TimeoutException:
        print_lg("Search results header didn't show up in time.")
    buffer(2)


def close_popup() -> None:
    try:
        actions.send_keys(Keys.ESCAPE).perform()
    except Exception:
        pass
    sleep(0.5)


def applied_job_types() -> tuple[list[str], dict[str, bool]]:
    """Ticked employment types and the offered options, read from the dropdown (then closed)."""
    if not click_displayed(driver, EMPLOYMENT_TYPE_PILL_XPATH):
        return read_applied_filters(driver)["job_type"], {}
    sleep(1.5)
    offered = read_employment_options(driver)
    close_popup()
    return [name for name, ticked in offered.items() if ticked], offered


def set_job_types(wanted: list[str]) -> None:
    """Ticks exactly the wanted employment types (of those LinkedIn offers) and shows results."""
    if not click_displayed(driver, EMPLOYMENT_TYPE_PILL_XPATH):
        print_lg('Couldn\'t find the "Employment type" filter on the results page.')
        return
    sleep(1.5)
    changed = False
    for name, ticked in read_employment_options(driver).items():
        if ticked != (name in wanted):
            changed |= click_displayed(driver, employment_option_xpath(name))
            sleep(0.3)
    if changed and click_displayed(driver, FILTER_SHOW_RESULTS_XPATH):
        wait_for_results()
    else:
        close_popup()


def set_location(name: str) -> None:
    """Types the location into the results page's location box and picks the matching suggestion."""
    if not click_displayed(driver, LOCATION_BUTTON_XPATH):
        print_lg("Couldn't find the location button on the results page.")
        return
    try:
        box = WebDriverWait(driver, 5).until(lambda _: first_displayed(LOCATION_INPUT_XPATH))
        box.click()
        box.send_keys(Keys.CONTROL, "a")
        box.send_keys(Keys.BACKSPACE)
        box.send_keys(name)
        sleep(2.5)
        options = [o for o in driver.find_elements(By.XPATH, LOCATION_OPTIONS_XPATH) if o.is_displayed()]
        match = next((o for o in options if o.text.strip().lower() == name.lower()), None) or (
            options[0] if options else None
        )
        if match is None:
            print_lg(f'LinkedIn suggested no location for "{name}".')
            close_popup()
            return
        match.click()
        wait_for_results()
    except Exception as e:
        print_lg(f'Failed to set location "{name}"!', e)
        close_popup()


def apply_filters() -> None:
    """
    The search URL sets what LinkedIn still honours (date, Easy Apply, remote via redirect, geoId).
    LinkedIn's /jobs/search-results/ page silently drops the rest (job type, sometimes location and
    remote), so read back what it applied, set what's missing through the page, and check again.
    Anything still missing pauses the run (with "Pause after search") or is logged.
    """
    for name in unsupported_search_filters(
        companies=companies,
        location=location,
        industry=industry,
        job_function=job_function,
        job_titles=job_titles,
        benefits=benefits,
        commitments=commitments,
        fair_chance_employer=fair_chance_employer,
    ):
        print_lg(
            f'Search filter "{name}" is not supported on LinkedIn\'s new jobs search and was ignored.'
        )

    expected = {
        "job_type": list(job_type),
        "on_site": list(on_site),
        "location": search_location.strip(),
        "easy_apply": bool(easy_apply_only),
    }
    wait_for_results()
    missing: list[str] = []
    for attempt in range(3):
        applied = read_applied_filters(driver)
        if expected["job_type"]:
            applied["job_type"], offered = applied_job_types()
            unavailable = [t for t in expected["job_type"] if offered and t not in offered]
            if unavailable:
                print_lg(
                    f"LinkedIn doesn't offer employment type(s) {unavailable} for this search; using the rest."
                )
                expected["job_type"] = [t for t in expected["job_type"] if t not in unavailable]
        missing = missing_filters(expected, applied)
        print_lg(f"Filters on the results page: {applied}")
        if not missing or attempt == 2:
            break
        print_lg(f"LinkedIn didn't apply {missing}; setting them on the page (attempt {attempt + 1}).")
        if "location" in missing:
            set_location(expected["location"])
        if "job_type" in missing:
            set_job_types(expected["job_type"])
        if "on_site" in missing:
            for name in expected["on_site"]:
                if name not in read_applied_filters(driver)["on_site"]:
                    if click_displayed(driver, filter_pill_xpath(name)):
                        wait_for_results()
                    else:
                        print_lg(f'No "{name}" filter on the results page.')
        if "easy_apply" in missing and click_displayed(driver, filter_pill_xpath("Easy Apply")):
            wait_for_results()

    global pause_after_filters
    if missing:
        message = (
            f"LinkedIn didn't apply these filters: {', '.join(missing)} "
            f"(wanted {', '.join(f'{k}={expected[k]}' for k in missing)}). "
            "Fix them in the live browser, then continue."
        )
        print_lg(message)
        if pause_after_filters:
            pause_for_user(message, "Filters not applied", "Done, continue")
            return
    # "Continue" goes first: the terminal prompt picks the first button when you just press Enter.
    if pause_after_filters and "Turn off Pause after search" == pyautogui.confirm(
        "These are your configured search results and filter. It is safe to change them while this dialog is open, any changes later could result in errors and skipping this search run.",
        "Please check your results",
        ["Look's good, Continue", "Turn off Pause after search"],
    ):
        pause_after_filters = False


def get_page_info() -> tuple[WebElement | None, int | None]:
    """
    Function to get pagination element and current page number
    """
    try:
        pagination_element = driver.find_element(By.XPATH, PAGINATION_XPATH)
        scroll_to_view(driver, pagination_element)
        current_page = int(
            pagination_element.find_element(By.XPATH, CURRENT_PAGE_XPATH).text
        )
    except Exception as e:
        print_lg("Failed to find Pagination element, hence couldn't scroll till end!")
        pagination_element = None
        current_page = None
        print_lg(e)
    return pagination_element, current_page


def get_job_main_details(
    job: WebElement, blacklisted_companies: set, rejected_jobs: set
) -> tuple[str, str, str, str, str, bool]:
    """
    # Function to get job main details.
    Returns a tuple of (job_id, title, company, work_location, work_style, skip)
    * job_id: Job ID
    * title: Job title
    * company: Company name
    * work_location: Work location of this job
    * work_style: Work style of this job (Remote, On-site, Hybrid)
    * skip: A boolean flag to skip this job
    """
    skip = False
    # The whole card is the clickable element that opens the job details.
    job_details_button = job
    # Avoid placing the card under fixed LinkedIn top navigation.
    scroll_to_view(driver, job_details_button)
    job_id = job_id_from_card_key(job.get_dom_attribute("componentkey"))
    title = job.find_element(By.XPATH, CARD_TITLE_XPATH).text.strip()
    company = job.find_element(By.XPATH, CARD_COMPANY_XPATH).text.strip()
    work_location, work_style = split_work_location(
        job.find_element(By.XPATH, CARD_LOCATION_XPATH).text
    )

    # Skip if previously rejected due to blacklist or already applied
    if company in blacklisted_companies:
        print_lg(
            f'Skipping "{title} | {company}" job (Blacklisted Company). Job ID: {job_id}!'
        )
        skip = True
    elif job_id in rejected_jobs:
        print_lg(
            f'Skipping previously rejected "{title} | {company}" job. Job ID: {job_id}!'
        )
        skip = True
    if not skip and job.find_elements(By.XPATH, CARD_APPLIED_XPATH):
        skip = True
        print_lg(f'Already applied to "{title} | {company}" job. Job ID: {job_id}!')
    try:
        if not skip:
            try:
                job_details_button.click()
            except ElementClickInterceptedException:
                # If intercepted by sticky header/overlay, re-center and retry.
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});",
                    job_details_button,
                )
                buffer(1)
                try:
                    job_details_button.click()
                except ElementClickInterceptedException:
                    # Final fallback: JS click bypasses viewport overlap issues.
                    driver.execute_script("arguments[0].click();", job_details_button)
    except Exception:
        print_lg(
            f'Failed to click "{title} | {company}" job on details button. Job ID: {job_id}!'
        )
        discard_job()
        job_details_button.click()  # To pass the error outside
    if not skip:
        # Wait for the details panel to show this job, so later reads don't get the previous job's details.
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, job_details_loaded_xpath(job_id))
                )
            )
        except TimeoutException:
            print_lg(
                f'Details of "{title} | {company}" job did not load, skipping it. Job ID: {job_id}!'
            )
            skip = True
    buffer(click_gap)
    return (job_id, title, company, work_location, work_style, skip)


# Function to check for Blacklisted words in About Company
def check_blacklist(
    rejected_jobs: set, job_id: str, company: str, blacklisted_companies: set
) -> tuple[set, set, WebElement] | ValueError:
    jobs_top_card = driver.find_element(By.XPATH, JOB_DETAILS_XPATH)
    about_company_org = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, about_company_xpath(job_id)))
    )
    scroll_to_view(driver, about_company_org)
    about_company_org = about_company_org.text
    about_company = about_company_org.lower()
    skip_checking = False
    for word in about_company_good_words:
        if word.lower() in about_company:
            print_lg(
                f'Found the word "{word}". So, skipped checking for blacklist words.'
            )
            skip_checking = True
            break
    if not skip_checking:
        for word in about_company_bad_words:
            if word.lower() in about_company:
                rejected_jobs.add(job_id)
                blacklisted_companies.add(company)
                raise ValueError(f'About Company contains "{word}".')
    buffer(click_gap)
    scroll_to_view(driver, jobs_top_card)
    return rejected_jobs, blacklisted_companies, jobs_top_card


# Function to extract years of experience required from About Job
def extract_years_of_experience(text: str) -> int:
    # Extract all patterns like '10+ years', '5 years', '3-5 years', etc.
    matches = re.findall(re_experience, text)
    if len(matches) == 0:
        print_lg("Couldn't find an experience requirement in About the Job.")
        return 0
    return max([int(match) for match in matches if int(match) <= 12])


def get_job_description(
    job_id: str,
) -> tuple[
    str | Literal["Unknown"], int | Literal["Unknown"], bool, str | None, str | None
]:
    """
    # Job Description
    Function to extract job description from About the Job.
    ### Returns:
    - `jobDescription: str | 'Unknown'`
    - `experience_required: int | 'Unknown'`
    - `skip: bool`
    - `skipReason: str | None`
    - `skipMessage: str | None`
    """
    # Set before the `try`, so they're defined when returned after a failed extraction.
    skip = False
    skipReason = None
    skipMessage = None
    try:
        ##> ------ Dheeraj Deshwal : dheeraj9811 Email:dheeraj20194@iiitd.ac.in/dheerajdeshwal9811@gmail.com - Feature ------
        jobDescription = "Unknown"
        ##<
        experience_required = "Unknown"
        found_masters = 0
        about_job = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, about_job_xpath(job_id)))
        )
        # innerText includes lines hidden behind the "… more" button, unlike .text
        jobDescription = clean_description(about_job.get_attribute("innerText"))
        jobDescriptionLow = jobDescription.lower()
        for word in bad_words:
            if word.lower() in jobDescriptionLow:
                skipMessage = f'Contains bad word "{word}".'
                skipReason = "Found a Bad Word in About Job"
                skip = True
                break
        if (
            not skip
            and security_clearance == False
            and (
                "polygraph" in jobDescriptionLow
                or "clearance" in jobDescriptionLow
                or "secret" in jobDescriptionLow
            )
        ):
            skipMessage = 'Found "Clearance" or "Polygraph".'
            skipReason = "Asking for Security clearance"
            skip = True
        if not skip:
            if did_masters and "master" in jobDescriptionLow:
                print_lg('Found the word "master" in About the Job.')
                found_masters = 2
            experience_required = extract_years_of_experience(jobDescription)
            if (
                current_experience > -1
                and experience_required > current_experience + found_masters
            ):
                skipMessage = f"Experience required {experience_required} > current experience {current_experience + found_masters}."
                skipReason = "Required experience is high"
                skip = True
    except Exception:
        if jobDescription == "Unknown":
            print_lg("Unable to extract job description!")
            save_debug_page("Job description not found")
        else:
            experience_required = "Error in extraction"
            print_lg("Unable to extract years of experience required!")

    return jobDescription, experience_required, skip, skipReason, skipMessage


# Function to upload resume
def upload_resume(modal: WebElement, resume: str) -> tuple[bool, str]:
    try:
        modal.find_element(By.NAME, "file").send_keys(os.path.abspath(resume))
        return True, os.path.basename(default_resume_path)
    except:
        return False, "Previous resume"


current_job_id: str | None = None


def note_unanswered(label: str, question_type: str, options: list[str] | None = None) -> None:
    """A question the bot had to guess (or leave): listed in the UI so you can add an answer."""
    randomly_answered_questions.add((label, question_type))
    try:
        bridge.record_unanswered(label, question_type, options, current_job_id)
    except Exception as e:
        print_lg("Failed to record unanswered question!", e)


# Function to answer common questions for Easy Apply
def answer_common_questions(label: str, answer: str) -> str:
    if "sponsorship" in label or "visa" in label:
        answer = require_visa
    return answer


# Function to answer the questions for Easy Apply
def answer_questions(
    modal: WebElement,
    questions_list: set,
    work_location: str,
    job_description: str | None = None,
) -> set:
    # Get all questions from the page

    all_questions = modal.find_elements(By.XPATH, FORM_QUESTIONS_XPATH)
    # all_questions = modal.find_elements(By.CLASS_NAME, "jobs-easy-apply-form-element")
    # all_list_questions = modal.find_elements(By.XPATH, ".//div[@data-test-text-entity-list-form-component]")
    # all_single_line_questions = modal.find_elements(By.XPATH, ".//div[@data-test-single-line-text-form-component]")
    # all_questions = all_questions + all_list_questions + all_single_line_questions

    for Question in all_questions:
        # Check if it's a select Question
        select = try_xp(Question, ".//select", False)
        if select:
            label_org = question_label(Question, select)
            answer = "Yes"
            label = label_org.lower()
            select = Select(select)
            selected_option = select.first_selected_option.text
            optionsText = []
            options = '"List of phone country codes"'
            if label != "phone country code":
                optionsText = [option.text for option in select.options]
                options = "".join([f' "{option}",' for option in optionsText])
            prev_answer = selected_option
            # An unanswered select shows "Select an option", or an empty placeholder in the new Easy Apply form.
            if overwrite_previous_answers or selected_option in ("Select an option", ""):
                custom = lookup_custom_answer(label_org, custom_answers)
                ##> ------ WINDY_WINDWARD Email:karthik.sarode23@gmail.com - Added fuzzy logic to answer location based questions ------
                if custom is not None:
                    answer = custom
                elif "email" in label or "phone" in label:
                    answer = prev_answer
                    if not answer:
                        # Nothing prefilled to keep; leave it for "Pause at failed question".
                        note_unanswered(label_org, "select", optionsText)
                        questions_list.add(
                            (f"{label_org} [ {options} ]", answer, "select", prev_answer)
                        )
                        continue
                elif "gender" in label or "sex" in label:
                    answer = gender
                elif "disability" in label:
                    answer = disability_status
                elif "proficiency" in label:
                    answer = "Professional"
                # Add location handling
                elif any(
                    loc_word in label
                    for loc_word in ["location", "city", "state", "country"]
                ):
                    if "country" in label:
                        answer = country
                    elif "state" in label:
                        answer = state
                    elif "city" in label:
                        answer = current_city if current_city else work_location
                    else:
                        answer = work_location
                else:
                    answer = answer_common_questions(label, answer)
                try:
                    select.select_by_visible_text(answer)
                except NoSuchElementException:
                    # Define similar phrases for common answers
                    possible_answer_phrases = []
                    if answer == "Decline":
                        possible_answer_phrases = [
                            "Decline",
                            "not wish",
                            "don't wish",
                            "Prefer not",
                            "not want",
                        ]
                    elif "yes" in answer.lower():
                        possible_answer_phrases = ["Yes", "Agree", "I do", "I have"]
                    elif "no" in answer.lower():
                        possible_answer_phrases = [
                            "No",
                            "Disagree",
                            "I don't",
                            "I do not",
                        ]
                    else:
                        # Try partial matching for any answer
                        possible_answer_phrases = [answer]
                        # Add lowercase and uppercase variants
                        possible_answer_phrases.append(answer.lower())
                        possible_answer_phrases.append(answer.upper())
                        # Try without special characters
                        possible_answer_phrases.append(
                            "".join(c for c in answer if c.isalnum())
                        )
                    ##<
                    foundOption = False
                    for phrase in possible_answer_phrases:
                        for option in optionsText:
                            # Check if phrase is in option or option is in phrase (bidirectional matching)
                            if (
                                phrase.lower() in option.lower()
                                or option.lower() in phrase.lower()
                            ):
                                select.select_by_visible_text(option)
                                answer = option
                                foundOption = True
                                break
                    if not foundOption:
                        # TODO: Use AI to answer the question need to be implemented logic to extract the options for the question
                        print_lg(
                            f'Failed to find an option with text "{answer}" for question labelled "{label_org}", answering randomly!'
                        )
                        select.select_by_index(randint(1, len(select.options) - 1))
                        answer = select.first_selected_option.text
                        note_unanswered(label_org, "select", optionsText)
            questions_list.add(
                (f"{label_org} [ {options} ]", answer, "select", prev_answer)
            )
            continue

        # Check if it's a radio Question (the question itself may be the fieldset)
        radio = try_xp(
            Question,
            "self::fieldset[.//input[@type='radio']] | .//fieldset[.//input[@type='radio']]",
            False,
        )
        if radio:
            prev_answer = None
            label = try_xp(
                radio,
                ".//span[@data-test-form-builder-radio-button-form-component__title]",
                False,
            )
            try:
                label = find_by_class(label, "visually-hidden", 2.0)
            except:
                pass
            if not label:
                label = try_xp(radio, ".//legend", False)
            label_org = label.text if label else ""
            if not label_org:
                # New Easy Apply form: each option carries the question in aria-label.
                radio_option = try_xp(radio, RADIO_OPTIONS_XPATH, False)
                label_org = (
                    question_label_text(
                        (radio_option.get_attribute("aria-label") if radio_option else "")
                        or ""
                    )
                    or "Unknown"
                )
            answer = "Yes"
            label = label_org.lower()

            label_org += " [ "
            options = radio.find_elements(By.TAG_NAME, "input")
            options_labels = []

            for option in options:
                id = option.get_attribute("id")
                option_label = try_xp(radio, f'.//label[@for="{id}"]', False)
                option_text = option_label.text if option_label else ""
                if not option_text:
                    # New Easy Apply form: the label is empty, the text is on the role="radio" option.
                    radio_option = try_xp(option, RADIO_OPTION_OF_INPUT_XPATH, False)
                    option_text = radio_option.text if radio_option else "Unknown"
                options_labels.append(
                    f'"{option_text}"<{option.get_attribute("value")}>'
                )  # Saving option as "label <value>"
                if option.is_selected():
                    prev_answer = options_labels[-1]
                label_org += f" {options_labels[-1]},"

            if overwrite_previous_answers or prev_answer is None:
                custom = lookup_custom_answer(label, custom_answers)
                if custom is not None:
                    answer = custom
                elif "citizenship" in label or "employment eligibility" in label:
                    answer = us_citizenship
                elif "veteran" in label or "protected" in label:
                    answer = veteran_status
                elif "disability" in label or "handicapped" in label:
                    answer = disability_status
                else:
                    answer = answer_common_questions(label, answer)
                foundOption = try_xp(
                    radio, f".//label[normalize-space()='{answer}']", False
                ) or try_xp(radio, radio_option_xpath(answer), False)
                if foundOption:
                    actions.move_to_element(foundOption).click().perform()
                else:
                    possible_answer_phrases = (
                        ["Decline", "not wish", "don't wish", "Prefer not", "not want"]
                        if answer == "Decline"
                        else [answer]
                    )
                    ele = options[0]
                    answer = options_labels[0]
                    for phrase in possible_answer_phrases:
                        for i, option_label in enumerate(options_labels):
                            if phrase in option_label:
                                foundOption = options[i]
                                ele = foundOption
                                answer = (
                                    f"Decline ({option_label})"
                                    if len(possible_answer_phrases) > 1
                                    else option_label
                                )
                                break
                        if foundOption:
                            break
                    # Click the visible role="radio" option rather than its hidden <input>, when there is one.
                    ele = try_xp(ele, RADIO_OPTION_OF_INPUT_XPATH, False) or ele
                    actions.move_to_element(ele).click().perform()
                    if not foundOption:
                        note_unanswered(
                            label_org.split(" [ ")[0],
                            "radio",
                            [o.split("<")[0].strip('"') for o in options_labels],
                        )
            else:
                answer = prev_answer
            questions_list.add((label_org + " ]", answer, "radio", prev_answer))
            continue

        # Check if it's a text question
        text = try_xp(Question, FORM_TEXT_INPUT_XPATH, False)
        if text:
            do_actions = False
            label_org = question_label(Question, text)
            answer = ""  # years_of_experience
            label = label_org.lower()

            prev_answer = text.get_attribute("value")
            if not prev_answer or overwrite_previous_answers:
                custom = lookup_custom_answer(label_org, custom_answers)
                if custom is not None:
                    answer = custom
                elif "experience" in label or "years" in label:
                    answer = years_of_experience
                elif "phone" in label or "mobile" in label:
                    answer = phone_number
                elif "street" in label:
                    answer = street
                elif "city" in label or "location" in label or "address" in label:
                    answer = current_city if current_city else work_location
                    do_actions = True
                elif "signature" in label:
                    answer = full_name  # 'signature' in label or 'legal name' in label or 'your name' in label or 'full name' in label: answer = full_name     # What if question is 'name of the city or university you attend, name of referral etc?'
                elif "name" in label:
                    if "full" in label:
                        answer = full_name
                    elif "first" in label and "last" not in label:
                        answer = first_name
                    elif "middle" in label and "last" not in label:
                        answer = middle_name
                    elif "last" in label and "first" not in label:
                        answer = last_name
                    elif "employer" in label:
                        answer = recent_employer
                    else:
                        answer = full_name
                elif "notice" in label:
                    if "month" in label:
                        answer = notice_period_months
                    elif "week" in label:
                        answer = notice_period_weeks
                    else:
                        answer = notice_period
                elif "hourly" in label and "rate" in label:
                    answer = hourly_rate
                elif (
                    "salary" in label
                    or "compensation" in label
                    or "ctc" in label
                    or "pay" in label
                ):
                    if "current" in label or "present" in label:
                        if "month" in label:
                            answer = current_ctc_monthly
                        elif "lakh" in label:
                            answer = current_ctc_lakhs
                        else:
                            answer = current_ctc
                    else:
                        if "month" in label:
                            answer = desired_salary_monthly
                        elif "lakh" in label:
                            answer = desired_salary_lakhs
                        else:
                            answer = desired_salary
                elif "linkedin" in label:
                    answer = linkedIn
                elif (
                    "website" in label
                    or "blog" in label
                    or "portfolio" in label
                    or "link" in label
                ):
                    answer = website
                elif "scale of 1-10" in label:
                    answer = confidence_level
                elif "headline" in label:
                    answer = linkedin_headline
                elif (
                    ("hear" in label or "come across" in label)
                    and "this" in label
                    and ("job" in label or "position" in label)
                ):
                    answer = "https://github.com/GodsScion/Auto_job_applier_linkedIn"
                elif "state" in label or "province" in label:
                    answer = state
                elif "zip" in label or "postal" in label or "code" in label:
                    answer = zipcode
                elif "country" in label:
                    answer = country
                else:
                    answer = answer_common_questions(label, answer)
                ##> ------ Yang Li : MARKYangL - Feature ------
                if answer == "":
                    if use_AI and aiClient:
                        try:
                            if ai_provider.lower() == "claude":
                                answer = claude_answer_question(
                                    aiClient,
                                    label_org,
                                    options=None,
                                    question_type="text",
                                    job_description=job_description,
                                    about_company=None,
                                    user_information_all=user_information_all,
                                )
                            elif ai_provider.lower() == "glm":
                                answer = glm_answer_question(
                                    aiClient,
                                    label_org,
                                    options=None,
                                    question_type="text",
                                    job_description=job_description,
                                    about_company=None,
                                    user_information_all=user_information_all,
                                )
                            else:
                                note_unanswered(label_org, "text")
                                answer = years_of_experience
                            if not (answer and isinstance(answer, str)):
                                note_unanswered(label_org, "text")
                                answer = years_of_experience
                        except Exception as e:
                            print_lg("Failed to get AI answer!", e)
                            note_unanswered(label_org, "text")
                            answer = years_of_experience
                    else:
                        note_unanswered(label_org, "text")
                        answer = years_of_experience
                ##<
                text.clear()
                text.send_keys(answer)
                if do_actions:
                    sleep(2)
                    actions.send_keys(Keys.ARROW_DOWN)
                    actions.send_keys(Keys.ENTER).perform()
            questions_list.add(
                (label, text.get_attribute("value"), "text", prev_answer)
            )
            continue

        # Check if it's a textarea question
        text_area = try_xp(Question, ".//textarea", False)
        if text_area:
            label_org = question_label(Question, text_area)
            label = label_org.lower()
            answer = ""
            prev_answer = text_area.get_attribute("value")
            if not prev_answer or overwrite_previous_answers:
                custom = lookup_custom_answer(label_org, custom_answers)
                if custom is not None:
                    answer = custom
                elif "summary" in label:
                    answer = linkedin_summary
                elif "cover" in label:
                    answer = cover_letter
                if answer == "":
                    ##> ------ Yang Li : MARKYangL - Feature ------
                    if use_AI and aiClient:
                        try:
                            if ai_provider.lower() == "claude":
                                answer = claude_answer_question(
                                    aiClient,
                                    label_org,
                                    options=None,
                                    question_type="textarea",
                                    job_description=job_description,
                                    about_company=None,
                                    user_information_all=user_information_all,
                                )
                            elif ai_provider.lower() == "glm":
                                answer = glm_answer_question(
                                    aiClient,
                                    label_org,
                                    options=None,
                                    question_type="textarea",
                                    job_description=job_description,
                                    about_company=None,
                                    user_information_all=user_information_all,
                                )
                            else:
                                note_unanswered(label_org, "textarea")
                                answer = ""
                            if not (answer and isinstance(answer, str)):
                                note_unanswered(label_org, "textarea")
                                answer = ""
                        except Exception as e:
                            print_lg("Failed to get AI answer!", e)
                            note_unanswered(label_org, "textarea")
                            answer = ""
                    else:
                        note_unanswered(label_org, "textarea")
            text_area.clear()
            text_area.send_keys(answer)
            questions_list.add(
                (label, text_area.get_attribute("value"), "textarea", prev_answer)
            )
            ##<
            continue

        # Check if it's a checkbox question
        checkbox = try_xp(Question, ".//input[@type='checkbox']", False)
        if checkbox:
            label = try_xp(Question, ".//span[@class='visually-hidden']", False) or try_xp(
                Question, ".//legend", False
            )
            label_org = label.text if label else "Unknown"
            label = label_org.lower()
            answer = try_xp(
                Question, ".//label[@for]", False
            )  # Sometimes multiple checkboxes are given for 1 question, Not accounted for that yet
            answer = answer.text if answer else "Unknown"
            prev_answer = checkbox.is_selected()
            checked = prev_answer
            if not prev_answer:
                try:
                    actions.move_to_element(checkbox).click().perform()
                    checked = True
                except Exception as e:
                    print_lg("Checkbox click failed!", e)
                    pass
            questions_list.add(
                (f"{label} ([X] {answer})", checked, "checkbox", prev_answer)
            )
            continue

    # Select todays date
    try_xp(driver, "//button[contains(@aria-label, 'This is today')]")


    return questions_list


def external_apply(
    pagination_element: WebElement,
    job_id: str,
    job_link: str,
    resume: str,
    date_listed,
    application_link: str,
    screenshot_name: str,
) -> tuple[bool, str, int]:
    """
    Function to open new tab and save external job application links
    """
    global tabs_count, dailyEasyApplyLimitReached
    if easy_apply_only:
        try:
            if (
                "exceeded the daily application limit"
                in driver.find_element(
                    By.CLASS_NAME, "artdeco-inline-feedback__message"
                ).text
            ):
                dailyEasyApplyLimitReached = True
        except:
            pass
        print_lg("Easy apply failed I guess!")
        if pagination_element != None:
            return True, application_link, tabs_count
    try:
        wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    ".//button[contains(@class,'jobs-apply-button') and contains(@class, 'artdeco-button--3')]",
                )
            )
        ).click()  # './/button[contains(span, "Apply") and not(span[contains(@class, "disabled")])]'
        wait_span_click(driver, "Continue", 1, True, False)
        windows = driver.window_handles
        tabs_count = len(windows)
        driver.switch_to.window(windows[-1])
        application_link = driver.current_url
        print_lg('Got the external application link "{}"'.format(application_link))
        if close_tabs and driver.current_window_handle != linkedIn_tab:
            driver.close()
        driver.switch_to.window(linkedIn_tab)
        return False, application_link, tabs_count
    except Exception as e:
        print_lg("Failed to apply!")
        failed_job(
            job_id,
            job_link,
            resume,
            date_listed,
            "Probably didn't find Apply button or unable to switch tabs.",
            e,
            application_link,
            screenshot_name,
        )
        global failed_count
        failed_count += 1
        bridge.bump_counts(failed=1)
        return True, application_link, tabs_count


def follow_company(modal: WebDriver = driver) -> None:
    """
    Ticks or unticks "Follow <Company> to stay up to date with their page" to match
    `follow_companies`. Called right before clicking Submit.
    """
    try:
        targets = modal.find_elements(By.XPATH, FOLLOW_COMPANY_LABEL_XPATH)
        if not targets:
            print_lg('No "Follow company" checkbox on this application.')
            return
        target = targets[0]
        boxes = modal.find_elements(By.XPATH, FOLLOW_COMPANY_CHECKBOX_XPATH)
        box = boxes[0] if boxes else None
        if follow_checked(target, box) == follow_companies:
            return
        scroll_to_view(driver, target)
        try:
            target.click()
        except Exception:
            driver.execute_script("arguments[0].click();", target)
        sleep(0.5)
        wanted = "ticked" if follow_companies else "unticked"
        if follow_checked(target, box) != follow_companies:
            print_lg(f'Couldn\'t get the "Follow company" checkbox {wanted}!')
        else:
            print_lg(f'"Follow company" checkbox {wanted}.')
    except Exception as e:
        print_lg("Failed to update follow companies checkbox!", e)


# < Failed attempts logging (failed_job lives in modules/history.py)
def screenshot(driver: WebDriver, job_id: str, failedAt: str) -> str:
    """
    Function to to take screenshot for debugging
    - Returns screenshot name as String
    """
    screenshot_name = "{} - {} - {}.png".format(job_id, failedAt, str(datetime.now()))
    path = logs_folder_path + "/screenshots/" + screenshot_name.replace(":", ".")
    driver.save_screenshot(path.replace("//", "/"))
    return screenshot_name


# >


# Function to discard the job application
def discard_job() -> None:
    actions.send_keys(Keys.ESCAPE).perform()
    wait_span_click(driver, "Discard", 2)


# Function to apply to jobs
def apply_to_jobs(search_terms: list[str]) -> None:
    applied_jobs = get_applied_job_ids()
    rejected_jobs = set()
    blacklisted_companies = set()
    global current_city, failed_count, skip_count, easy_applied_count, external_jobs_count, tabs_count, pause_before_submit, pause_at_failed_question, useNewResume, current_job_id
    current_city = current_city.strip()

    if randomize_search_order:
        shuffle(search_terms)
    for searchTerm in search_terms:
        search_url = build_jobs_search_url(
            searchTerm,
            date_posted=date_posted,
            sort_by=sort_by,
            location=search_location,
            easy_apply_only=easy_apply_only,
            experience_level=experience_level,
            job_type=job_type,
            on_site=on_site,
            salary=salary,
            under_10_applicants=under_10_applicants,
            in_your_network=in_your_network,
        )
        driver.get(search_url)
        print_lg(f'>>>> Now searching for "{searchTerm}" <<<<')
        print_lg(f"Search URL: {search_url}")

        apply_filters()

        current_count = 0
        switch_to_next_search = False
        try:
            while current_count < switch_number:
                # Wait until job listings are loaded
                try:
                    wait.until(
                        EC.presence_of_all_elements_located((By.XPATH, JOB_CARDS_XPATH))
                    )
                except TimeoutException:
                    save_debug_page("Job listings not found")
                    raise

                pagination_element, current_page = get_page_info()

                # Find all job listings in current page. Collect ids first: opening a job
                # re-renders the list, which would make held card elements stale.
                buffer(3)
                job_ids_on_page = [
                    job_id_from_card_key(card.get_dom_attribute("componentkey"))
                    for card in driver.find_elements(By.XPATH, JOB_CARDS_XPATH)
                ]
                print_lg(f"Found {len(job_ids_on_page)} jobs on page {current_page}.")
                if not job_ids_on_page:
                    save_debug_page("No job cards on page")

                for job_id in job_ids_on_page:
                    if current_count >= switch_number:
                        break
                    try:
                        job = driver.find_element(By.XPATH, job_card_xpath(job_id))
                    except NoSuchElementException:
                        print_lg(f"Job card disappeared from the list. Job ID: {job_id}!")
                        continue

                    job_id, title, company, work_location, work_style, skip = (
                        get_job_main_details(job, blacklisted_companies, rejected_jobs)
                    )

                    if skip:
                        continue
                    # Redundant fail safe check for applied jobs!
                    if job_id in applied_jobs:
                        print_lg(
                            f'Already applied to "{title} | {company}" job. Job ID: {job_id}!'
                        )
                        continue
                    print_lg(
                        f'Trying to Apply to "{title} | {company}" job. Job ID: {job_id}'
                    )
                    current_job_id = job_id

                    job_link = "https://www.linkedin.com/jobs/view/" + job_id
                    application_link = "Easy Applied"
                    date_applied = "Pending"
                    hr_link = "Unknown"
                    hr_name = "Unknown"
                    connect_request = "In Development"  # Still in development
                    date_listed = "Unknown"
                    skills = "Needs an AI"  # Still in development
                    resume = "Pending"
                    reposted = False
                    questions_list = None
                    screenshot_name = "Not Available"

                    try:
                        rejected_jobs, blacklisted_companies, jobs_top_card = (
                            check_blacklist(
                                rejected_jobs, job_id, company, blacklisted_companies
                            )
                        )
                    except ValueError as e:
                        print_lg(f'Skipping "{title} | {company}": {e}')
                        failed_job(
                            job_id,
                            job_link,
                            resume,
                            date_listed,
                            "Found Blacklisted words in About Company",
                            e,
                            "Skipped",
                            screenshot_name,
                        )
                        skip_count += 1
                        bridge.bump_counts(skipped=1)
                        continue
                    except Exception:
                        print_lg("Failed to scroll to About Company!")

                    # Hiring Manager info
                    try:
                        hr_info_card = WebDriverWait(driver, 2).until(
                            EC.presence_of_element_located(
                                (By.XPATH, hiring_team_link_xpath(job_id))
                            )
                        )
                        hr_link = hr_info_card.get_attribute("href")
                        hr_name = hr_info_card.find_element(
                            By.XPATH, HIRER_NAME_XPATH
                        ).text
                    except Exception:
                        pass  # Not every job lists its hiring team.

                    # Calculation of date posted
                    try:
                        time_posted_text = jobs_top_card.find_element(
                            By.XPATH, TIME_POSTED_XPATH
                        ).text
                        if time_posted_text.__contains__("Reposted"):
                            reposted = True
                            time_posted_text = time_posted_text.replace("Reposted", "")
                        date_listed = calculate_date_posted(time_posted_text.strip())
                    except Exception as e:
                        print_lg("Failed to calculate the date posted!", e)

                    description, experience_required, skip, reason, message = (
                        get_job_description(job_id)
                    )
                    if skip:
                        print_lg(f'Skipping "{title} | {company}": {message}')
                        failed_job(
                            job_id,
                            job_link,
                            resume,
                            date_listed,
                            reason,
                            f"{message}\n\n{description}",
                            "Skipped",
                            screenshot_name,
                        )
                        rejected_jobs.add(job_id)
                        skip_count += 1
                        bridge.bump_counts(skipped=1)
                        continue

                    if use_AI and aiClient and description != "Unknown":
                        ##> ------ Yang Li : MARKYangL - Feature ------
                        try:
                            if ai_provider.lower() == "claude":
                                skills = claude_extract_skills(aiClient, description)
                            elif ai_provider.lower() == "glm":
                                skills = glm_extract_skills(aiClient, description)
                            else:
                                skills = "In Development"
                        except Exception as e:
                            print_lg("Failed to extract skills:", e)
                            skills = "Error extracting skills"
                        ##<

                    # AI screen: score the job against your profile (to skip poor fits) and
                    # detect "apply by email" postings (their address goes to the HR email list).
                    relevance = {}
                    match_score = None
                    if (
                        use_AI
                        and aiClient
                        and ai_provider.lower() in ("claude", "glm")
                        and description != "Unknown"
                    ):
                        try:
                            if ai_provider.lower() == "glm":
                                relevance = glm_check_job_relevance(
                                    aiClient,
                                    description,
                                    about_company=company,
                                    user_information_all=user_information_all,
                                )
                            else:
                                relevance = claude_check_job_relevance(
                                    aiClient,
                                    description,
                                    about_company=company,
                                    user_information_all=user_information_all,
                                )

                            # Relevance filtering / skip decision.
                            if ai_filter_jobs:
                                match_score = relevance.get("match_score")
                                relevance_reasons = relevance.get("reasons", "")
                                if match_score is not None:
                                    print_lg(
                                        f"AI job match score: {match_score}/100 (threshold {ai_min_match_score}). "
                                        f"Reason: {relevance_reasons}"
                                    )
                                    if (
                                        ai_min_match_score > 0
                                        and match_score < ai_min_match_score
                                    ):
                                        message = (
                                            f"AI match score {match_score} < {ai_min_match_score} "
                                            f"for '{title}' at '{company}'. Reason: {relevance_reasons}\n"
                                            f"Missing skills: {relevance.get('missing_skills')}"
                                        )
                                        print_lg(f"Skipping: AI match score {match_score} < {ai_min_match_score}.")
                                        failed_job(
                                            job_id,
                                            job_link,
                                            resume,
                                            date_listed,
                                            "AI: low relevance",
                                            message,
                                            "Skipped",
                                            screenshot_name,
                                        )
                                        rejected_jobs.add(job_id)
                                        skip_count += 1
                                        bridge.bump_counts(skipped=1)
                                        continue
                                else:
                                    print_lg(
                                        "AI relevance check returned no score; applying anyway.",
                                        relevance,
                                    )
                        except Exception as e:
                            # Fail open: if the AI screen errors, don't skip the job.
                            print_lg("Failed AI screen, applying anyway:", e)

                    # HR emails: saved for every job the bot applies to (a real score below the
                    # threshold already skipped the job above).
                    if should_collect_emails(ai_filter_jobs, match_score, ai_min_match_score):
                        found_emails = extract_emails(
                            f"{description if description != 'Unknown' else ''}\n{relevance.get('apply_email') or ''}"
                        )
                        if found_emails:
                            try:
                                added = bridge.save_emails(
                                    {"job_id": job_id, "title": title, "company": company, "job_link": job_link},
                                    found_emails,
                                    relevance.get("email_subject", "") or "",
                                )
                                print_lg(
                                    f"Found HR email(s) {', '.join(found_emails)} for \"{title} | {company}\" ({added} new)."
                                )
                            except Exception as e:
                                print_lg("Failed to save HR emails!", e)

                    uploaded = False
                    # Case 1: Easy Apply Button
                    is_easy_apply = click_displayed(driver, EASY_APPLY_BUTTON_XPATH)
                    if not is_easy_apply:
                        print_lg(
                            f'Didn\'t find a visible Easy Apply button for "{title} | {company}".'
                        )
                        save_debug_page("Easy Apply button not found")
                    # Fallback: the classic button with "Easy" in aria-label
                    if not is_easy_apply:
                        is_easy_apply = try_xp(
                            driver,
                            ".//button[contains(@class,'jobs-apply-button') and contains(@class, 'artdeco-button--3') and contains(@aria-label, 'Easy')]",
                        )
                    # Fallback 1: check if apply link contains Easy Apply URL pattern
                    if not is_easy_apply:
                        try:
                            apply_link_el = driver.find_element(
                                By.XPATH,
                                ".//a[contains(@href, 'openSDUIApplyFlow=true')]",
                            )
                            if apply_link_el:
                                apply_link_el.click()
                                is_easy_apply = True
                                print_lg(
                                    "Detected Easy Apply via URL pattern (openSDUIApplyFlow)"
                                )
                        except:
                            pass
                    # Fallback 2: click any Apply button and check if Easy Apply modal appears
                    if not is_easy_apply:
                        try:
                            apply_btn = driver.find_element(
                                By.XPATH,
                                ".//button[contains(@class,'jobs-apply-button')]",
                            )
                            if apply_btn:
                                tabs_before = len(driver.window_handles)
                                apply_btn.click()
                                buffer(click_gap)
                                tabs_after = len(driver.window_handles)
                                if tabs_after > tabs_before:
                                    # New tab opened — external apply, close it and go back
                                    driver.switch_to.window(driver.window_handles[-1])
                                    if (
                                        close_tabs
                                        and driver.current_window_handle != linkedIn_tab
                                    ):
                                        driver.close()
                                    driver.switch_to.window(linkedIn_tab)
                                    print_lg(
                                        "External apply detected via new tab, skipping"
                                    )
                                else:
                                    try:
                                        find_by_class(driver, "jobs-easy-apply-modal")
                                        is_easy_apply = True
                                        print_lg(
                                            "Detected Easy Apply via modal appearance after click"
                                        )
                                    except:
                                        # Modal didn't appear — dismiss
                                        try:
                                            actions.send_keys(Keys.ESCAPE).perform()
                                        except:
                                            pass
                        except:
                            pass
                    if is_easy_apply:
                        try:
                            # Find the dialog before the `try`/`finally` below, so its Review
                            # and Submit steps never run when the dialog didn't open.
                            errored = ""
                            try:
                                # Wait for the form, or LinkedIn's "may not be the best fit" prompt before it.
                                wait.until(
                                    EC.presence_of_element_located(
                                        (
                                            By.XPATH,
                                            f"{EASY_APPLY_MODAL_XPATH} | {APPLY_INTERCEPT_CONTINUE_XPATH}",
                                        )
                                    )
                                )
                                # The job filters already decided to apply, so continue past the prompt.
                                if click_displayed(driver, APPLY_INTERCEPT_CONTINUE_XPATH):
                                    print_lg(
                                        'LinkedIn says this job may not be the best fit, clicking "Continue applying".'
                                    )
                                modal = wait.until(
                                    EC.presence_of_element_located(
                                        (By.XPATH, EASY_APPLY_MODAL_XPATH)
                                    )
                                )
                            except TimeoutException:
                                save_debug_page("Easy Apply modal not found")
                                raise
                            try:
                                # Skip the contact info page. One-page forms have no "Next"; the loop below handles them.
                                wait_span_click(modal, "Next", 1, quiet=True)
                                resume = "Previous resume"
                                next_button = True
                                questions_list = set()
                                next_counter = 0
                                # Next/Review clicks in a row that left the form on the same page,
                                # which happens when required questions are unanswered.
                                failed_attempts = 0
                                while next_button:
                                    next_counter += 1
                                    if failed_attempts >= 2 or next_counter >= 15:
                                        if pause_at_failed_question:
                                            screenshot(
                                                driver,
                                                job_id,
                                                "Needed manual intervention for failed question",
                                            )
                                            pause_for_user(
                                                'Couldn\'t answer one or more questions. Please fill them in the live browser, then click "Continue" and the bot will carry on. DO NOT click Back, Next or Review in LinkedIn. (You can turn off "Pause at failed question" in Settings.)',
                                                "Help Needed",
                                                "Continue",
                                            )
                                            next_counter = 1
                                            failed_attempts = 0
                                            continue
                                        if questions_list:
                                            print_lg(
                                                "Stuck on one of these questions: "
                                                + "; ".join(sorted(str(q[0]) for q in questions_list))
                                            )
                                        screenshot_name = screenshot(
                                            driver, job_id, "Failed at questions"
                                        )
                                        errored = "stuck"
                                        raise Exception(
                                            "Seems like stuck in a continuous loop of next, probably because of new questions."
                                        )
                                    # Save each kind of form page once, to adapt to LinkedIn's form changes.
                                    try:
                                        page_title = modal.find_element(
                                            By.XPATH, EASY_APPLY_PAGE_TITLE_XPATH
                                        ).text
                                    except NoSuchElementException:
                                        page_title = "Untitled"
                                    save_debug_page(f"Easy Apply page - {page_title}")
                                    questions_list = answer_questions(
                                        modal,
                                        questions_list,
                                        work_location,
                                        job_description=description,
                                    )
                                    if useNewResume and not uploaded:
                                        uploaded, resume = upload_resume(
                                            modal, default_resume_path
                                        )
                                    try:
                                        next_button = modal.find_element(
                                            By.XPATH,
                                            './/span[normalize-space(.)="Review"]',
                                        )
                                    except NoSuchElementException:
                                        next_button = modal.find_element(
                                            By.XPATH,
                                            './/button[contains(span, "Next")]',
                                        )
                                    page_before = form_page_key(modal)
                                    try:
                                        next_button.click()
                                    except ElementClickInterceptedException:
                                        break  # Happens when it tries to click Next button in About Company photos section
                                    buffer(click_gap)
                                    try:
                                        WebDriverWait(driver, 3).until(
                                            lambda _: form_page_key(modal) != page_before
                                        )
                                        failed_attempts = 0
                                    except TimeoutException:
                                        failed_attempts += 1
                                        print_lg(
                                            f"Form didn't move on after clicking Next/Review (attempt {failed_attempts} of 2), probably unanswered required questions."
                                        )

                            except NoSuchElementException:
                                errored = "nose"
                            finally:
                                if questions_list and errored != "stuck":
                                    print_lg(f"Answered {len(questions_list)} question(s).")
                                # Already on the review step when the loop above ended there.
                                wait_span_click(driver, "Review", 1, scrollTop=True, quiet=True)
                                cur_pause_before_submit = pause_before_submit
                                # Set "Follow <Company>" now so the pause shows it as it'll be sent.
                                follow_company(modal)
                                if errored != "stuck" and cur_pause_before_submit:
                                    decision = pyautogui.confirm(
                                        '1. Please verify your information.\n2. If you edited something, please return to this final screen.\n3. DO NOT CLICK "Submit Application".\n\n\n\n\nYou can turn off "Pause before submit" in Settings\nTo TEMPORARILY disable pausing, click "Disable Pause"',
                                        "Confirm your information",
                                        # "Disable Pause" isn't first: pressing Enter in the terminal picks the first button.
                                        [
                                            "Submit Application",
                                            "Discard Application",
                                            "Disable Pause",
                                        ],
                                    )
                                    if decision == "Discard Application":
                                        raise Exception(DISCARDED_BY_USER)
                                    pause_before_submit = (
                                        False if "Disable Pause" == decision else True
                                    )
                                follow_company(modal)
                                submitted_successfully = False
                                if wait_span_click(
                                    driver, "Submit application", 2, scrollTop=True
                                ):
                                    date_applied = datetime.now()
                                    submitted_successfully = True
                                    close_after_submit(driver, actions)
                                elif (
                                    errored != "stuck"
                                    and cur_pause_before_submit
                                    and "Yes"
                                    in pyautogui.confirm(
                                        "You submitted the application, didn't you 😒?",
                                        "Failed to find Submit Application!",
                                        ["Yes", "No"],
                                    )
                                ):
                                    date_applied = datetime.now()
                                    submitted_successfully = True
                                    close_after_submit(driver, actions)
                                else:
                                    print_lg(
                                        "Since, Submit Application failed, discarding the job application..."
                                    )
                                    save_debug_page("Submit application not found")
                                    if errored == "nose":
                                        raise Exception(
                                            "Failed to click Submit application 😑"
                                        )
                                if submitted_successfully:
                                    buffer(post_submit_timeout)

                        except Exception as e:
                            print_lg("Failed to Easy apply!")
                            critical_error_log("Somewhere in Easy Apply process", e)
                            failed_job(
                                job_id,
                                job_link,
                                resume,
                                date_listed,
                                easy_apply_failure_reason(e),
                                e,
                                application_link,
                                screenshot_name,
                            )
                            failed_count += 1
                            bridge.bump_counts(failed=1)
                            discard_job()
                            continue
                    else:
                        # Case 2: Apply externally
                        skip, application_link, tabs_count = external_apply(
                            pagination_element,
                            job_id,
                            job_link,
                            resume,
                            date_listed,
                            application_link,
                            screenshot_name,
                        )
                        if dailyEasyApplyLimitReached:
                            print_lg("Daily application limit for Easy Apply is reached!")
                            return
                        if skip:
                            continue

                    submitted_jobs(
                        job_id,
                        title,
                        company,
                        work_location,
                        work_style,
                        description,
                        experience_required,
                        skills,
                        hr_name,
                        hr_link,
                        resume,
                        reposted,
                        date_listed,
                        date_applied,
                        job_link,
                        application_link,
                        questions_list,
                        connect_request,
                    )
                    if uploaded:
                        useNewResume = False

                    print_lg(
                        f'Successfully saved "{title} | {company}" job. Job ID: {job_id} info'
                    )
                    current_count += 1
                    bridge.bump_counts(applied=1)
                    if application_link == "Easy Applied":
                        easy_applied_count += 1
                    else:
                        external_jobs_count += 1
                    applied_jobs.add(job_id)

                    if (
                        applications_before_search_prompt > 0
                        and current_count >= applications_before_search_prompt
                        and current_count % applications_before_search_prompt == 0
                    ):
                        if (
                            pyautogui.confirm(
                                f'You have applied to {current_count} job(s) for "{searchTerm}".\nMove to the next search term?',
                                "Switch search term?",
                                ["Yes, next search term", "No, keep applying"],
                            )
                            == "Yes, next search term"
                        ):
                            switch_to_next_search = True
                            break
                        current_count = 0

                if switch_to_next_search:
                    print_lg(f'Moving to the next search term after "{searchTerm}".')
                    break

                # Past this point LinkedIn only shows "related" jobs that ignore the filters.
                if driver.find_elements(By.XPATH, RELATED_RESULTS_MARKER_XPATH):
                    print_lg(
                        "Reached LinkedIn's \"more results related to your search\" list (it ignores your filters); moving on."
                    )
                    break

                # Switching to next page
                if pagination_element == None:
                    print_lg(
                        "Couldn't find pagination element, probably at the end page of results!"
                    )
                    break
                next_page = current_page + 1
                # Only a window of page numbers is shown, so fall back to the "Next" button.
                next_page_button = try_xp(
                    driver, page_button_xpath(next_page), False
                ) or try_xp(driver, NEXT_PAGE_BUTTON_XPATH, False)
                if not next_page_button:
                    print_lg(
                        f"Didn't find page {next_page}, probably the last page of results."
                    )
                    break
                next_page_button.click()
                # Wait for the new page, so the old page's job cards aren't read again.
                wait.until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            page_button_xpath(next_page) + "[@aria-current='true']",
                        )
                    )
                )
                print_lg(f">-> Now on page {next_page}")

        except Exception as e:
            if is_browser_gone(e):
                print_lg(
                    "Browser window closed or session is invalid. Ending application process.",
                    e,
                )
                raise e  # Re-raise to be caught by main
            print_lg("Failed to find Job listings!")
            critical_error_log("In Applier", e)
            save_debug_page("Job listings error")


def run(total_runs: int) -> int:
    if dailyEasyApplyLimitReached:
        return total_runs
    print_lg(
        f"==== Cycle {total_runs}: jobs posted within '{date_posted or 'Any time'}', sorted by '{sort_by or 'LinkedIn default'}' ===="
    )
    apply_to_jobs(search_terms)
    if not dailyEasyApplyLimitReached:
        print_lg("Sleeping for 10 min...")
        sleep(300)
        print_lg("Few more min... Gonna start with in next 5 min...")
        sleep(300)
    buffer(3)
    return total_runs + 1


linkedIn_tab = False


def main() -> str | None:
    """Runs the bot. Returns the fatal error message, or None when it ended normally."""
    total_runs = 1
    fatal_error = None
    try:
        global linkedIn_tab, tabs_count, useNewResume, aiClient
        alert_title = "Error Occurred. Closing Browser!"
        validate_config()

        if not os.path.exists(default_resume_path):
            print_lg(
                "No resume uploaded (Settings → Resume), so the bot will use your previous upload on LinkedIn."
            )
            useNewResume = False

        # Login to LinkedIn
        tabs_count = len(driver.window_handles)
        driver.get("https://www.linkedin.com/login")
        if not is_logged_in_LN():
            bridge.record_session("logged_out")
            login_LN()
        bridge.record_session("logged_in" if is_logged_in_LN() else "logged_out")

        linkedIn_tab = driver.current_window_handle

        if use_AI:
            if ai_provider == "claude":
                aiClient = claude_create_client()
            elif ai_provider == "glm":
                aiClient = glm_create_client()

            try:
                about_company_for_ai = " ".join(
                    [
                        word
                        for word in (first_name + " " + last_name).split()
                        if len(word) > 3
                    ]
                )
                print_lg(
                    f"Extracted about company info for AI: '{about_company_for_ai}'"
                )
            except Exception as e:
                print_lg("Failed to extract about company info!", e)

        # Start applying to jobs
        driver.switch_to.window(linkedIn_tab)
        total_runs = run(total_runs)
        while run_non_stop:
            if cycle_date_posted:
                date_options = ["Any time", "Past month", "Past week", "Past 24 hours"]
                global date_posted
                date_posted = (
                    date_options[
                        (
                            date_options.index(date_posted) + 1
                            if date_options.index(date_posted) + 1 > len(date_options)
                            else -1
                        )
                    ]
                    if stop_date_cycle_at_24hr
                    else date_options[
                        (
                            0
                            if date_options.index(date_posted) + 1 >= len(date_options)
                            else date_options.index(date_posted) + 1
                        )
                    ]
                )
            if alternate_sortby:
                global sort_by
                sort_by = (
                    "Most recent" if sort_by == "Most relevant" else "Most relevant"
                )
                total_runs = run(total_runs)
                sort_by = (
                    "Most recent" if sort_by == "Most relevant" else "Most relevant"
                )
            total_runs = run(total_runs)
            if dailyEasyApplyLimitReached:
                break

    except Exception as e:
        if is_browser_gone(e):
            print_lg("Browser window closed or session is invalid. Exiting.", e)
            fatal_error = f"The browser closed or crashed: {e}"
        else:
            critical_error_log("In Applier Main", e)
            pyautogui.alert(e, alert_title)
            fatal_error = str(e)
    finally:
        summary = "Total runs: {}\nJobs Easy Applied: {}\nExternal job links collected: {}\nTotal applied or collected: {}\nFailed jobs: {}\nIrrelevant jobs skipped: {}\n".format(
            total_runs,
            easy_applied_count,
            external_jobs_count,
            easy_applied_count + external_jobs_count,
            failed_count,
            skip_count,
        )
        # The exit alert below shows the summary.
        if randomly_answered_questions:
            print_lg(
                "Questions answered randomly: "
                + "; ".join(str(question) for question in randomly_answered_questions)
            )
        quotes = choice(
            [
                "Never quit. You're one step closer than before. - Sai Vignesh Golla",
                "All the best with your future interviews, you've got this. - Sai Vignesh Golla",
                "Keep up with the progress. You got this. - Sai Vignesh Golla",
                "If you're tired, learn to take rest but never give up. - Sai Vignesh Golla",
                "Success is not final, failure is not fatal, It is the courage to continue that counts. - Winston Churchill (Not a sponsor)",
                "Believe in yourself and all that you are. Know that there is something inside you that is greater than any obstacle. - Christian D. Larson (Not a sponsor)",
                "Every job is a self-portrait of the person who does it. Autograph your work with excellence. - Jessica Guidobono (Not a sponsor)",
                "The only way to do great work is to love what you do. If you haven't found it yet, keep looking. Don't settle. - Steve Jobs (Not a sponsor)",
                "Opportunities don't happen, you create them. - Chris Grosser (Not a sponsor)",
                "The road to success and the road to failure are almost exactly the same. The difference is perseverance. - Colin R. Davis (Not a sponsor)",
                "Obstacles are those frightful things you see when you take your eyes off your goal. - Henry Ford (Not a sponsor)",
                "The only limit to our realization of tomorrow will be our doubts of today. - Franklin D. Roosevelt (Not a sponsor)",
            ]
        )
        sponsors = "Be the first to have your name here!"
        timeSaved = (
            (easy_applied_count * 80) + (external_jobs_count * 20) + (skip_count * 10)
        )
        timeSavedMsg = ""
        if timeSaved > 0:
            timeSaved += 60
            timeSavedMsg = f"In this run, you saved approx {round(timeSaved/60)} mins ({timeSaved} secs), please consider supporting the project."
        msg = f"{quotes}\n\n\n{timeSavedMsg}\nYou can also get your quote and name shown here, or prioritize your bug reports by supporting the project at:\n\nhttps://github.com/sponsors/GodsScion\n\n\nSummary:\n{summary}\n\n\nBest regards,\nSai Vignesh Golla\nhttps://www.linkedin.com/in/saivigneshgolla/\n\nTop Sponsors:\n{sponsors}"
        pyautogui.alert(msg, "Exiting..")
        print_lg("Closing the browser...")
        if tabs_count >= 10:
            msg = "NOTE: IF YOU HAVE MORE THAN 10 TABS OPENED, PLEASE CLOSE OR BOOKMARK THEM!\n\nOr it's highly likely that application will just open browser and not do anything next time!"
            pyautogui.alert(msg, "Info")
            print_lg(msg)
        ##> ------ Yang Li : MARKYangL - Feature ------
        if use_AI and aiClient:
            try:
                if ai_provider.lower() == "claude":
                    claude_close_client(aiClient)
                elif ai_provider.lower() == "glm":
                    glm_close_client(aiClient)
                print_lg(f"Closed {ai_provider} AI client.")
            except Exception as e:
                print_lg("Failed to close AI client:", e)
        ##<
        try:
            if driver:
                driver.quit()
        except WebDriverException as e:
            print_lg("Browser already closed.", e)
        except Exception as e:
            critical_error_log("When quitting...", e)


    return fatal_error


if __name__ == "__main__":
    error = main()
    if error:
        # Last line of the log: the worker shows it as the reason the run failed.
        print_lg(f"Run failed: {error}")
        raise SystemExit(1)
