import pytest
import allure
import time
from selenium.webdriver.common.by import By

from pages.login_page import LoginPage
from pages.reports_page import ReportsPage
from utilities.helpers import take_screenshot
from config.config import USERNAME, PASSWORD
from utilities.menu_utils import verify_menu_or_skip

@allure.epic("DMS Application")
@allure.feature("Reports")
@allure.story("Verify Reports Navigation")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Open Reports and Verify All Reports")
@allure.tag("regression", "reports")
def test_click_all_reports(driver):

    with allure.step("Step 1: Login"):
        login = LoginPage(driver)
        login.login(USERNAME, PASSWORD)
        time.sleep(5)
        take_screenshot(driver, "reports_01_login")
    with allure.step("Step 2: Verify Bill Menu Availability"):
         verify_menu_or_skip(driver, "Reports")

    with allure.step("Step 2: Navigate to Reports"):
        reports = ReportsPage(driver)
        reports.navigate_to_reports()
        time.sleep(3)
        take_screenshot(driver, "reports_02_page")

    with allure.step("Step 3: Verify Date Filters"):

        filters = [
            "Today",
            "Yesterday",
            "Last 7 Days",
            "Last 30 Days",
            "This Month",
            "Last Month",
            "Year"
        ]

        for filter_name in filters:
            reports.click_date_filter(filter_name)
            time.sleep(2)

            take_screenshot(
                driver,
                f"DateFilter_{filter_name.replace(' ', '_')}"
            )

    with allure.step("Step 4: Verify Reports"):

        reports_list = [
            ("Sale Report", "//label[normalize-space()='Sale Report']"),
            ("Sale Details Report", "//label[normalize-space()='Sale Details Report']"),
            ("Order Report", "//label[normalize-space()='Order Report']"),
            ("Return Report", "//label[normalize-space()='Return Report']"),
            ("Fill Rate", "//label[normalize-space()='Fill Rate']"),
            ("SNS Report", "//label[normalize-space()='SNS Report']"),
            ("Current Stock", "//label[normalize-space()='Current Stock']"),
            ("Claim Report", "//label[normalize-space()='Claim Report']"),
            ("Purchase Report", "//label[normalize-space()='Purchase Report']"),
            ("Customer Master", "//label[normalize-space()='Customer Master']")
        ]

        not_shown = []
        for report_name, xpath in reports_list:

            with allure.step(f"Verify {report_name}"):

                # Some reports are switched on per company (e.g. Purchase Report via the
                # AdminSetting 'DMSPurchaseReport' flag), so a missing one is noted and skipped.
                if not [e for e in driver.find_elements(By.XPATH, xpath) if e.is_displayed()]:
                    not_shown.append(report_name)
                    allure.attach(
                        f"'{report_name}' is not shown on the Reports page for this user/company.",
                        name=f"{report_name} not shown",
                        attachment_type=allure.attachment_type.TEXT,
                    )
                    print(f"⚠ Not shown, skipped: {report_name}")
                    continue

                reports.click_report_and_capture(
                    report_name,
                    xpath
                )

                take_screenshot(
                    driver,
                    f"Report_{report_name.replace(' ', '_')}"
                )

                time.sleep(2)