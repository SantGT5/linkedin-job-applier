import os

import pytest
from lxml import html

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


@pytest.fixture
def search_page():
    """Parsed LinkedIn /jobs/search-results/ page (lxml uses XPath 1.0, same as Selenium)."""
    with open(
        os.path.join(FIXTURES, "search_results_page.html"), encoding="utf-8"
    ) as file:
        return html.fromstring(file.read())
