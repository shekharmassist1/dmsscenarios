import os

import allure
import pytest
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException

from config import USERNAME, PASSWORD
from pages.login_page import LoginPage
from utilities.soft_assert import SoftAssert


def _build_driver():
    headless = os.environ.get("HEADLESS", "false").strip().lower() not in ("false", "0", "no")
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    return driver


@pytest.fixture
def logged_in_driver():
    max_attempts = 3
    last_exc = None
    for attempt in range(max_attempts):
        drv = _build_driver()
        try:
            LoginPage(drv).open().login(USERNAME, PASSWORD)
        except (TimeoutException, WebDriverException) as exc:

            last_exc = exc
            drv.quit()
            continue
        else:
            yield drv
            drv.quit()
            return
    raise last_exc


@pytest.fixture
def soft_assert(request):
    sa = SoftAssert()
    yield sa
    if sa.errors:
        drv = request.node.funcargs.get("driver") or request.node.funcargs.get("logged_in_driver")
        if drv is not None:
            try:
                allure.attach(
                    drv.get_screenshot_as_png(),
                    name="failure_screenshot",
                    attachment_type=allure.attachment_type.PNG,
                )
            except Exception:
                pass
    sa.assert_all()
