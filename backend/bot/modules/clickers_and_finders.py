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

from config.settings import click_gap, smooth_scroll
from modules.helpers import buffer, print_lg
from selenium.common.exceptions import ElementClickInterceptedException, ElementNotInteractableException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver

# Click Functions
def is_filter_option_selected(driver: WebDriver, element: WebElement) -> bool:
    '''
    Returns True if a LinkedIn jobs filter option (checkbox, radio, or pill) is already selected.
    '''
    current = element
    for _ in range(3):
        try:
            aria_checked = current.get_attribute("aria-checked")
            if aria_checked is not None:
                return aria_checked.lower() == "true"
            aria_pressed = current.get_attribute("aria-pressed")
            if aria_pressed is not None:
                return aria_pressed.lower() == "true"
            classes = current.get_attribute("class") or ""
            if "filter-button--selected" in classes or "artdeco-pill--selected" in classes:
                return True
        except Exception:
            pass
        try:
            current = current.find_element(By.XPATH, "..")
        except Exception:
            break

    try:
        label = element.find_element(By.XPATH, "./ancestor::label[1]")
        for xpath in (
            "./preceding-sibling::input[@type='checkbox' or @type='radio']",
            "./following-sibling::input[@type='checkbox' or @type='radio']",
            "../input[@type='checkbox' or @type='radio']",
            ".//input[@type='checkbox' or @type='radio']",
        ):
            try:
                return label.find_element(By.XPATH, xpath).is_selected()
            except Exception:
                continue
        for_id = label.get_attribute("for")
        if for_id:
            return driver.find_element(By.ID, for_id).is_selected()
    except Exception:
        pass

    return False

def _filter_span_xpaths(text: str, section: str | None = None) -> list[str]:
    xpaths = []
    if section:
        xpaths.extend(
            [
                f'//h3[contains(normalize-space(.),"{section}")]/ancestor::fieldset[1]//span[normalize-space(.)="{text}"]',
                f'//legend[contains(normalize-space(.),"{section}")]/ancestor::fieldset[1]//span[normalize-space(.)="{text}"]',
                f'//fieldset[.//*[contains(normalize-space(.),"{section}")]]//span[normalize-space(.)="{text}"]',
                f'//div[contains(@class,"search-reusables__filter") and .//*[contains(normalize-space(.),"{section}")]]//span[normalize-space(.)="{text}"]',
                f'//*[contains(normalize-space(.),"{section}")]/following::span[normalize-space(.)="{text}"][1]',
            ]
        )
    xpaths.append(f'.//span[normalize-space(.)="{text}"]')
    return xpaths


def wait_span_click(driver: WebDriver, text: str, time: float=5.0, click: bool=True, scroll: bool=True, scrollTop: bool=False, section: str | None = None, quiet: bool = False) -> WebElement | bool:
    '''
    Finds the span element with the given `text`.
    - Returns `WebElement` if found, else `False` if not found.
    - Clicks on it if `click = True`.
    - Will spend a max of `time` seconds in searching for each element.
    - Will scroll to the element if `scroll = True`.
    - Will scroll to the top if `scrollTop = True`.
    - If `section` is set (e.g. "Date posted"), search within that filter group first.
    - Won't log a missing element if `quiet = True`, for elements that may be absent.
    '''
    if text:
        for xpath in _filter_span_xpaths(text, section):
            try:
                button = WebDriverWait(driver, time).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                if scroll:
                    scroll_to_view(driver, button, scrollTop)
                if click:
                    if not is_filter_option_selected(driver, button):
                        button.click()
                        buffer(click_gap)
                return button
            except Exception:
                continue
        if not quiet:
            print_lg("Click Failed! Didn't find '" + text + "'")
        return False

def close_after_submit(driver: WebDriver, actions) -> None:
    """
    Closes LinkedIn's "Application sent" dialog after a successful submit. It doesn't always
    show a "Done" button, which is fine: Escape closes it too.
    """
    if not wait_span_click(driver, "Done", 2, quiet=True):
        actions.send_keys(Keys.ESCAPE).perform()

# Find functions
def find_by_class(driver: WebDriver, class_name: str, time: float=5.0) -> WebElement | Exception:
    '''
    Waits for a max of `time` seconds for element to be found, and returns `WebElement` if found, else `Exception` if not found.
    '''
    return WebDriverWait(driver, time).until(EC.presence_of_element_located((By.CLASS_NAME, class_name)))

# Scroll functions
def scroll_to_view(driver: WebDriver, element: WebElement, top: bool = False, smooth_scroll: bool = smooth_scroll) -> None:
    '''
    Scrolls the `element` to view.
    - `smooth_scroll` will scroll with smooth behavior.
    - `top` will scroll to the `element` to top of the view.
    '''
    if top:
        return driver.execute_script('arguments[0].scrollIntoView();', element)
    behavior = "smooth" if smooth_scroll else "instant"
    return driver.execute_script('arguments[0].scrollIntoView({block: "center", behavior: "'+behavior+'" });', element)

def try_xp(driver: WebDriver, xpath: str, click: bool=True) -> WebElement | bool:
    try:
        if click:
            driver.find_element(By.XPATH, xpath).click()
            return True
        else:
            return driver.find_element(By.XPATH, xpath)
    except: return False

def click_displayed(driver: WebDriver, xpath: str) -> bool:
    '''
    Clicks the first displayed element matching `xpath`. Returns `False` if there's none.
    Falls back to a JavaScript click when something (e.g. a sticky header) covers the element.
    '''
    displayed = [element for element in driver.find_elements(By.XPATH, xpath) if element.is_displayed()]
    if not displayed:
        return False
    element = displayed[0]
    scroll_to_view(driver, element, smooth_scroll=False)
    try:
        element.click()
    except (ElementClickInterceptedException, ElementNotInteractableException) as e:
        # First line only: the full message carries a long chromedriver stack trace.
        print_lg("Click was blocked, clicking with JavaScript instead:", e.msg.splitlines()[0] if e.msg else e)
        driver.execute_script("arguments[0].click();", element)
    return True

def try_linkText(driver: WebDriver, linkText: str) -> WebElement | bool:
    try:    return driver.find_element(By.LINK_TEXT, linkText)
    except:  return False
