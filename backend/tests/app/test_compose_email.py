from app.compose_email import compose
from app.settings_schema import defaults

ROW = {
    "email": "hr@acme.com",
    "title": "Senior Full Stack Software Engineer",
    "job_link": "https://www.linkedin.com/jobs/view/1",
}
ME = {
    **defaults()["email"],
    "my_name": "Jane Doe",
    "phone_number": "+1 555 0100",
    "linkedin_profile": "[linkedin.com/in/janedoe](https://linkedin.com/in/janedoe)",
}


def test_compose_matches_spec_example():
    c = compose(ROW, ME)
    assert c.to == "hr@acme.com"
    assert c.subject == "Senior Full Stack Software Engineer - Jane Doe"
    assert '<a href="https://www.linkedin.com/jobs/view/1">Senior Full Stack Software Engineer</a>' in c.body_html
    assert '<a href="https://linkedin.com/in/janedoe">linkedin.com/in/janedoe</a>' in c.body_html
    assert c.body_text.startswith("Hi,\n\nHope this message finds you well.")
    assert "I came across the Senior Full Stack Software Engineer (https://www.linkedin.com/jobs/view/1) role" in c.body_text
    assert c.body_text.endswith(
        "Best regards,\nJane Doe\n+1 555 0100\nlinkedin.com/in/janedoe (https://linkedin.com/in/janedoe)"
    )
    assert "<br>" in c.body_html and "\n" not in c.body_html


def test_phone_and_linkedin_placeholders():
    settings = {"subject_template": "{my_name}", "body_template": "Call {phone_number}, see {linkedin_profile}"}
    c = compose(ROW, {**settings, "my_name": "Jane", "phone_number": "+1 555 0100", "linkedin_profile": "linkedin.com/in/janedoe"})
    assert c.body_text == "Call +1 555 0100, see linkedin.com/in/janedoe"


def test_empty_signature_lines_are_dropped():
    # Defaults are empty: an unfilled phone or profile leaves no blank lines behind.
    c = compose(ROW, {**ME, "phone_number": "", "linkedin_profile": ""})
    assert c.body_text.endswith("Best regards,\nJane Doe")
    c = compose(ROW, defaults()["email"])
    assert c.body_text.endswith("Best regards,")
    # A line with other text stays, even when its placeholder is empty.
    c = compose(ROW, {"subject_template": "", "body_template": "a\nPhone: {phone_number}\nb"})
    assert c.body_text == "a\nPhone: \nb"


def test_compose_escapes_html():
    c = compose({**ROW, "title": "<b>x</b> & co"}, ME)
    assert "<b>" not in c.body_html
    assert "&lt;b&gt;x&lt;/b&gt; &amp; co" in c.body_html
    assert c.subject == "<b>x</b> & co - Jane Doe"  # plain text stays as-is


def test_compose_unknown_placeholder_and_unsafe_link():
    settings = {"my_name": "Me", "subject_template": "{job_title} {nope}", "body_template": "[click](javascript:alert(1)) {hr_email}"}
    c = compose(ROW, settings)
    assert c.subject == "Senior Full Stack Software Engineer {nope}"
    assert "<a " not in c.body_html and "hr@acme.com" in c.body_html


def test_compose_missing_fields():
    c = compose({"email": "a@b.io", "title": None, "job_link": None}, ME)
    assert c.subject == " - Jane Doe"
    assert c.to == "a@b.io"
