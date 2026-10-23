'''
Author:     Sai Vignesh Golla
LinkedIn:   https://www.linkedin.com/in/saivigneshgolla/

Copyright (C) 2024 Sai Vignesh Golla

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/GodsScion/Auto_job_applier_linkedIn

Support me: https://github.com/sponsors/GodsScion

version:    26.01.20.5.08
'''

import os

from modules.helpers import get_default_temp_profile, make_directories
from config.settings import run_in_background, stealth_mode, disable_extensions, safe_mode, logs_folder_path
from config.questions import default_resume_path
if stealth_mode:
    import undetected_chromedriver as uc
else:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from modules.helpers import (
    clear_profile_locks,
    container_chrome_kwargs,
    critical_error_log,
    print_lg,
)
from selenium.common.exceptions import SessionNotCreatedException

def _apply_chrome_stability_options(options) -> None:
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-popup-blocking")


def _create_container_chrome(options, container: dict, guest: bool):
    """Worker container: OS Chromium + its chromedriver, profile on the data volume (keeps you logged in)."""
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # The bot reads English page text ("Sign in", "Easy Apply", ...): keep LinkedIn in English
    # whatever the container's location says.
    options.add_argument("--lang=en-US")
    options.add_experimental_option("prefs", {"intl.accept_languages": "en-US,en"})
    profile = get_default_temp_profile() if guest else container["user_data_dir"]
    os.makedirs(profile, exist_ok=True)
    clear_profile_locks(profile)
    print_lg(f"Starting Chromium {container.get('version_main', '')} with profile {'(guest)' if guest else profile}")
    if stealth_mode:
        kwargs = {k: v for k, v in container.items() if k != "user_data_dir"}
        return uc.Chrome(options=options, user_data_dir=profile, **kwargs)
    options.binary_location = container["browser_executable_path"]
    options.add_argument(f"--user-data-dir={profile}")
    return webdriver.Chrome(options=options, service=Service(container["driver_executable_path"]))


def createChromeSession(isRetry: bool = False):
    make_directories([logs_folder_path+"/screenshots",default_resume_path])
    container = container_chrome_kwargs(os.environ)
    if not container:
        # Set in the worker image (docker/stack/worker.Dockerfile).
        raise SystemExit("CHROME_BINARY and CHROMEDRIVER are not set: the bot runs in the worker container (`make up`).")
    # Set up WebDriver with Chrome Profile
    options = uc.ChromeOptions() if stealth_mode else Options()
    if run_in_background:   options.add_argument("--headless")
    if disable_extensions:  options.add_argument("--disable-extensions")
    _apply_chrome_stability_options(options)
    driver = _create_container_chrome(options, container, guest=isRetry or safe_mode)
    driver.maximize_window()
    wait = WebDriverWait(driver, 5)
    actions = ActionChains(driver)
    return options, driver, actions, wait



try:
    options, driver, actions, wait = None, None, None, None
    options, driver, actions, wait = createChromeSession()
except SessionNotCreatedException as e:
    critical_error_log("Failed to create Chrome Session, retrying with guest profile", e)
    try:
        driver.quit()
    except Exception:
        pass
    try:
        options, driver, actions, wait = createChromeSession(True)
    except Exception as retry_error:
        critical_error_log("In Opening Chrome (guest profile retry)", retry_error)
        raise SystemExit(f"Could not start Chrome: {retry_error}")
except Exception as e:
    msg = 'Could not start Chrome. If this keeps happening, try turning on "safe_mode" in Settings (uses a throwaway profile).'
    if isinstance(e,TimeoutError): msg = "Couldn't download Chrome-driver. Turn off stealth_mode in Settings!"
    print_lg(msg)
    critical_error_log("In Opening Chrome", e)
    try: driver.quit()
    except Exception: pass
    # The worker records the run as failed with these last lines.
    raise SystemExit(f"{msg}\n{e}")
