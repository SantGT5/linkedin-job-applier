import csv
import io
from datetime import datetime, timezone

from app.models import AppliedJob, FailedJob, HrEmail


def test_export_applied_headers(client, db):
    db.add(AppliedJob(job_id="1", title='Dev, "senior"', company="Acme", date_applied=datetime(2026, 10, 1, 9)))
    db.commit()
    r = client.get("/api/export/applied.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(r.text)))
    assert rows[0][:3] == ["Job ID", "Title", "Company"] and rows[0][-1] == "Connect Request"
    assert rows[1][1] == 'Dev, "senior"' and rows[1][13].startswith("2026-10-01 09:00")


def test_export_failed_and_emails(client, db):
    db.add(FailedJob(job_id="2", assumed_reason="x"))
    db.add(HrEmail(email="a@b.io", job_id="3", status="new", found_at=datetime(2026, 10, 1, tzinfo=timezone.utc)))
    db.commit()
    failed = list(csv.reader(io.StringIO(client.get("/api/export/failed.csv").text)))
    assert failed[0][0] == "Job ID" and failed[0][5] == "Assumed Reason" and failed[1][0] == "2"
    emails = list(csv.reader(io.StringIO(client.get("/api/export/emails.csv").text)))
    assert emails[0][:4] == ["Job ID", "Title", "Company", "Apply Email"] and emails[1][3] == "a@b.io"
    assert client.get("/api/export/nope.csv").status_code == 404


def test_export_requires_login(anon_client):
    assert anon_client.get("/api/export/applied.csv").status_code == 401
