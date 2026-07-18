import pytest
import allure
import time
from pages.login_page import LoginPage
from pages.salereturn_page import SaleReturnPage
from utilities.helpers import take_screenshot
from config.config import USERNAME, PASSWORD
from utilities.menu_utils import verify_menu_or_skip
@allure.epic("DMS Application")
@allure.feature("Sale Return")
@allure.story("Process Sale Return Without Reference")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Process Sale Return for Demo Dealer 4")
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
def test_sale_return(driver):

    with allure.step("Step 1: Login to DMS"):
        login = LoginPage(driver)
        login.login(USERNAME, PASSWORD)
        time.sleep(5)
        take_screenshot(driver, "salereturn_01_Login")
    with allure.step("Step 2: Verify salereturn Menu Availability"):
         verify_menu_or_skip(driver, "Sale Return")

    with allure.step("Step 2: Navigate to Sale Return"):
        salereturn = SaleReturnPage(driver)
        salereturn.navigate_to_sale_return()
        time.sleep(3)
        take_screenshot(driver, "salereturn_02_Menu")

    with allure.step("Step 2.1: Enter customer"):
        salereturn.search_customer("Demo 4")
        time.sleep(5)
        take_screenshot(driver, "searchcustomer_2.1_Customer")

    with allure.step("Step 3: Select Customer - Demo Dealer 4"):
        salereturn.select_customer("Demo Dealer 4")
        time.sleep(5)
        take_screenshot(driver, "salereturn_03_Customer")

    with allure.step("Step 4: Select Return Type - Without Reference"):
        salereturn.select_return_type("Without Reference")
        time.sleep(25)
        take_screenshot(driver, "salereturn_04_Type")

    with allure.step("Step 5: Select First Product"):
        salereturn.select_first_product()
        take_screenshot(driver, "salereturn_05_Product")

    with allure.step("Step 6: Enter Quantity = 1"):
        salereturn.enter_qty("1")
        time.sleep(5)
        take_screenshot(driver, "salereturn_06_Qty")

    with allure.step("Step 7: Calculate"):
        salereturn.click_calculate()
        time.sleep(10)
        take_screenshot(driver, "salereturn_07_Calculated")

    with allure.step("Step 8: Save"):
        salereturn.click_save()
        time.sleep(5)
        take_screenshot(driver, "salereturn_08_Saved")

    with allure.step("Step 9: Product Receive"):
        salereturn.click_product_receive()
        time.sleep(5)
        take_screenshot(driver, "salereturn_09_Receive")

    with allure.step("Step 10: Confirm"):
        salereturn.confirm_order()
        time.sleep(5)
        take_screenshot(driver, "salereturn_10_Confirmed")

    with allure.step("Step 11: Click OK - Verify Completion"):
        salereturn.click_ok()
        time.sleep(5)
        take_screenshot(driver, "salereturn_11_Done")