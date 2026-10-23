from urllib.parse import parse_qs, urlparse

from selenium.common.exceptions import (
    InvalidSessionIdException,
    NoSuchElementException,
    NoSuchWindowException,
    TimeoutException,
    WebDriverException,
)

from modules.helpers import (
    build_jobs_search_url,
    is_browser_gone,
    unsupported_search_filters,
)


def query_of(url: str) -> dict[str, str]:
    return {key: values[0] for key, values in parse_qs(urlparse(url).query).items()}


def test_keywords_only():
    url = build_jobs_search_url("Python Developer")
    assert url.startswith("https://www.linkedin.com/jobs/search/?")
    assert query_of(url) == {"keywords": "Python Developer"}


def test_date_and_sort_still_supported():
    url = build_jobs_search_url(
        "Python Developer", date_posted="Past 24 hours", sort_by="Most recent"
    )
    assert query_of(url) == {
        "keywords": "Python Developer",
        "f_TPR": "r86400",
        "sortBy": "DD",
    }


def test_all_url_filters():
    url = build_jobs_search_url(
        "Python Developer",
        date_posted="Past week",
        location="United States",
        easy_apply_only=True,
        experience_level=["Entry level", "Mid-Senior level"],
        job_type=["Contract", "Temporary"],
        on_site=["Remote", "Hybrid"],
        salary="$100,000+",
        under_10_applicants=True,
        in_your_network=True,
    )
    assert query_of(url) == {
        "keywords": "Python Developer",
        "f_TPR": "r604800",
        # LinkedIn's /jobs/search-results/ drops `location`; it keeps `geoId`.
        "geoId": "103644278",
        "f_AL": "true",
        "f_E": "2,4",
        "f_JT": "C,T",
        "f_WT": "2,3",
        "f_SB2": "4",
        "f_EA": "true",
        "f_JIYN": "true",
    }


def test_empty_and_unknown_values_are_left_out():
    url = build_jobs_search_url(
        "Python Developer",
        date_posted="Any time",
        location="  ",
        easy_apply_only=False,
        job_type=["Not a job type"],
        salary="",
    )
    assert query_of(url) == {"keywords": "Python Developer"}


def test_unsupported_search_filters_lists_only_filters_that_are_set():
    assert unsupported_search_filters(
        companies=["Acme"],
        location=[],
        industry=["Software"],
        job_function=[],
        job_titles=[],
        benefits=[],
        commitments=[],
        fair_chance_employer=True,
    ) == ["companies", "industry", "fair_chance_employer"]
    assert (
        unsupported_search_filters(
            companies=[],
            location=[],
            industry=[],
            job_function=[],
            job_titles=[],
            benefits=[],
            commitments=[],
            fair_chance_employer=False,
        )
        == []
    )


def test_is_browser_gone():
    assert is_browser_gone(NoSuchWindowException("window closed"))
    assert is_browser_gone(InvalidSessionIdException("invalid session id"))
    assert is_browser_gone(WebDriverException("chrome not reachable"))
    # Element lookups failing are not a closed browser.
    assert not is_browser_gone(TimeoutException(""))
    assert not is_browser_gone(NoSuchElementException("no such element"))
    assert not is_browser_gone(ValueError("other"))


def test_unknown_location_falls_back_to_text():
    # No known geoId: keep the text (the bot then sets it through the page's location box).
    url = build_jobs_search_url("Dev", location="Lisbon, Portugal")
    assert query_of(url) == {"keywords": "Dev", "location": "Lisbon, Portugal"}


def test_geo_id_lookup_ignores_case_and_spaces():
    from modules.helpers import geo_id_for

    assert geo_id_for(" united states ") == "103644278"
    assert geo_id_for("European Union") == "91000000"
    assert geo_id_for("Mars") is None
