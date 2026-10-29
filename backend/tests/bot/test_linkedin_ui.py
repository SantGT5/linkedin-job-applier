"""
Selectors and parsers for LinkedIn's AI-powered jobs search page, checked against
tests/fixtures/search_results_page.html with lxml (XPath 1.0, like Selenium).
"""

import os

from lxml import html
from selenium.common.exceptions import NoSuchElementException

from modules import linkedin_ui as ui


def text_of(element) -> str:
    return " ".join(element.text_content().split())


def first(context, xpath: str):
    matches = context.xpath(xpath)
    assert matches, f"No match for {xpath}"
    return matches[0]


# Job list


def test_job_cards_xpath_finds_every_card(search_page):
    cards = search_page.xpath(ui.JOB_CARDS_XPATH)
    assert [card.get("componentkey") for card in cards] == [
        "job-card-component-ref-1000000001",
        "job-card-component-ref-1000000002",
        "job-card-component-ref-1000000003",
    ]


def test_job_id_from_card_key():
    assert ui.job_id_from_card_key("job-card-component-ref-4477006723") == "4477006723"


def test_job_card_xpath_finds_one_card_by_id(search_page):
    cards = search_page.xpath(ui.job_card_xpath("1000000002"))
    assert len(cards) == 1
    assert cards[0].get("componentkey") == "job-card-component-ref-1000000002"


def test_card_title_skips_screen_reader_text(search_page):
    card = first(search_page, ui.job_card_xpath("1000000001"))
    assert text_of(first(card, ui.CARD_TITLE_XPATH)) == "Senior Python Developer"


def test_card_company_and_location(search_page):
    card = first(search_page, ui.job_card_xpath("1000000002"))
    assert text_of(first(card, ui.CARD_COMPANY_XPATH)) == "Globex"
    assert text_of(first(card, ui.CARD_LOCATION_XPATH)) == "Berlin, Germany (Hybrid)"


def test_card_applied_state(search_page):
    def applied(job_id):
        card = first(search_page, ui.job_card_xpath(job_id))
        return bool(card.xpath(ui.CARD_APPLIED_XPATH))

    assert applied("1000000003")
    # "Applied Data Engineer" is a job title, not the applied state.
    assert not applied("1000000002")
    assert not applied("1000000001")


def test_split_work_location():
    assert ui.split_work_location("United States (Remote)") == ("United States", "Remote")
    assert ui.split_work_location("Berlin, Germany (Hybrid)") == ("Berlin, Germany", "Hybrid")
    assert ui.split_work_location("Toronto, ON") == ("Toronto, ON", "")


# Job details panel


def test_job_details_loaded_for_selected_job_only(search_page):
    assert search_page.xpath(ui.job_details_loaded_xpath("1000000001"))
    assert not search_page.xpath(ui.job_details_loaded_xpath("1000000002"))


def test_time_posted_in_details(search_page):
    details = first(search_page, ui.JOB_DETAILS_XPATH)
    assert text_of(first(details, ui.TIME_POSTED_XPATH)) == "15 hours ago"


def test_about_company(search_page):
    about = first(search_page, ui.about_company_xpath("1000000001"))
    assert "Acme Robotics builds warehouse robots." in text_of(about)


def test_about_job_description(search_page):
    about = first(search_page, ui.about_job_xpath("1000000001"))
    assert ui.clean_description(about.text_content()) == (
        "We build robots.Requirements: 5+ years of Python."
    )


def test_about_job_description_without_expandable_box():
    # Short descriptions may not be wrapped in the expandable "… more" text box.
    page = html.fromstring(
        "<div id='JobDetails_AboutTheJob_42'><h2>About the job</h2>"
        "<p>Short description.</p></div>"
    )
    about = first(page, ui.about_job_xpath("42"))
    assert ui.clean_description(about.text_content()) == "Short description."


def test_clean_description_strips_heading_and_more_button():
    assert ui.clean_description("About the job\nLine one\nLine two\n…\nmore\n") == (
        "Line one\nLine two"
    )
    assert ui.clean_description("Line one …more") == "Line one"
    assert ui.clean_description("Need more") == "Need more"
    assert ui.clean_description("About the jobs we offer") == "About the jobs we offer"


def test_hiring_team_link_skips_other_people(search_page):
    link = first(search_page, ui.hiring_team_link_xpath("1000000001"))
    assert link.get("href") == "https://www.linkedin.com/in/jane-hirer/"
    assert text_of(first(link, ui.HIRER_NAME_XPATH)) == "Jane Hirer"


def test_easy_apply_button(search_page):
    button = first(search_page, ui.EASY_APPLY_BUTTON_XPATH)
    assert text_of(button) == "Easy Apply"


# Pagination


def test_current_page(search_page):
    pagination = first(search_page, ui.PAGINATION_XPATH)
    assert text_of(first(pagination, ui.CURRENT_PAGE_XPATH)) == "1"


def test_page_button(search_page):
    assert text_of(first(search_page, ui.page_button_xpath(2))) == "2"
    assert not search_page.xpath(ui.page_button_xpath(4))


def test_next_page_button(search_page):
    assert text_of(first(search_page, ui.NEXT_PAGE_BUTTON_XPATH)) == "Next"


# Easy Apply dialog


def easy_apply_page():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "easy_apply_contact_info.html")
    with open(path, encoding="utf-8") as file:
        return html.fromstring(file.read())


def test_easy_apply_modal():
    modals = easy_apply_page().xpath(ui.EASY_APPLY_MODAL_XPATH)
    assert len(modals) == 1
    assert modals[0].tag == "dialog"


def test_form_questions_are_one_per_field():
    modal = first(easy_apply_page(), ui.EASY_APPLY_MODAL_XPATH)
    questions = modal.xpath(ui.FORM_QUESTIONS_XPATH)
    labels = [ui.question_label_text(q.xpath(".//label")[0].text_content()) for q in questions]
    assert labels == ["Email address", "Phone country code", "Mobile phone number"]
    assert [len(q.xpath(ui.FORM_TEXT_INPUT_XPATH)) for q in questions] == [0, 0, 1]


def test_easy_apply_progress():
    modal = first(easy_apply_page(), ui.EASY_APPLY_MODAL_XPATH)
    assert first(modal, ui.EASY_APPLY_PROGRESS_XPATH).get("aria-valuenow") == "25"


def test_question_label_text():
    assert ui.question_label_text("Email address*") == "Email address"
    assert ui.question_label_text("  Years of Python experience? *\n") == "Years of Python experience?"
    assert ui.question_label_text("Website") == "Website"


def test_easy_apply_page_title():
    modal = first(easy_apply_page(), ui.EASY_APPLY_MODAL_XPATH)
    assert text_of(first(modal, ui.EASY_APPLY_PAGE_TITLE_XPATH)) == "Contact info"


class SeleniumLike:
    """Test-only adapter: exposes an lxml element through the WebElement calls `question_label` uses."""

    def __init__(self, element):
        self.element = element

    def find_element(self, by, xpath):
        matches = self.element.xpath(xpath)
        if not matches:
            raise NoSuchElementException(xpath)
        return SeleniumLike(matches[0])

    @property
    def text(self):
        return " ".join(self.element.text_content().split())

    def get_attribute(self, name):
        return self.element.get(name)


def additional_questions():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "easy_apply_additional_questions.html")
    with open(path, encoding="utf-8") as file:
        modal = first(html.fromstring(file.read()), ui.EASY_APPLY_MODAL_XPATH)
    return modal.xpath(ui.FORM_QUESTIONS_XPATH)


def test_form_questions_include_unlabelled_fields():
    questions = additional_questions()
    controls = [first(q, ui.FORM_TEXT_INPUT_XPATH + " | .//textarea") for q in questions]
    assert [c.get("id") for c in controls] == ["_r_6n_", "_r_6o_", "_r_5v_", "_r_66_"]


def test_question_label_falls_back_to_aria_label_then_paragraph():
    labels = [
        ui.question_label(
            SeleniumLike(q), SeleniumLike(first(q, ui.FORM_TEXT_INPUT_XPATH + " | .//textarea"))
        )
        for q in additional_questions()
    ]
    assert labels == [
        "How many years of work experience do you have with Python?",
        "How many years of work experience do you have with Django?",
        "Location (city)",
        "Summary",
    ]


def test_question_label_prefers_label_element():
    modal = first(easy_apply_page(), ui.EASY_APPLY_MODAL_XPATH)
    phone = modal.xpath(ui.FORM_QUESTIONS_XPATH)[2]
    control = SeleniumLike(first(phone, ui.FORM_TEXT_INPUT_XPATH))
    assert ui.question_label(SeleniumLike(phone), control) == "Mobile phone number"


def test_apply_intercept_continue_link():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "apply_intercept.html")
    with open(path, encoding="utf-8") as file:
        page = html.fromstring(file.read())
    links = page.xpath(ui.APPLY_INTERCEPT_CONTINUE_XPATH)
    assert [text_of(link) for link in links] == ["Continue applying"]
    # The prompt is not the Easy Apply form itself.
    assert not page.xpath(ui.EASY_APPLY_MODAL_XPATH)
    assert not easy_apply_page().xpath(ui.APPLY_INTERCEPT_CONTINUE_XPATH)


def radio_question():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "easy_apply_radio_questions.html")
    with open(path, encoding="utf-8") as file:
        modal = first(html.fromstring(file.read()), ui.EASY_APPLY_MODAL_XPATH)
    return modal, modal.xpath(ui.FORM_QUESTIONS_XPATH)


def test_radio_options_carry_question_and_option_text():
    modal, questions = radio_question()
    assert [q.tag for q in questions] == ["fieldset"]
    options = questions[0].xpath(ui.RADIO_OPTIONS_XPATH)
    assert [text_of(o) for o in options] == ["Yes", "No"]
    assert options[0].get("aria-label") == "Do you have at least 5 years of experience with Python?"


def test_radio_option_of_input_and_by_answer():
    modal, questions = radio_question()
    no_input = questions[0].xpath(".//input[@id='_r_5l_']")[0]
    assert text_of(first(no_input, ui.RADIO_OPTION_OF_INPUT_XPATH)) == "No"
    assert text_of(first(questions[0], ui.radio_option_xpath("No"))) == "No"
    assert not questions[0].xpath(ui.radio_option_xpath("Maybe"))


def test_form_page_key():
    assert ui.form_page_key(SeleniumLike(first(easy_apply_page(), ui.EASY_APPLY_MODAL_XPATH))) == (
        "25",
        "Contact info",
    )
    modal, _ = radio_question()
    assert ui.form_page_key(SeleniumLike(modal)) == ("75", "Additional Questions")
    # A page without progress or title still gets a key, for comparing before and after a click.
    assert ui.form_page_key(SeleniumLike(html.fromstring("<dialog></dialog>"))) == (None, None)


def _login_page():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "login_page.html")
    with open(path, encoding="utf-8") as file:
        return html.fromstring(file.read())


def test_login_inputs_found_without_english_text():
    # Captured from the worker (LinkedIn served it in Dutch): ids are random, no "Sign in" text.
    page = _login_page()
    emails = page.xpath(ui.LOGIN_EMAIL_INPUT_XPATH)
    passwords = page.xpath(ui.LOGIN_PASSWORD_INPUT_XPATH)
    assert emails and all(e.get("type") == "email" for e in emails)
    assert passwords and all(p.get("type") == "password" for p in passwords)


def test_login_inputs_match_classic_form():
    page = html.fromstring(
        '<form><input id="username" name="session_key" type="text">'
        '<input id="password" name="session_password" type="password"></form>'
    )
    assert len(page.xpath(ui.LOGIN_EMAIL_INPUT_XPATH)) == 1
    assert len(page.xpath(ui.LOGIN_PASSWORD_INPUT_XPATH)) == 1


def _review_page():
    # Captured "Apply to <company>" step (one-page form), PII replaced. Root cause of the
    # Follow bug: LinkedIn dropped `input#follow-company-checkbox`; the control is now a
    # role="checkbox" div labelled "Follow <Company> to stay up to date with their page".
    path = os.path.join(os.path.dirname(__file__), "fixtures", "easy_apply_review.html")
    with open(path, encoding="utf-8") as file:
        return html.fromstring(file.read())


def test_follow_checkbox_found_on_review_page():
    page = _review_page()
    boxes = page.xpath(ui.FOLLOW_COMPANY_CHECKBOX_XPATH)
    assert len(boxes) == 1
    assert boxes[0].tag == "input" and boxes[0].get("type") == "checkbox"
    target = page.xpath(ui.FOLLOW_COMPANY_LABEL_XPATH)
    assert len(target) == 1 and "to stay up to date" in target[0].text_content()


def test_follow_label_clickable_target():
    page = _review_page()
    target = page.xpath(ui.FOLLOW_COMPANY_LABEL_XPATH)[0]
    assert target.get("role") == "checkbox" and target.get("tabindex") == "0"
    # Ticked by default: the bot must untick it when follow_companies is off.
    assert ui.follow_checked(target) is True
    # The hidden input sits inside the clickable target.
    assert target.xpath(".//input[@type='checkbox']")


def test_follow_xpaths_still_match_old_markup():
    page = html.fromstring(
        '<div><input id="follow-company-checkbox" type="checkbox" checked>'
        '<label for="follow-company-checkbox">Follow Acme to stay up to date with their page</label></div>'
    )
    assert len(page.xpath(ui.FOLLOW_COMPANY_CHECKBOX_XPATH)) == 1
    assert page.xpath(ui.FOLLOW_COMPANY_LABEL_XPATH)[0].tag == "label"


def test_follow_native_checkbox():
    # 2026-10-29: the aria-label moved onto a hidden native input; the visible target is its <label>.
    markup = (
        '<div><div><input id="_r_g0_" aria-label="Follow Acme to stay up to date with their page" '
        'type="checkbox"{}><label for="_r_g0_"></label></div><p>Follow Acme to stay up to date with their page</p></div>'
    )
    page = html.fromstring(markup.format(' checked=""'))
    targets = page.xpath(ui.FOLLOW_COMPANY_LABEL_XPATH)
    boxes = page.xpath(ui.FOLLOW_COMPANY_CHECKBOX_XPATH)
    assert [(t.tag, t.get("for")) for t in targets] == [("label", "_r_g0_")]
    assert [b.get("id") for b in boxes] == ["_r_g0_"]
    assert ui.follow_checked(targets[0], boxes[0]) is True
    page = html.fromstring(markup.format(""))
    assert ui.follow_checked(page.xpath(ui.FOLLOW_COMPANY_LABEL_XPATH)[0], page.xpath(ui.FOLLOW_COMPANY_CHECKBOX_XPATH)[0]) is False
