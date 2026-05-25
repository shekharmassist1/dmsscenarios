import pytest
import allure
import time
from pages.login_page import LoginPage
from pages.mysale_page import MySalePage
from utilities.helpers import take_screenshot
from config.config import USERNAME, PASSWORD

@allure.epic("DMS Application")
@allure.feature("My Sales")
@allure.story("Edit Existing Sale")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Edit and Update Existing Sale Order")
@allure.description("""
    Test verifies the sale edit flow:
    - Login to DMS
    - Navigate to My Sales
    - Edit existing order
    - Update and confirm
    - Verify invoice generated
""")
@allure.tag("regression", "mysale")
def test_edit_mysale(driver):
    invoice_id = "215744513"

    with allure.step("Step 1: Login to DMS"):
        login = LoginPage(driver)
        login.login(USERNAME, PASSWORD)
        time.sleep(5)
        take_screenshot(driver, "mysale_01_Login")

    with allure.step("Step 2: Navigate to My Sales"):
        mysale = MySalePage(driver)
        mysale.navigate_to_mysale()
        time.sleep(5)
        take_screenshot(driver, "mysale_02_Page")

    with allure.step(f"Step 3: Click Edit for Invoice {invoice_id}"):
        mysale.click_edit(invoice_id)
        time.sleep(20)
        take_screenshot(driver, "mysale_03_Edit")

    with allure.step("Step 4: Save Changes"):
        mysale.click_save()
        time.sleep(5)
        take_screenshot(driver, "mysale_04_Saved")

    with allure.step("Step 5: Update Sale"):
        mysale.click_update_sale()
        time.sleep(5)
        take_screenshot(driver, "mysale_05_Updated")

    with allure.step("Step 6: Confirm Order"):
        mysale.confirm_order()
        time.sleep(5)
        take_screenshot(driver, "mysale_06_Confirmed")

    with allure.step("Step 7: Print Invoice"):
        mysale.click_print_and_switch()
        take_screenshot(driver, "mysale_07_Invoice")