"""Runs the bot: one fresh subprocess per queued run.

    python -m app.worker

Each tick reconciles the DB with the child process: starts queued runs (after writing the
settings snapshot the bot's config modules read), streams the child's output into
`run_logs`, stops the child when `bot_control.desired` becomes `stopped`, and records how
the run ended. A run never stays "running" without a child behind it.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import signal
import sqlite3
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from app.api.settings import load_all
from app.models import BotControl, LinkedinSession, Prompt, Run, RunLog

log = logging.getLogger("worker")

BACKEND_DIR = Path(__file__).resolve().parent.parent
BOT_SCRIPT = BACKEND_DIR / "bot" / "runAiBot.py"
STOPPED_ANSWER = "__stopped__"
# The bot doesn't need these; keep them out of its environment.
HIDDEN_FROM_BOT = ("UI_PASSWORD", "SESSION_SECRET", "POSTGRES_PASSWORD", "DATABASE_URL")
LOG_FLUSH_SECONDS = 0.5
ERROR_TAIL_LINES = 20
SESSION_CHECK_SECONDS = 60
# Chrome cookie times are microseconds since 1601-01-01.
CHROME_EPOCH_OFFSET = 11644473600


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Child:
    """A running bot process plus the thread that ships its output to `run_logs`."""

    def __init__(self, run_id: int, process: subprocess.Popen, session_factory: sessionmaker[Session]):
        self.run_id = run_id
        self.process = process
        self.session_factory = session_factory
        self.tail: deque[str] = deque(maxlen=ERROR_TAIL_LINES)
        self.lines: queue.Queue[str | None] = queue.Queue()
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.writer = threading.Thread(target=self._write, daemon=True)
        self.reader.start()
        self.writer.start()

    def _read(self) -> None:
        for raw in iter(self.process.stdout.readline, b""):
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            self.tail.append(line)
            self.lines.put(line)
        self.lines.put(None)

    def _write(self) -> None:
        done = False
        while not done:
            batch: list[str] = []
            deadline = time.monotonic() + LOG_FLUSH_SECONDS
            while time.monotonic() < deadline:
                try:
                    line = self.lines.get(timeout=max(0.0, deadline - time.monotonic()))
                except queue.Empty:
                    break
                if line is None:
                    done = True
                    break
                batch.append(line)
            if batch:
                try:
                    with self.session_factory() as session:
                        session.add_all(RunLog(run_id=self.run_id, line=line) for line in batch)
                        session.commit()
                except Exception:
                    log.exception("Failed to save %d log lines", len(batch))

    def alive(self) -> bool:
        return self.process.poll() is None

    def finish_output(self, timeout: float = 10.0) -> None:
        self.reader.join(timeout)
        self.writer.join(timeout)


class Worker:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        bot_script: Path = BOT_SCRIPT,
        data_dir: Path | str = "/data",
        database_url: str = "",
        kill_grace: float = 5.0,
        display: str | None = None,
    ):
        self.session_factory = session_factory
        self.bot_script = Path(bot_script)
        self.data_dir = Path(data_dir)
        self.database_url = database_url
        self.kill_grace = kill_grace
        self.display = display or os.environ.get("DISPLAY", ":99")
        self.python = sys.executable
        self.child: Child | None = None
        self.profile_dir = Path(os.environ.get("CHROME_PROFILE_DIR", self.data_dir / "chrome-profile"))
        self._last_session_check = 0.0

    # ---- process handling -------------------------------------------------

    def child_env(self, run_id: int, snapshot: Path) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k not in HIDDEN_FROM_BOT}
        paths = [str(BACKEND_DIR), str(self.bot_script.parent), str(BACKEND_DIR / "bot")]
        if env.get("PYTHONPATH"):
            paths.append(env["PYTHONPATH"])
        env.update(
            APPLIER_CONFIG_FILE=str(snapshot),
            APPLIER_DATABASE_URL=self.database_url,
            APPLIER_RUN_ID=str(run_id),
            DATA_DIR=str(self.data_dir),
            DISPLAY=self.display,
            PYTHONPATH=os.pathsep.join(paths),
            PYTHONUNBUFFERED="1",
        )
        return env

    def _write_snapshot(self, session: Session, run_id: int) -> Path:
        path = self.data_dir / "run" / f"run-{run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(load_all(session), indent=2, default=str), encoding="utf-8")
        return path

    def _spawn(self, session: Session, run: Run) -> None:
        snapshot = self._write_snapshot(session, run.id)
        process = subprocess.Popen(
            [self.python, "-u", str(self.bot_script)],
            cwd=str(self.bot_script.parent),
            env=self.child_env(run.id, snapshot),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            # Own process group, so stopping also kills Chrome and chromedriver.
            start_new_session=True,
        )
        self.child = Child(run.id, process, self.session_factory)
        log.info("Run %s started (pid %s)", run.id, process.pid)

    def _signal_group(self, sig: int) -> None:
        try:
            os.killpg(self.child.process.pid, sig)
        except (ProcessLookupError, PermissionError):
            pass

    def _kill_child(self) -> None:
        """SIGTERM the bot's process group, SIGKILL whatever is left after the grace period."""
        self._signal_group(signal.SIGTERM)
        try:
            self.child.process.wait(self.kill_grace)
        except subprocess.TimeoutExpired:
            pass
        # Chrome children may outlive the bot itself.
        self._signal_group(signal.SIGKILL)
        try:
            self.child.process.wait(5)
        except subprocess.TimeoutExpired:
            log.error("Bot process %s did not die", self.child.process.pid)

    # ---- DB helpers ---------------------------------------------------------

    @staticmethod
    def _close_prompts(session: Session, run_id: int) -> None:
        session.execute(
            update(Prompt)
            .where(Prompt.run_id == run_id, Prompt.answer.is_(None))
            .values(answer=STOPPED_ANSWER, answered_at=_now())
        )

    @staticmethod
    def _end_run(session: Session, run_id: int, status: str, error: str | None = None) -> None:
        run = session.get(Run, run_id)
        run.status = status
        run.ended_at = _now()
        run.error = error
        Worker._close_prompts(session, run_id)
        control = session.get(BotControl, 1)
        if control is not None:
            control.desired = "stopped"
        session.commit()

    # ---- reconcile ----------------------------------------------------------

    def tick(self) -> None:
        with self.session_factory() as session:
            if self.child is None:
                self._tick_idle(session)
            else:
                self._tick_busy(session)

    def _session_from_profile(self) -> str:
        """LinkedIn login state from the saved Chrome profile's `li_at` session cookie."""
        cookies = self.profile_dir / "Default" / "Cookies"
        if not cookies.is_file():
            return "unknown"
        con = sqlite3.connect(f"file:{cookies}?mode=ro&immutable=1", uri=True)
        try:
            row = con.execute(
                "SELECT MAX(expires_utc) FROM cookies WHERE name = 'li_at' AND host_key LIKE '%linkedin.com'"
            ).fetchone()
        finally:
            con.close()
        expires = row[0] if row else None
        if expires is None:
            return "logged_out"
        if expires == 0:  # session cookie
            return "logged_in"
        return "logged_in" if expires / 1_000_000 - CHROME_EPOCH_OFFSET > time.time() else "logged_out"

    def check_session(self) -> None:
        """Updates the dashboard's LinkedIn status while no run is using the profile."""
        try:
            state = self._session_from_profile()
        except sqlite3.Error:
            log.exception("Could not read the Chrome profile cookies")
            return
        cookies = self.profile_dir / "Default" / "Cookies"
        with self.session_factory() as session:
            row = session.get(LinkedinSession, 1)
            if row is None:
                return
            # A bot check made after the cookie file last changed knows better (cookie revoked server-side).
            if row.checked_at is not None and cookies.is_file():
                written = datetime.fromtimestamp(cookies.stat().st_mtime, timezone.utc)
                if row.checked_at > written and row.state != "unknown":
                    return
            row.state = state
            row.checked_at = _now()
            session.commit()

    def _tick_idle(self, session: Session) -> None:
        # A run that claims to be busy with no child behind it was orphaned (worker restart).
        for run in session.scalars(select(Run).where(Run.status.in_(("running", "waiting", "stopping")))):
            self._end_run(session, run.id, "failed", "The worker restarted while this run was in progress.")
        run = session.scalar(
            select(Run).where(Run.status == "queued").order_by(Run.id).limit(1).with_for_update(skip_locked=True)
        )
        if run is None:
            session.rollback()
            if time.monotonic() - self._last_session_check >= SESSION_CHECK_SECONDS:
                self._last_session_check = time.monotonic()
                self.check_session()
            return
        run.status = "running"
        run.started_at = _now()
        session.commit()
        try:
            self._spawn(session, run)
        except Exception as e:
            log.exception("Failed to start run %s", run.id)
            self.child = None
            self._end_run(session, run.id, "failed", f"Could not start the bot: {e}")

    def _tick_busy(self, session: Session) -> None:
        child = self.child
        control = session.get(BotControl, 1)
        if child.alive() and control is not None and control.desired == "stopped":
            run = session.get(Run, child.run_id)
            run.status = "stopping"
            # Unblock a bot waiting on a prompt, then make sure it's gone.
            self._close_prompts(session, child.run_id)
            session.commit()
            self._kill_child()
            child.finish_output()
            self._end_run(session, child.run_id, "stopped")
            self.child = None
            log.info("Run %s stopped", child.run_id)
            return
        if child.alive():
            return
        child.finish_output()
        code = child.process.returncode
        session.expire_all()
        run = session.get(Run, child.run_id)
        if run.status == "stopping":
            self._end_run(session, child.run_id, "stopped")
        elif code == 0:
            self._end_run(session, child.run_id, "finished")
        else:
            tail = "\n".join(child.tail) or "(no output)"
            self._end_run(session, child.run_id, "failed", f"Bot exited with code {code}.\n{tail}")
        self.child = None
        log.info("Run %s ended with code %s", child.run_id, code)

    def shutdown(self) -> None:
        """Stops a running child (worker shutting down) and records the run as stopped."""
        if self.child is None:
            return
        child = self.child
        if child.alive():
            self._kill_child()
        child.finish_output()
        with self.session_factory() as session:
            self._end_run(session, child.run_id, "stopped")
        self.child = None

    def run_forever(self, poll: float = 0.5) -> None:
        stop = threading.Event()

        def on_signal(signum, frame):
            stop.set()

        signal.signal(signal.SIGTERM, on_signal)
        signal.signal(signal.SIGINT, on_signal)
        log.info("Worker ready")
        while not stop.is_set():
            try:
                self.tick()
            except Exception:
                log.exception("Worker tick failed")
            stop.wait(poll)
        self.shutdown()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    from app.config import get_env
    from app.db import session_factory

    env = get_env()
    Worker(
        session_factory=session_factory(),
        data_dir=env.data_dir,
        database_url=env.database_url,
    ).run_forever()


if __name__ == "__main__":
    main()
