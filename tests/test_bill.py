import pytest
import allure
import time
from pages.login_page import LoginPage
from pages.bill_page import BillPage
from utilities.helpers import take_screenshot
from config.config import USERNAME, PASSWORD

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

    with allure.step("Step 2: Navigate to Bill/New Invoice"):
        bill = BillPage(driver)
        bill.navigate_to_bill()
        take_screenshot(driver, "bill_02_Menu")

    with allure.step("Step 3: Select Customer - Demo Dealer 4"):
        bill.select_customer("Demo Dealer 4")
        time.sleep(5)
        take_screenshot(driver, "bill_03_Customer")

    with allure.step("Step 4: Enter Sale Quantity = 10"):
        bill.enter_sale_qty("10")
        take_screenshot(driver, "bill_04_Qty")

    with allure.step("Step 5: Click Calculate"):
        bill.click_calculate()
        time.sleep(5)
        take_screenshot(driver, "bill_05_Calculated")

    with allure.step("Step 6: Save Bill"):
        bill.click_save()
        time.sleep(2)
        take_screenshot(driver, "bill_06_Saved")

    with allure.step("Step 7: Add to Cart"):
        bill.click_add_to_cart()
        time.sleep(5)
        take_screenshot(driver, "bill_07_Cart")

    with allure.step("Step 8: Confirm Order"):
        bill.confirm_order()
        time.sleep(5)
        take_screenshot(driver, "bill_08_Confirmed")

    with allure.step("Step 9: Print and Verify Invoice"):
        bill.click_print_and_switch()
        take_screenshot(driver, "bill_09_Invoice")
        allure.attach(
            driver.current_url,
            name="Invoice URL",
            attachment_type=allure.attachment_type.TEXT
        )