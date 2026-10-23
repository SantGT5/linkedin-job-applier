import re

import pytest

from app.settings_schema import SCHEMA, SECTIONS, SECRET_ENV, SettingsError, defaults, validate

REMOVED = {
    "llm_api_url", "llm_api_key", "llm_model", "llm_spec", "stream_output",
    "keep_screen_awake", "ai_log_email_apply", "generated_resume_path", "file_name",
    "failed_file_name", "email_apply_file_name", "logs_folder_path", "default_resume_path",
}


def test_defaults_cover_every_section():
    values = defaults()
    assert set(values) == set(SECTIONS)
    for field in SCHEMA:
        assert values[field.section][field.key] == field.default


def test_validate_coerces_and_rejects():
    with pytest.raises(SettingsError) as err:
        validate("questions", {"desired_salary": "abc"})
    assert "desired_salary" in err.value.field_errors

    with pytest.raises(SettingsError) as err:
        validate("search", {"date_posted": "Yesterday"})
    assert "date_posted" in err.value.field_errors

    assert validate("ai", {"ai_provider": "glm"})["ai_provider"] == "glm"
    # Numeric strings from form inputs are coerced.
    assert validate("questions", {"desired_salary": "120000"})["desired_salary"] == 120000


def test_validate_rejects_unknown_key_and_multi_enum_option():
    with pytest.raises(SettingsError) as err:
        validate("search", {"nope": 1, "on_site": ["Mars"]})
    assert set(err.value.field_errors) == {"nope", "on_site"}


def test_validate_answers_shape():
    ok = validate("questions", {"custom_answers": [{"match": "German", "answer": "None"}]})
    assert ok["custom_answers"] == [{"match": "German", "answer": "None"}]
    with pytest.raises(SettingsError):
        validate("questions", {"custom_answers": [{"match": ""}]})


def test_removed_settings_absent():
    keys = {field.key for field in SCHEMA}
    assert not keys & REMOVED
    assert not keys & set(SECRET_ENV)


def test_ai_provider_options():
    field = next(f for f in SCHEMA if f.key == "ai_provider")
    assert field.section == "ai" and field.options == ["claude", "glm"]


def test_email_defaults_are_generic():
    values = defaults()["email"]
    # Personal details start empty; the default body only uses placeholders for them.
    assert values["my_name"] == values["phone_number"] == values["linkedin_profile"] == ""
    assert values["subject_template"] == "{job_title} - {my_name}"
    body = values["body_template"]
    assert "[{job_title}]({job_url})" in body
    assert body.endswith("Best regards,\n{my_name}\n{phone_number}\n{linkedin_profile}")
    assert not re.search(r"\d|linkedin\.com|@", body)


def test_email_personal_fields_are_optional():
    assert validate("email", {"my_name": "", "phone_number": "", "linkedin_profile": ""}) == {
        "my_name": "", "phone_number": "", "linkedin_profile": "",
    }
