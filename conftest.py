# conftest.py (in ROOT folder, not inside tests/)
import pytest
import allure
import json
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from config.config import BASE_URL, IMPLICIT_WAIT

def pytest_configure(config):
    os.makedirs("allure-results", exist_ok=True)
    os.makedirs("screenshots", exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    executor = {
        "name": "QA Team",
        "type": "local",
        "buildName": "DMS Regression Suite",
        "reportName": "DMS Automation Report"
    }
    with open("allure-results/executor.json", "w") as f:
        json.dump(executor, f)

@pytest.fixture(scope="function")
def driver():
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.maximize_window()
    driver.implicitly_wait(IMPLICIT_WAIT)
    driver.get(BASE_URL)
    yield driver
    driver.quit()

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        try:
            driver = item.funcargs["driver"]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"screenshots/FAILED_{item.name}_{timestamp}.png"
            driver.save_screenshot(screenshot_path)
            with open(screenshot_path, "rb") as f:
                allure.attach(
                    f.read(),
                    name=f"FAILED_{item.name}",
                    attachment_type=allure.attachment_type.PNG
                )
        except KeyError:
            pass