'''
Author:     Sai Vignesh Golla
LinkedIn:   https://www.linkedin.com/in/saivigneshgolla/

Copyright (C) 2024 Sai Vignesh Golla

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html

GitHub:     https://github.com/GodsScion/Auto_job_applier_linkedIn

version:    26.01.20.5.08
'''

# Settings are edited in the web UI (Settings page) and secrets in `.env`; the API already
# validates types on save, so this mainly catches required values that are still empty.

__validation_file_path = ""


def check_int(var: int, var_name: str, min_value: int=0) -> bool | TypeError | ValueError:
    if not isinstance(var, int) or isinstance(var, bool): raise TypeError(f'The setting "{var_name}" in {__validation_file_path} must be a whole number, not "{var}".')
    if var < min_value: raise ValueError(f'The setting "{var_name}" in {__validation_file_path} must be at least {min_value}, not {var}.')
    return True


def check_boolean(var: bool, var_name: str) -> bool | ValueError:
    if var == True or var == False: return True
    raise ValueError(f'The setting "{var_name}" in {__validation_file_path} must be on or off, not "{var}".')


def check_string(var: str, var_name: str, options: list=[], min_length: int=0) -> bool | TypeError | ValueError:
    if not isinstance(var, str): raise TypeError(f'Invalid value for "{var_name}" in {__validation_file_path}: expected text.')
    if min_length > 0 and len(var) < min_length: raise ValueError(f'"{var_name}" in {__validation_file_path} is required (at least {min_length} characters). Fill it in and start again.')
    if len(options) > 0 and var not in options: raise ValueError(f'Invalid value for "{var_name}" in {__validation_file_path}: expected one of {options}, not "{var}".')
    return True


def check_list(var: list, var_name: str, options: list=[], min_length: int=0) -> bool | TypeError | ValueError:
    if not isinstance(var, list):
        raise TypeError(f'Invalid value for "{var_name}" in {__validation_file_path}: expected a list.')
    if len(var) < min_length: raise ValueError(f'"{var_name}" in {__validation_file_path} needs at least {min_length} entr{"y" if min_length == 1 else "ies"}.')
    for element in var:
        if not isinstance(element, str): raise TypeError(f'Invalid value for "{var_name}" in {__validation_file_path}: every entry must be text.')
        if len(options) > 0 and element not in options: raise ValueError(f'Invalid value for "{var_name}" in {__validation_file_path}: "{element}" is not one of {options}.')
    return True


def check_secret(var: str, var_name: str, env_var: str, min_length: int) -> bool | ValueError:
    if not isinstance(var, str) or len(var.strip()) < min_length:
        raise ValueError(f'{env_var} is not set in .env (needed for "{var_name}"). Add it to .env and run `make up`.')
    return True


from config.personals import *
def validate_personals() -> None | ValueError | TypeError:
    global __validation_file_path
    __validation_file_path = "Settings → Personals"

    check_string(first_name, "first_name", min_length=1)
    check_string(middle_name, "middle_name")
    check_string(last_name, "last_name", min_length=1)

    check_string(phone_number, "phone_number", min_length=10)

    check_string(current_city, "current_city")

    check_string(street, "street")
    check_string(state, "state")
    check_string(zipcode, "zipcode")
    check_string(country, "country")

    check_string(ethnicity, "ethnicity", ["", "Decline", "Hispanic/Latino", "American Indian or Alaska Native", "Asian", "Black or African American", "Native Hawaiian or Other Pacific Islander", "White", "Other"])
    check_string(gender, "gender", ["Male", "Female", "Other", "Decline", ""])
    check_string(disability_status, "disability_status", ["Yes", "No", "Decline"])
    check_string(veteran_status, "veteran_status", ["Yes", "No", "Decline"])


from config.questions import *
def validate_questions() -> None | ValueError | TypeError:
    global __validation_file_path
    __validation_file_path = "Settings → Questions"

    check_string(years_of_experience, "years_of_experience")
    check_string(require_visa, "require_visa", ["Yes", "No"])
    check_string(website, "website")
    check_string(linkedIn, "linkedIn")
    check_int(desired_salary, "desired_salary")
    check_string(us_citizenship, "us_citizenship", ["U.S. Citizen/Permanent Resident", "Non-citizen allowed to work for any employer", "Non-citizen allowed to work for current employer", "Non-citizen seeking work authorization", "Canadian Citizen/Permanent Resident", "Other"])
    check_string(linkedin_headline, "linkedin_headline")
    check_int(hourly_rate, "hourly_rate")
    check_int(notice_period, "notice_period")
    check_int(current_ctc, "current_ctc")
    check_string(linkedin_summary, "linkedin_summary")
    check_string(cover_letter, "cover_letter")
    check_string(recent_employer, "recent_employer")
    check_string(confidence_level, "confidence_level")

    check_boolean(pause_before_submit, "pause_before_submit")
    check_boolean(pause_at_failed_question, "pause_at_failed_question")
    check_boolean(overwrite_previous_answers, "overwrite_previous_answers")
    if not isinstance(custom_answers, list) or not all(isinstance(a, dict) and a.get("match") for a in custom_answers):
        raise ValueError(f'Invalid value for "custom_answers" in {__validation_file_path}.')


from config.search import *
def validate_search() -> None | ValueError | TypeError:
    global __validation_file_path
    __validation_file_path = "Settings → Search"

    check_list(search_terms, "search_terms", min_length=1)
    check_string(search_location, "search_location")
    check_int(switch_number, "switch_number", 1)
    check_int(applications_before_search_prompt, "applications_before_search_prompt", -1)
    check_boolean(randomize_search_order, "randomize_search_order")

    check_string(sort_by, "sort_by", ["", "Most recent", "Most relevant"])
    check_string(date_posted, "date_posted", ["", "Any time", "Past month", "Past week", "Past 24 hours"])
    check_string(salary, "salary")

    check_boolean(easy_apply_only, "easy_apply_only")

    check_list(experience_level, "experience_level", ["Internship", "Entry level", "Associate", "Mid-Senior level", "Director", "Executive"])
    check_list(job_type, "job_type", ["Full-time", "Part-time", "Contract", "Temporary", "Volunteer", "Internship", "Other"])
    check_list(on_site, "on_site", ["On-site", "Remote", "Hybrid"])

    check_list(companies, "companies")
    check_list(location, "location")
    check_list(industry, "industry")
    check_list(job_function, "job_function")
    check_list(job_titles, "job_titles")
    check_list(benefits, "benefits")
    check_list(commitments, "commitments")

    check_boolean(under_10_applicants, "under_10_applicants")
    check_boolean(in_your_network, "in_your_network")
    check_boolean(fair_chance_employer, "fair_chance_employer")

    check_boolean(pause_after_filters, "pause_after_filters")

    check_list(about_company_bad_words, "about_company_bad_words")
    check_list(about_company_good_words, "about_company_good_words")
    check_list(bad_words, "bad_words")
    check_boolean(security_clearance, "security_clearance")
    check_boolean(did_masters, "did_masters")
    check_int(current_experience, "current_experience", -1)
    check_boolean(ai_filter_jobs, "ai_filter_jobs")
    check_int(ai_min_match_score, "ai_min_match_score", 0)


from config.secrets import *
def validate_secrets() -> None | ValueError | TypeError:
    global __validation_file_path
    __validation_file_path = "Settings → AI"

    # LinkedIn credentials are optional: without them you log in yourself in the live browser.
    check_string(username, "username")
    check_string(password, "password")

    check_boolean(use_AI, "use_AI")
    check_string(ai_provider, "ai_provider", ["claude", "glm"])
    if use_AI:
        if ai_provider == "claude":
            check_secret(claude_api_key, "claude_api_key", "CLAUDE_API_KEY", 10)
            check_string(claude_model, "claude_model", min_length=5)
        elif ai_provider == "glm":
            check_secret(glm_api_key, "glm_api_key", "GLM_API_KEY", 10)
            check_string(glm_model, "glm_model", min_length=3)
            check_string(glm_api_url, "glm_api_url", min_length=5)


from config.settings import *
def validate_settings() -> None | ValueError | TypeError:
    global __validation_file_path
    __validation_file_path = "Settings → Bot"

    check_boolean(close_tabs, "close_tabs")
    check_boolean(follow_companies, "follow_companies")
    check_boolean(run_non_stop, "run_non_stop")
    check_boolean(alternate_sortby, "alternate_sortby")
    check_boolean(cycle_date_posted, "cycle_date_posted")
    check_boolean(stop_date_cycle_at_24hr, "stop_date_cycle_at_24hr")

    check_int(click_gap, "click_gap", 0)
    check_int(post_submit_timeout, "post_submit_timeout", 0)

    check_boolean(run_in_background, "run_in_background")
    check_boolean(disable_extensions, "disable_extensions")
    check_boolean(safe_mode, "safe_mode")
    check_boolean(smooth_scroll, "smooth_scroll")
    check_boolean(stealth_mode, "stealth_mode")


def validate_config() -> bool | ValueError | TypeError:
    '''
    Runs all validation functions to validate all settings.
    '''
    validate_personals()
    validate_questions()
    validate_search()
    validate_secrets()
    validate_settings()
    return True
