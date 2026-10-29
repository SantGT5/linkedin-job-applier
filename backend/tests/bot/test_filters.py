"""Search filters on LinkedIn's /jobs/search-results/ page, read back from captured pages.

Root cause (captured in the worker Chrome, 2026-10-22): the old /jobs/search/ URL redirects to
/jobs/search-results/, which keeps only keywords, f_TPR and f_AL. `location`, `f_JT` (job type)
and sometimes `f_WT` (remote) are dropped. `geoId` is kept; job type has to be set in the
"Employment type" dropdown.
"""

import os

import pytest
from lxml import html

from modules import linkedin_ui as ui

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _page(name: str):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as file:
        return html.fromstring(file.read())


def test_read_applied_filters_from_fixture():
    assert ui.read_applied_filters(_page("search_results_filtered.html")) == {
        "job_type": ["Contract"],
        "on_site": ["Remote"],
        "location": "United States",
        "easy_apply": True,
    }


def test_read_applied_filters_unfiltered_page():
    applied = ui.read_applied_filters(_page("search_results_unfiltered.html"))
    assert applied["job_type"] == [] and applied["on_site"] == [] and applied["easy_apply"] is False
    assert applied["location"]  # whatever LinkedIn picked, it's read


def test_read_employment_options_from_open_dropdown():
    options = ui.read_employment_options(_page("search_results_employment_dropdown.html"))
    assert options == {
        "Part-time": False,
        "Contract": True,
        "Internship": False,
        "Full-time": False,
        "Volunteer": False,
    }


# LinkedIn renders the pill bar twice (one copy sticky); the bot clicks the visible one.
def test_employment_dropdown_pill_found_when_set_and_unset():
    for name in ("search_results_filtered.html", "search_results_unfiltered.html"):
        pills = _page(name).xpath(ui.EMPLOYMENT_TYPE_PILL_XPATH)
        assert 1 <= len(pills) <= 2 and all(p.get("role") == "button" for p in pills), name


def test_show_results_link_in_open_dropdown():
    assert len(_page("search_results_employment_dropdown.html").xpath(ui.FILTER_SHOW_RESULTS_XPATH)) == 1


def test_filter_pill_xpath_toggles():
    page = _page("search_results_filtered.html")
    remote = page.xpath(ui.filter_pill_xpath("Remote"))
    assert remote and all(p.get("aria-checked") == "true" for p in remote)
    assert page.xpath(ui.filter_pill_xpath("Hybrid")) == []


EXPECTED = {"job_type": ["Contract", "Temporary"], "on_site": ["Remote"], "location": "United States", "easy_apply": True}


@pytest.mark.parametrize(
    "applied, missing",
    [
        ({"job_type": ["Contract", "Temporary"], "on_site": ["Remote"], "location": "United States", "easy_apply": True}, []),
        ({"job_type": ["Contract"], "on_site": ["Remote"], "location": "United States", "easy_apply": True}, ["job_type"]),
        ({"job_type": ["Contract", "Temporary"], "on_site": [], "location": "United States", "easy_apply": True}, ["on_site"]),
        ({"job_type": ["Contract", "Temporary"], "on_site": ["Remote"], "location": "European Union", "easy_apply": True}, ["location"]),
        ({"job_type": ["Contract", "Temporary"], "on_site": ["Remote"], "location": "united states", "easy_apply": False}, ["easy_apply"]),
    ],
)
def test_missing_filters_detects_each(applied, missing):
    assert ui.missing_filters(EXPECTED, applied) == missing


def test_missing_filters_ignores_unset_expectations():
    assert ui.missing_filters({"job_type": [], "on_site": [], "location": "", "easy_apply": False}, {
        "job_type": [], "on_site": [], "location": "European Union", "easy_apply": False}) == []


def test_job_cards_stop_at_related_results():
    # Kestrel M3 #7: cards under "We found more results related to your search" ignore the filters.
    filtered = _page("search_results_filtered.html")
    assert len(filtered.xpath(ui.JOB_CARDS_XPATH)) == 2
    assert filtered.xpath(ui.RELATED_RESULTS_MARKER_XPATH)
    unfiltered = _page("search_results_unfiltered.html")
    assert len(unfiltered.xpath(ui.JOB_CARDS_XPATH)) == 25
    assert unfiltered.xpath(ui.RELATED_RESULTS_MARKER_XPATH) == []


# Kestrel (public round): with 2+ types ticked LinkedIn labels the pill
# "Filter by Employment type, 2 filters are selected": the bot missed it and reported
# a false "Filters not applied".
def test_employment_pill_found_with_several_types():
    pills = _page("search_results_two_job_types.html").xpath(ui.EMPLOYMENT_TYPE_PILL_XPATH)
    assert 1 <= len(pills) <= 2 and all(p.get("role") == "button" for p in pills)


def test_read_several_job_types():
    page = _page("search_results_two_job_types.html")
    options = ui.read_employment_options(page)
    assert [name for name, ticked in options.items() if ticked] == ["Contract", "Full-time"]
    assert sorted(ui.read_applied_filters(page)["job_type"]) == ["Contract", "Full-time"]


# 2026-10-29: LinkedIn swapped the role="radio"/"checkbox" widgets for hidden native checkboxes
# (opacity 0, never displayed) with a visible sibling <label for>. State is the `checked`
# attribute; the click goes to the label.
NATIVE_PILLS = (
    '<div><nav>'
    '<div aria-label="Filter by Remote"><input aria-label="Filter by Remote" id="_r_fk_" type="checkbox" checked="">'
    '<label for="_r_fk_">Remote</label></div>'
    '<div aria-label="Filter by Easy Apply"><input aria-label="Filter by Easy Apply" id="_r_fm_" type="checkbox">'
    '<label for="_r_fm_">Easy Apply</label></div>'
    '</nav><nav>'  # LinkedIn renders the pill bar twice
    '<div aria-label="Filter by Remote"><input aria-label="Filter by Remote" id="_r_x1_" type="checkbox" checked="">'
    '<label for="_r_x1_">Remote</label></div>'
    '</nav></div>'
)
NATIVE_DROPDOWN = (
    '<div>'
    '<div><div><input id="_r_ak_" aria-label="Full-time" type="checkbox" checked=""><label for="_r_ak_"></label></div><p>Full-time</p></div>'
    '<div><div><input id="_r_ag_" aria-label="Contract" type="checkbox"><label for="_r_ag_"></label></div><p>Contract</p></div>'
    '<div><input aria-label="Filter by Remote" id="_r_fk_" type="checkbox" checked=""><label for="_r_fk_">Remote</label></div>'
    '</div>'
)


def test_read_applied_filters_native_checkboxes():
    applied = ui.read_applied_filters(html.fromstring(NATIVE_PILLS))
    assert applied["on_site"] == ["Remote"]
    assert applied["easy_apply"] is False


def test_read_applied_filters_native_easy_apply_ticked():
    page = html.fromstring(NATIVE_PILLS.replace('id="_r_fm_" type="checkbox"', 'id="_r_fm_" type="checkbox" checked=""'))
    assert ui.read_applied_filters(page)["easy_apply"] is True


def test_filter_pill_xpath_targets_label_of_native_checkbox():
    page = html.fromstring(NATIVE_PILLS)
    easy = page.xpath(ui.filter_pill_xpath("Easy Apply"))
    assert [(e.tag, e.get("for")) for e in easy] == [("label", "_r_fm_")]
    assert [e.get("for") for e in page.xpath(ui.filter_pill_xpath("Remote"))] == ["_r_fk_", "_r_x1_"]


def test_read_employment_options_native_checkboxes():
    assert ui.read_employment_options(html.fromstring(NATIVE_DROPDOWN)) == {"Full-time": True, "Contract": False}


def test_employment_option_xpath_targets_label():
    page = html.fromstring(NATIVE_DROPDOWN)
    assert [(e.tag, e.get("for")) for e in page.xpath(ui.employment_option_xpath("Contract"))] == [("label", "_r_ag_")]
