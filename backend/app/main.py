import os

from fastapi import Depends, FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app import auth
from app.api import bot, emails, export, health, history, questions, resume, runs, settings

PROTECTED = [
    settings.router, bot.router, runs.router, questions.router,
    history.router, emails.router, export.router, resume.router,
]


def create_app() -> FastAPI:
    secret = os.environ.get("SESSION_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError("SESSION_SECRET must be set in .env (at least 32 characters)")
    app = FastAPI(title="Applier", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret,
        session_cookie="applier_session",
        max_age=14 * 24 * 3600,
        same_site="lax",
        https_only=False,  # served on http://localhost only
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    for router in PROTECTED:
        app.include_router(router, dependencies=[Depends(auth.require_auth)])
    return app
