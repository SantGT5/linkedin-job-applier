"""
Author:     Sai Vignesh Golla
LinkedIn:   https://www.linkedin.com/in/saivigneshgolla/

Copyright (C) 2024 Sai Vignesh Golla

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html

GitHub:     https://github.com/GodsScion/Auto_job_applier_linkedIn

Support me: https://github.com/sponsors/GodsScion

version:    26.01.20.5.08
"""

# Imports

import json
import os
import pathlib
import re
import shutil
import subprocess
from datetime import datetime, timedelta
from pprint import pprint
from random import randint
from time import sleep

from config.settings import logs_folder_path

#### Common functions ####


# < Directories related
def make_directories(paths: list[str]) -> None:
    """
    Function to create missing directories
    """
    for path in paths:
        path = os.path.expanduser(path)  # Expands ~ to user's home directory
        path = path.replace("//", "/")

        # If path looks like a file path, get the directory part
        if "." in os.path.basename(path):
            path = os.path.dirname(path)

        if not path:  # Handle cases where path is empty after dirname
            continue

        try:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)  # exist_ok=True avoids race condition
        except Exception as e:
            print(f'Error while creating directory "{path}": ', e)


def get_default_temp_profile() -> str:
    # Thanks to https://github.com/vinodbavage31 for suggestion!
    return str(pathlib.Path.home() / ".auto-job-apply-profile")


def _under_worker() -> bool:
    """True when the bot runs under the app's worker: dialogs go to the web UI."""
    from modules import bridge

    return bridge.enabled()


def pause_for_user(text: str = "", title: str = "", button: str = "Continue") -> str:
    """
    Waits until the owner does something in the browser and clicks `button`.
    Under the worker this is a "Bot needs you" prompt in the UI; otherwise a blocking alert.
    """
    if _under_worker():
        from modules import bridge

        return bridge.ask(title, text, [button])
    return safe_alert(text, title, button)


def safe_alert(text: str = "", title: str = "", button: str = "OK") -> str:
    """
    Under the worker it is information only: logged, never blocking (use `pause_for_user` to wait).
    Otherwise (a terminal run) it logs and waits for Enter.
    """
    header = f"[{title}]" if title else "[Alert]"
    if _under_worker():
        print(f"\n{header}\n{text}\n", flush=True)
        return button
    print(f"\n{header}\n{text}\n")
    try:
        with open(__logs_file_path, "a+", encoding="utf-8") as file:
            file.write(f"{header}\n{text}\n")
    except Exception:
        pass
    try:
        input(f"Press Enter to continue ({button})... ")
    except EOFError:
        pass
    return button


def safe_confirm(
    text: str = "",
    title: str = "",
    buttons: tuple | list = ("OK", "Cancel"),
) -> str | None:
    """
    Under the worker it is a "Bot needs you" prompt in the UI; otherwise it asks in the terminal.
    """
    if isinstance(buttons, list):
        buttons = tuple(buttons)
    if _under_worker():
        from modules import bridge

        return bridge.ask(title, text, list(buttons))
    header = f"[{title}]" if title else "[Confirm]"
    print(f"\n{header}\n{text}\n")
    for i, label in enumerate(buttons, 1):
        print(f"  {i}. {label}")
    try:
        with open(__logs_file_path, "a+", encoding="utf-8") as file:
            file.write(f"{header}\n{text}\n")
    except Exception:
        pass
    try:
        choice = input(f"Choose 1-{len(buttons)} (default 1): ").strip()
        if not choice:
            return buttons[0]
        idx = int(choice) - 1
        if 0 <= idx < len(buttons):
            return buttons[idx]
    except (EOFError, ValueError):
        pass
    return buttons[0]


def chrome_major_version(binary: str) -> int | None:
    """Major version of the Chrome/Chromium at `binary` (e.g. 141), or None."""
    try:
        out = subprocess.check_output(
            [binary, "--version"], stderr=subprocess.STDOUT, text=True, timeout=10
        )
        match = re.search(r"(\d+)\.", out)
        return int(match.group(1)) if match else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def container_chrome_kwargs(environ: dict, work_dir: str | pathlib.Path = "/tmp") -> dict:
    """
    Extra `uc.Chrome(...)` arguments when running in the worker container, where Chromium and
    its matching chromedriver come from the OS (`CHROME_BINARY`, `CHROMEDRIVER`). Empty otherwise.
    """
    binary, driver = environ.get("CHROME_BINARY"), environ.get("CHROMEDRIVER")
    if not binary or not driver:
        return {}
    # undetected-chromedriver patches the driver binary in place: give it a writable copy.
    work_dir = pathlib.Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    driver_copy = work_dir / f"chromedriver-{os.getpid()}"
    shutil.copyfile(driver, driver_copy)
    os.chmod(driver_copy, 0o755)
    kwargs = {
        "browser_executable_path": binary,
        "driver_executable_path": str(driver_copy),
        "user_data_dir": environ.get("CHROME_PROFILE_DIR", "/data/chrome-profile"),
    }
    version = chrome_major_version(binary)
    if version:
        kwargs["version_main"] = version
    return kwargs


def clear_profile_locks(profile_dir: str) -> None:
    """
    Removes Chrome's "profile in use" lock files. They survive a killed browser or container
    restart and would make the next Chrome refuse to open the saved (logged-in) profile.
    """
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        path = os.path.join(profile_dir, name)
        if os.path.lexists(path):
            try:
                os.remove(path)
            except OSError:
                pass


# >


# < Logging related
def critical_error_log(possible_reason: str, stack_trace: Exception) -> None:
    """
    Function to log and print critical errors along with datetime stamp
    """
    print_lg(possible_reason, stack_trace, datetime.now(), from_critical=True)


def get_log_path():
    """
    Function to replace '//' with '/' for logs path
    """
    try:
        path = (logs_folder_path + "/log.txt").replace("//", "/")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path
    except Exception as e:
        critical_error_log(
            "Failed getting log path! So assigning default logs path: './logs/log.txt'",
            e,
        )
        return "logs/log.txt"


__logs_file_path = get_log_path()


def print_lg(
    *msgs: str | dict,
    end: str = "\n",
    pretty: bool = False,
    flush: bool = False,
    from_critical: bool = False,
) -> None:
    """
    Function to log and print. **Note that, `end` and `flush` parameters are ignored if `pretty = True`**
    """
    try:
        for message in msgs:
            pprint(message) if pretty else print(message, end=end, flush=flush)
            with open(__logs_file_path, "a+", encoding="utf-8") as file:
                file.write(str(message) + end)
    except Exception as e:
        trail = (
            f'Skipped saving this message: "{message}" to log.txt!'
            if from_critical
            else "We'll try one more time to log..."
        )
        safe_alert(
            f"log.txt in {logs_folder_path} is open or is occupied by another program! Please close it! {trail}",
            "Failed Logging",
        )
        if not from_critical:
            critical_error_log("Log.txt is open or is occupied by another program!", e)


# >


def buffer(speed: int = 0) -> None:
    """
    Function to wait within a period of selected random range.
    * Will not wait if input `speed <= 0`
    * Will wait within a random range of
      - `0.6 to 1.0 secs` if `1 <= speed < 2`
      - `1.0 to 1.8 secs` if `2 <= speed < 3`
      - `1.8 to speed secs` if `3 <= speed`
    """
    if speed <= 0:
        return
    elif speed <= 1 and speed < 2:
        return sleep(randint(6, 10) * 0.1)
    elif speed <= 2 and speed < 3:
        return sleep(randint(10, 18) * 0.1)
    else:
        return sleep(randint(18, round(speed) * 10) * 0.1)


def manual_login_retry(is_logged_in: callable, limit: int = 2) -> None:
    """
    Waits for you to finish logging in (captcha, 2FA, ...) in the live browser.
    """
    count = 0
    while not is_logged_in():
        print_lg("Seems like you're not logged in!")
        button = "Done, continue"
        message = f'Finish LinkedIn login in the live browser (captcha, 2FA...), then click "{button}".'
        if count > limit:
            button = "Skip confirmation"
            message = f'If you\'re seeing this even after you logged in, click "{button}". Seems like auto login confirmation failed!'
        count += 1
        if pause_for_user(message, "LinkedIn login needed", button) and count > limit:
            return


def lookup_custom_answer(label: str, custom_answers: list[dict]) -> str | None:
    """
    Your own answer for a question (Settings → Questions → custom answers): the first entry
    whose `match` appears in the label, case-insensitively. None when nothing matches.
    """
    text = (label or "").lower()
    if not text:
        return None
    for entry in custom_answers or []:
        match = (entry.get("match") or "").strip().lower()
        if match and match in text:
            return entry.get("answer", "")
    return None


DATE_POSTED_F_TPR = {
    "Past month": "r2592000",
    "Past week": "r604800",
    "Past 24 hours": "r86400",
}

SORT_BY_URL = {
    "Most recent": "DD",
    "Most relevant": "R",
}


EXPERIENCE_LEVEL_F_E = {
    "Internship": "1",
    "Entry level": "2",
    "Associate": "3",
    "Mid-Senior level": "4",
    "Director": "5",
    "Executive": "6",
}

JOB_TYPE_F_JT = {
    "Full-time": "F",
    "Part-time": "P",
    "Contract": "C",
    "Temporary": "T",
    "Volunteer": "V",
    "Internship": "I",
    "Other": "O",
}

ON_SITE_F_WT = {
    "On-site": "1",
    "Remote": "2",
    "Hybrid": "3",
}

SALARY_F_SB2 = {
    "$40,000+": "1",
    "$60,000+": "2",
    "$80,000+": "3",
    "$100,000+": "4",
    "$120,000+": "5",
    "$140,000+": "6",
    "$160,000+": "7",
    "$180,000+": "8",
    "$200,000+": "9",
}


# LinkedIn location ids. /jobs/search-results/ ignores the `location` text parameter but keeps
# `geoId` (seen in the page's own location links). Others are set through the location box.
GEO_IDS = {
    "united states": "103644278",
    "european union": "91000000",
    "netherlands": "102890719",
    "worldwide": "92000000",
    "canada": "101174742",
    "united kingdom": "101165590",
    "germany": "101282230",
    "india": "102713980",
    "australia": "101452733",
}


def geo_id_for(location: str) -> str | None:
    return GEO_IDS.get(" ".join((location or "").lower().split()))


def build_jobs_search_url(
    keywords: str,
    *,
    date_posted: str = "",
    sort_by: str = "",
    location: str = "",
    easy_apply_only: bool = False,
    experience_level: list[str] = [],
    job_type: list[str] = [],
    on_site: list[str] = [],
    salary: str = "",
    under_10_applicants: bool = False,
    in_your_network: bool = False,
) -> str:
    """
    Build a LinkedIn jobs search URL with the search filters applied via query params.
    LinkedIn's AI-powered jobs search has no "All filters" panel, so the URL is how filters get applied.
    """
    from urllib.parse import urlencode

    def codes(values: list[str], mapping: dict[str, str]) -> str:
        return ",".join(mapping[value] for value in values if value in mapping)

    query: dict[str, str] = {"keywords": keywords}
    tpr = DATE_POSTED_F_TPR.get((date_posted or "").strip())
    if tpr:
        query["f_TPR"] = tpr
    sort = SORT_BY_URL.get((sort_by or "").strip())
    if sort:
        query["sortBy"] = sort
    if location.strip():
        geo_id = geo_id_for(location)
        if geo_id:
            query["geoId"] = geo_id
        else:
            query["location"] = location.strip()
    if easy_apply_only:
        query["f_AL"] = "true"
    for param, values, mapping in (
        ("f_E", experience_level, EXPERIENCE_LEVEL_F_E),
        ("f_JT", job_type, JOB_TYPE_F_JT),
        ("f_WT", on_site, ON_SITE_F_WT),
    ):
        if codes(values, mapping):
            query[param] = codes(values, mapping)
    if salary in SALARY_F_SB2:
        query["f_SB2"] = SALARY_F_SB2[salary]
    if under_10_applicants:
        query["f_EA"] = "true"
    if in_your_network:
        query["f_JIYN"] = "true"
    return "https://www.linkedin.com/jobs/search/?" + urlencode(query)


def unsupported_search_filters(**filters) -> list[str]:
    """
    Returns the names of the given filters that are set. Use it for filters that can't be
    applied through the search URL (they need IDs or the old "All filters" panel).
    """
    return [name for name, value in filters.items() if value]


def is_browser_gone(error: Exception) -> bool:
    """
    True if `error` means the browser window or WebDriver session is gone.
    Element lookup errors like `TimeoutException` subclass `WebDriverException`
    but don't mean the browser closed, so only the base class itself counts.
    """
    from selenium.common.exceptions import (
        InvalidSessionIdException,
        NoSuchWindowException,
        WebDriverException,
    )

    return (
        isinstance(error, (NoSuchWindowException, InvalidSessionIdException))
        or type(error) is WebDriverException
    )


def calculate_date_posted(time_string: str) -> datetime | None | ValueError:
    """
    Function to calculate date posted from string.
    Returns datetime object | None if unable to calculate | ValueError if time_string is invalid
    Valid time string examples:
    * 10 seconds ago
    * 15 minutes ago
    * 2 hours ago
    * 1 hour ago
    * 1 day ago
    * 10 days ago
    * 1 week ago
    * 1 month ago
    * 1 year ago
    """
    import re

    time_string = time_string.strip()
    now = datetime.now()

    match = re.search(
        r"(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago",
        time_string,
        re.IGNORECASE,
    )

    if match:
        try:
            value = int(match.group(1))
            unit = match.group(2).lower()

            if "second" in unit:
                return now - timedelta(seconds=value)
            elif "minute" in unit:
                return now - timedelta(minutes=value)
            elif "hour" in unit:
                return now - timedelta(hours=value)
            elif "day" in unit:
                return now - timedelta(days=value)
            elif "week" in unit:
                return now - timedelta(weeks=value)
            elif "month" in unit:
                return now - timedelta(days=value * 30)  # Approximation
            elif "year" in unit:
                return now - timedelta(days=value * 365)  # Approximation
        except (ValueError, IndexError):
            # Fallback for cases where parsing fails
            pass

    # If regex doesn't match, or parsing failed, return None.
    # This will skip jobs where the date can't be determined, preventing crashes.
    return None


def convert_to_json(data) -> dict:
    """
    Function to convert data to JSON, if unsuccessful, returns `{"error": "Unable to parse the response as JSON", "data": data}`
    """
    try:
        result_json = json.loads(data)
        return result_json
    except json.JSONDecodeError:
        return {"error": "Unable to parse the response as JSON", "data": data}


def truncate_text(
    data, max_length: int = 131000, suffix: str = "...[TRUNCATED]"
) -> str:
    """
    Function to truncate data before it's saved to the history, so one huge field can't fail the save.
    * Takes in `data` of any type and converts to string
    * Takes in `max_length` of type `int` - maximum allowed length (default: 131000, leaving room for suffix)
    * Takes in `suffix` of type `str` - text to append when truncated
    * Returns truncated string if data exceeds max_length
    """
    try:
        # Convert data to string
        str_data = str(data) if data is not None else ""

        # If within limit, return as-is
        if len(str_data) <= max_length:
            return str_data

        # Truncate and add suffix
        truncated = str_data[: max_length - len(suffix)] + suffix
        return truncated
    except Exception as e:
        return f"[ERROR CONVERTING DATA: {e}]"
