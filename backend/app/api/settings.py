import json
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Setting
from app.settings_schema import FIELDS, SCHEMA, SECTIONS, SettingsError, defaults, validate

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Shown in the UI as set / not set only; values never leave the process.
SECRETS = [
    ("LinkedIn username", "LINKEDIN_USERNAME"),
    ("LinkedIn password", "LINKEDIN_PASSWORD"),
    ("Claude API key", "CLAUDE_API_KEY"),
    ("GLM API key", "GLM_API_KEY"),
    ("UI password", "UI_PASSWORD"),
    ("Session signing key", "SESSION_SECRET"),
]
EXPORT_VERSION = 1
EXPORT_FILENAME = "applier-settings.json"
MAX_IMPORT_BYTES = 1024 * 1024


def load_all(session: Session) -> dict[str, dict]:
    """Saved settings over defaults, for every section."""
    values = defaults()
    for row in session.query(Setting).all():
        if row.section in values:
            values[row.section].update(
                {k: v for k, v in row.values.items() if k in values[row.section]}
            )
    return values


def _merge(session: Session, section: str, clean: dict) -> None:
    row = session.get(Setting, section)
    if row is None:
        row = Setting(section=section, values={})
        session.add(row)
    row.values = {**row.values, **clean}


def save_section(session: Session, section: str, values: dict) -> dict:
    """Validates and merges `values` into the stored section. Raises SettingsError."""
    _merge(session, section, validate(section, values))
    session.commit()
    return load_all(session)[section]


def parse_import(data: Any) -> dict[str, dict]:
    """Validates a whole settings file (from Settings → Export) before anything is saved.

    Returns the clean values per section. Raises SettingsError naming every bad field as
    `section.key` (or the section / `version` / `file` itself). A value equal to the field's
    default is always accepted, so a fresh install's export (empty name...) imports back.
    """
    if not isinstance(data, dict):
        raise SettingsError({"file": "must be a JSON object with a version and settings sections"})
    errors: dict[str, str] = {}
    version = data.get("version")
    if type(version) is not int or version != EXPORT_VERSION:
        errors["version"] = f"must be {EXPORT_VERSION} (use a file from Settings → Export)"
    clean: dict[str, dict] = {}
    for section, values in data.items():
        if section == "version":
            continue
        if section not in SECTIONS:
            errors[section] = "unknown section"
        elif not isinstance(values, dict):
            errors[section] = "must be an object"
        else:
            as_default = {k: v for k, v in values.items() if (section, k) in FIELDS and v == FIELDS[(section, k)].default}
            try:
                clean[section] = {**as_default, **validate(section, {k: v for k, v in values.items() if k not in as_default})}
            except SettingsError as e:
                errors.update({f"{section}.{key}": message for key, message in e.field_errors.items()})
    if errors:
        raise SettingsError(errors)
    return clean


@router.get("/schema")
def get_schema() -> list[dict]:
    return [field.to_dict() for field in SCHEMA]


@router.get("")
def get_settings(session: Session = Depends(get_session)) -> dict:
    return load_all(session)


@router.get("/secrets")
def get_secrets() -> list[dict]:
    return [
        {"name": name, "env_var": env_var, "set": bool(os.environ.get(env_var, "").strip())}
        for name, env_var in SECRETS
    ]


@router.get("/export")
def export_settings(session: Session = Depends(get_session)) -> JSONResponse:
    """Every non-secret setting, as a file Settings → Import reads back. Secrets stay in `.env`."""
    return JSONResponse(
        {"version": EXPORT_VERSION, **load_all(session)},
        headers={"Content-Disposition": f'attachment; filename="{EXPORT_FILENAME}"'},
    )


@router.post("/import")
def import_settings(file: UploadFile, session: Session = Depends(get_session)) -> dict:
    """Saves an exported settings file. All or nothing: any bad field means 422 and no changes."""
    raw = file.file.read(MAX_IMPORT_BYTES + 1)
    if len(raw) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="The file is larger than 1 MB.")
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except ValueError:
        raise HTTPException(status_code=422, detail={"field_errors": {"file": "isn't a valid JSON file"}})
    try:
        clean = parse_import(data)
    except SettingsError as e:
        raise HTTPException(status_code=422, detail={"field_errors": e.field_errors})
    for section, values in clean.items():
        _merge(session, section, values)
    session.commit()
    return load_all(session)


@router.put("/{section}")
def put_section(section: str, values: dict, session: Session = Depends(get_session)) -> dict:
    if section not in SECTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown section '{section}'")
    try:
        return save_section(session, section, values)
    except SettingsError as e:
        session.rollback()
        raise HTTPException(status_code=422, detail={"field_errors": e.field_errors})
