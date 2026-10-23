import pytest

from modules.emails import extract_emails, should_collect_emails


def test_extract_emails_basic():
    assert extract_emails("Send CV to Jobs@Acme.com.") == ["jobs@acme.com"]


def test_extract_emails_dedup_and_assets():
    assert extract_emails("a@b.io a@b.io logo@2x.png") == ["a@b.io"]


def test_extract_emails_keeps_order_and_strips_punctuation():
    text = "Contact (hr@x.nl), or <talent@y.com>; also mailto:jobs@z.co.uk]"
    assert extract_emails(text) == ["hr@x.nl", "talent@y.com", "jobs@z.co.uk"]


def test_extract_emails_empty():
    assert extract_emails("") == [] and extract_emails(None) == []


@pytest.mark.parametrize(
    "ai_filter_jobs, score, min_score, expected",
    [
        (False, None, 50, True),
        (True, None, 50, True),
        (True, 40, 0, True),
        (True, 60, 50, True),
        (True, 50, 50, True),
        (True, 40, 50, False),
        (False, 40, 50, True),
    ],
)
def test_should_collect(ai_filter_jobs, score, min_score, expected):
    assert should_collect_emails(ai_filter_jobs, score, min_score) is expected
