from selenium.common.exceptions import ElementClickInterceptedException

from modules.clickers_and_finders import click_displayed


class FakeElement:
    def __init__(self, displayed=True, click_error=None):
        self.displayed = displayed
        self.click_error = click_error
        self.clicked = False

    def is_displayed(self):
        return self.displayed

    def click(self):
        if self.click_error:
            raise self.click_error
        self.clicked = True


class FakeDriver:
    def __init__(self, elements):
        self.elements = elements
        self.scripts = []

    def find_elements(self, by, value):
        return self.elements

    def execute_script(self, script, *args):
        self.scripts.append((script, args))


def test_returns_false_without_a_match():
    assert click_displayed(FakeDriver([]), "//button") is False


def test_returns_false_when_every_match_is_hidden():
    hidden = FakeElement(displayed=False)
    assert click_displayed(FakeDriver([hidden]), "//button") is False
    assert not hidden.clicked


def test_clicks_the_displayed_match():
    hidden, shown = FakeElement(displayed=False), FakeElement()
    driver = FakeDriver([hidden, shown])
    assert click_displayed(driver, "//button") is True
    assert shown.clicked and not hidden.clicked
    # Scrolled into view first, without smooth-scroll animation.
    assert driver.scripts[0][1] == (shown,) and "instant" in driver.scripts[0][0]


def test_clicks_with_javascript_when_something_covers_the_element():
    covered = FakeElement(click_error=ElementClickInterceptedException("header on top"))
    driver = FakeDriver([covered])
    assert click_displayed(driver, "//button") is True
    assert driver.scripts[-1] == ("arguments[0].click();", (covered,))


class FakeActions:
    def __init__(self):
        self.keys = []

    def send_keys(self, key):
        self.keys.append(key)
        return self

    def perform(self):
        pass


def test_close_after_submit_is_quiet_when_done_is_missing(monkeypatch, capsys):
    # Kestrel E2E (iii): after a successful submit, a missing "Done" button isn't a failure.
    from selenium.webdriver.common.keys import Keys

    from modules import clickers_and_finders as cf

    calls = []
    monkeypatch.setattr(cf, "wait_span_click", lambda driver, text, time=5.0, **kw: calls.append((text, kw)) or False)
    actions = FakeActions()
    cf.close_after_submit(object(), actions)
    assert calls == [("Done", {"quiet": True})]
    assert actions.keys == [Keys.ESCAPE]
    assert "Click Failed" not in capsys.readouterr().out
