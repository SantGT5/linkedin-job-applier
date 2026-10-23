from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text

from app.models import HrEmail


def _emails(db, n):
    # Date filters use local days (the DB session's time zone: TZ in .env).
    zone = ZoneInfo(db.execute(text("SHOW timezone")).scalar())
    base = datetime(2026, 10, 1, tzinfo=zone)
    for i in range(n):
        db.add(HrEmail(email=f"hr{i}@acme.com", job_id=str(i), title="Backend Engineer" if i % 3 == 0 else "Designer",
                       company="Acme" if i % 2 == 0 else "Globex", job_link=f"https://l/{i}",
                       status="emailed" if i < 4 else "new", found_at=base + timedelta(hours=i)))
    db.commit()


def test_email_filters_and_pagination(client, db):
    _emails(db, 30)
    page2 = client.get("/api/emails?page=2&page_size=25").json()
    assert page2["total"] == 30 and len(page2["items"]) == 5 and page2["page"] == 2
    assert client.get("/api/emails?status=emailed").json()["total"] == 4
    assert client.get("/api/emails?status=new&company=globex").json()["total"] == 13
    assert client.get("/api/emails?role=backend").json()["total"] == 10
    assert client.get("/api/emails?q=hr7@").json()["total"] == 1
    newest = client.get("/api/emails").json()["items"][0]
    assert newest["email"] == "hr29@acme.com"
    assert client.get("/api/emails?status=bogus").status_code == 422


def test_email_date_filter(client, db):
    _emails(db, 30)
    r = client.get("/api/emails?date_from=2026-10-02&date_to=2026-10-02").json()
    assert r["total"] == 6  # local hours 24..29


def test_compose_endpoint(client, db):
    _emails(db, 1)
    client.put("/api/settings/email", json={"my_name": "Jane Doe"})
    eid = client.get("/api/emails").json()["items"][0]["id"]
    c = client.get(f"/api/emails/{eid}/compose").json()
    assert c["to"] == "hr0@acme.com" and c["subject"] == "Backend Engineer - Jane Doe"
    assert '<a href="https://l/0">Backend Engineer</a>' in c["body_html"]


def test_mark_emailed_sets_timestamp(client, db):
    _emails(db, 5)
    row = client.get("/api/emails?status=new").json()["items"][0]
    r = client.post(f"/api/emails/{row['id']}/mark-emailed").json()
    assert r["status"] == "emailed" and r["emailed_at"]
    r = client.post(f"/api/emails/{row['id']}/mark-new").json()
    assert r["status"] == "new" and r["emailed_at"] is None
    assert client.post("/api/emails/999999/mark-emailed").status_code == 404


def test_preview_uses_given_templates(client):
    r = client.post("/api/emails/preview", json={"subject_template": "Re: {job_title}", "body_template": "Hi {hr_email}, [{job_title}]({job_url})", "my_name": "Me"})
    c = r.json()
    assert c["subject"].startswith("Re: ") and "<a href=" in c["body_html"] and c["to"]


def test_preview_fills_phone_and_linkedin(client):
    r = client.post("/api/emails/preview", json={
        "subject_template": "{my_name}", "body_template": "{phone_number} {linkedin_profile}",
        "my_name": "Jane Doe", "phone_number": "+1 555 0100", "linkedin_profile": "linkedin.com/in/janedoe",
    })
    assert r.json()["body_text"] == "+1 555 0100 linkedin.com/in/janedoe"
