import pytest
import allure
import time
from pages.login_page import LoginPage
from pages.purchagereturn import purchageReturnPage
from utilities.helpers import take_screenshot
from config.config import USERNAME, PASSWORD
from utilities.menu_utils import verify_menu_or_skip
@allure.epic("DMS Application")
@allure.feature("purchage Return")
@allure.story("Process purchage Return Without Reference")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Process purchage Return")
@allure.description("""
    Test verifies the complete sale return flow:
    - Login to DMS
    - Navigate to Sale Return
    - Select customer
    - Choose Without Reference return type
    - Select product and enter quantity
    - Calculate, Save and Receive product
    - Confirm and verify completion
""")
@allure.tag("regression", "salereturn")
def test_purchage_return(driver):

    with allure.step("Step 1: Login to DMS"):
        login = LoginPage(driver)
        login.login(USERNAME, PASSWORD)
        time.sleep(5)
        take_screenshot(driver, "purchagereturn_01_Login")

    with allure.step("Step 2: Verify purchase return Menu Availability"):
         verify_menu_or_skip(driver, "Purchase Return")

    with allure.step("Step 2: Navigate to purchage Return"):
        purchagereturn = purchageReturnPage(driver)
        purchagereturn.navigate_to_purchage_return()
        time.sleep(3)
        take_screenshot(driver, "purchagereturn")

    with allure.step("Step 2.1: Enter customer"):
        purchagereturn.search_customer()
        time.sleep(5)
        take_screenshot(driver, "searchcustomer_2.1_Customer")

    with allure.step("Step 3: Select Customer"):
        purchagereturn.select_customer("vel")
        time.sleep(5)
        take_screenshot(driver, "purchagereturn_Customer")

    with allure.step("hamburger"):
        purchagereturn.hamburger()
        take_screenshot(driver, "Hamburger")

    with allure.step("Select Product"):
        purchagereturn.select_first_product()
        time.sleep(5)
        take_screenshot(driver, "select_first_product")

    with allure.step("enter quantity"):
        purchagereturn.enter_qty()
        take_screenshot(driver, "enter_qty")

    with allure.step("Calculate"):
        purchagereturn.click_calculate()
        take_screenshot(driver, "calculate")

    with allure.step("click save"):
        purchagereturn.click_save()
        take_screenshot(driver, "save")

    with allure.step("click place return"):
        purchagereturn.click_place_return()
        take_screenshot(driver, "place_return")
    with allure.step("confirm return"):
        purchagereturn.confirm_return()
        take_screenshot(driver, "confirm_return")

    with allure.step("click ok"):
        purchagereturn.click_ok()
        take_screenshot(driver, "order ok")

