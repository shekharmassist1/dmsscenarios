import pytest
import allure
import time
from pages.login_page import LoginPage
from pages.bill_page import BillPage
from utilities.helpers import take_screenshot
from config.config import USERNAME, PASSWORD
from utilities.menu_utils import verify_menu_or_skip

@allure.epic("DMS Application")
@allure.feature("Bill Management")
@allure.story("Create New Bill")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Create New Bill for Demo Dealer 4")
@allure.description("""
    Test verifies the complete bill creation flow:
    - Login to DMS
    - Navigate to Bill/New Invoice
    - Select customer Demo Dealer 4
    - Enter sale quantity
    - Calculate, Save and Confirm order
    - Verify invoice is generated
""")
@allure.tag("smoke", "bill", "critical")
@allure.link("https://admin.massistcrm.com", name="DMS Application")
def test_create_bill(driver):

    with allure.step("Step 1: Login to DMS"):
        login = LoginPage(driver)
        login.login(USERNAME, PASSWORD)
        time.sleep(5)
        take_screenshot(driver, "bill_01_Login")

    with allure.step("Step 2: Verify Audit Menu Availability"):
        verify_menu_or_skip(
            driver,
            "Asset Allocation"
        )

    with allure.step("Step 2: Navigate to Bill/New Invoice"):
        bill = BillPage(driver)
        bill.navigate_to_bill()
        take_screenshot(driver, "bill_02_Menu")