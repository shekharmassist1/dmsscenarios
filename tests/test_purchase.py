import pytest
import allure
import time

from pages.login_page import LoginPage
from pages.purchage import purchaseOrder
from utilities.helpers import take_screenshot
from config.config import USERNAME, PASSWORD
from utilities.menu_utils import verify_menu_or_skip

@allure.epic("DMS Application")
@allure.feature("Bill Management")
@allure.story("Create purchase order")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Create purchase order for Demo Dealer 4")
@allure.description("""
    Test verifies the complete bill creation flow:
    - Login to DMS
    - Navigate to purchase order
    - Select customer vel
    - Enter order quantity
    - Calculate, Save and Confirm order
    - Verify invoice is generated
""")
@allure.tag("smoke", "bill", "critical")
@allure.link("https://admin.massistcrm.com", name="DMS Application")
def test_purchase_order(driver):

    with allure.step("Step 1: Login to DMS"):
        login = LoginPage(driver)
        login.login(USERNAME, PASSWORD)
        time.sleep(5)
        take_screenshot(driver, "bill_01_Login")
    with allure.step("Step 2: Verify purchase Menu Availability"):
         verify_menu_or_skip(driver, "Purchase Order")

    with allure.step("Step 3: Navigate to purchase order"):
        purchase = purchaseOrder(driver)
        purchase.navigate_to_purchase()
        take_screenshot(driver, "purchase_order")

    with allure.step("search customer"):
        purchase.search_customer()
        take_screenshot(driver, "search_customer")

    with allure.step("select customer"):
        purchase.select_customer("vel")
        take_screenshot(driver, "select_customer")
        time.sleep(2)


    with allure.step("sale_quantity"):
        purchase.enter_sale_qty("sale quantity")
        take_screenshot(driver, "sale_qty")

    with allure.step("click calculate"):
        purchase.click_calculate()
        take_screenshot(driver, "calculate")

    with allure.step("click save"):
        purchase.click_save()
        take_screenshot(driver, "save")

    with allure.step("place order"):
        purchase.place_order()
        take_screenshot(driver, "place_order")

    with allure.step("confirm order"):
        purchase.confirm_order()
        take_screenshot(driver, "confirm_order")

    with allure.step("click ok print message"):
        purchase.click_ok_print_message()
        take_screenshot(driver, "click_ok_print_message")

    with allure.step("verify my order page"):
        purchase.verify_my_order_page()
        take_screenshot(driver, "verify_my_order_page")

    with allure.step("first row print"):
        purchase.click_first_row_print()
        take_screenshot(driver, "first_row_print")

    with allure.step("click print"):
        purchase.click_print()
        take_screenshot(driver, "print")

    with allure.step("verify amount and screenshot"):
        purchase.verify_amount_and_screenshot()
        take_screenshot(driver, "verify_amount_and_screenshot")





