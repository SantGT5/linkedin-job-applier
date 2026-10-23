"""Single-password login: a signed, HTTP-only session cookie (Starlette SessionMiddleware)."""

import hmac
import os

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Login(BaseModel):
    password: str


def _password_ok(given: str) -> bool:
    expected = os.environ.get("UI_PASSWORD", "")
    # No password configured = nobody gets in.
    return bool(expected) and hmac.compare_digest(given.encode(), expected.encode())


def require_auth(request: Request) -> None:
    if not request.session.get("auth"):
        raise HTTPException(status_code=401, detail="Not logged in")


@router.post("/login", status_code=204)
def login(body: Login, request: Request) -> Response:
    if not _password_ok(body.password):
        request.session.clear()
        raise HTTPException(status_code=401, detail="Wrong password")
    request.session["auth"] = True
    return Response(status_code=204)


@router.post("/logout", status_code=204)
def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=204)


@router.get("/check", status_code=204)
def check(request: Request) -> Response:
    """Used by nginx `auth_request` to guard /novnc/."""
    require_auth(request)
    return Response(status_code=204)
