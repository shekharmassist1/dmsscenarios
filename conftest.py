# conftest.py (in ROOT folder, not inside tests/)
import pytest
import allure
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from config.config import BASE_URL, IMPLICIT_WAIT
import shutil
import os

def pytest_sessionstart(session):
    # Only run in master process
    if hasattr(session.config, "workerinput"):
        return

    folders = [
        "screenshots",
        "allure-results",
        "allure-report",
        "reports"
    ]

    for folder in folders:
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)

        os.makedirs(folder, exist_ok=True)

def pytest_configure(config):
    os.makedirs("screenshots", exist_ok=True)
    os.makedirs("allure-results", exist_ok=True)

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
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install())
    )

    try:
        driver.maximize_window()
        driver.implicitly_wait(IMPLICIT_WAIT)
        driver.get(BASE_URL)

        yield driver

    finally:
        driver.quit()

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        try:
            driver = item.funcargs.get("driver")

            if driver:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = (
                    f"screenshots/FAILED_{item.name}_{timestamp}.png"
                )

                try:
                    driver.save_screenshot(screenshot_path)

                    with open(screenshot_path, "rb") as f:
                        allure.attach(
                            f.read(),
                            name=f"FAILED_{item.name}",
                            attachment_type=allure.attachment_type.PNG
                        )

                except Exception as e:
                    print(f"Screenshot capture failed: {e}")

        except Exception as e:
            print(f"pytest_runtest_makereport failed: {e}")

