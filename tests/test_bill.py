import pytest
import allure
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utilities.excel_reader import *
from openpyxl.reader.excel import ExcelReader
from validations.bill_validations import BillValidations
from pages.login_page import LoginPage
from pages.bill_page import BillPage
from utilities.excel_reader import get_bill_data
from utilities.helpers import take_screenshot
from config.config import USERNAME, PASSWORD
from utilities.menu_utils import verify_menu_or_skip
from utilities.soft_assert import SoftAssert

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


    soft = SoftAssert()

    with allure.step("Step 1: Login to DMS"):
        login = LoginPage(driver)
        login.login(USERNAME, PASSWORD)
        time.sleep(1)
        take_screenshot(driver, "bill_01_Login")

    with allure.step("Step 2: Verify Bill Menu Availability"):
        verify_menu_or_skip(
            driver,
            "Bill/New Invoice"
        )

    with allure.step("Step 2: Navigate to Bill/New Invoice"):
        bill = BillPage(driver)
        bill.navigate_to_bill()
        take_screenshot(driver, "bill_02_Menu")

    with allure.step("Step 3: Verify Beat"):
        try:
         bill.verify_beat()
         take_screenshot(driver, "Verify_Beat")

        except Exception as e:
         soft.record_exception("Beat", e)

    # with allure.step("Select Client Type"):
    #     bill.client_type()
    #     take_screenshot(driver, "Client Type Selected")

    with allure.step("Verify show dropdown"):
        try:
         bill.verify_show_dropdown()
         take_screenshot(driver, "Verify show dropdown")
        except Exception as e:
         soft.record_exception("dropdown", e)

    with allure.step("Excel download"):
        try:
         bill.click_excel()
         take_screenshot(driver, "Excel Download")
        except Exception as e:
         soft.record_exception("Excel", e)

    with allure.step("Verify Pagination"):
        try:
         bill.verify_pagination()
         take_screenshot(driver, "Pagination Verified")
        except Exception as e:
         soft.record_exception("Pagination", e)

    with allure.step("Search Customer"):
        try:
         bill.search_customer()
         take_screenshot(driver, "Search Customer")
        except Exception as e:
         soft.record_exception("search customer", e)

    with allure.step("Select Customer"):
        try:
         selected_customer = bill.select_customer("Demo 4")
         take_screenshot(driver, "Customer Selected")
        except Exception as e:
         soft.record_exception("Select Customer", e)

    with allure.step("Distributor"):
        try:
         bill.verify_page_elements(
            customer_name=selected_customer,
            distributor_name="Demo Distributor 1"
         )
         take_screenshot(driver, "Distributor Verified")
        except Exception as e:
         soft.record_exception("distributor", e)


    with allure.step("Verify Product Category Dropdowns"):
        try:
         bill.verify_product_category_dropdowns()
         take_screenshot(driver, "Product_Category_Dropdowns")
        except Exception as e:
         soft.record_exception("Product Dropdown", e)

    with allure.step("Product page show dropdown Verified"):
        try:
         bill.product_page_show_dropdown()
         take_screenshot(driver, "product page show dropdown Verified")
        except Exception as e:
         soft.record_exception("Product Dropdown Verification", e)

    with allure.step("Pagination - Iterate through pages"):
        try:
         bill.verify_pagination_using_next()
         take_screenshot(driver, "Pagination Verified")
        except Exception as e:
         soft.record_exception("Pagination", e)

    with allure.step("Product grid headers"):
        try:
         bill.verify_product_grid_headers()
         take_screenshot(driver, "product_grid_headers")
        except Exception as e:
         soft.record_exception("Product grid", e)

    with allure.step("Verify Inventory Popup"):
        try:
         bill.verify_inventory_popup_for_all_products()
         time.sleep(1)
         take_screenshot(driver, "inventory_popup")
        except Exception as e:
         soft.record_exception("Inventory", e)

    with allure.step("Click Filter"):
        try:
         bill.click_filter()
         take_screenshot(driver, "inventory_popup")
        except Exception as e:
         soft.record_exception("Filter", e)

    with allure.step("Move to Favourite"):
        try:
         bill.move_to_favourite()
         take_screenshot(driver, "Favourite Tab")
        except Exception as e:
         soft.record_exception("Favourite", e)

    with allure.step("Click Focus"):
        try:
         bill.click_focus()
         take_screenshot(driver, "Click Focus")
        except Exception as e:
         soft.record_exception("Beat", e)

    with allure.step("Enter Quantities"):

        test_data = get_bill_data()
        successful_rows = []

        for row in test_data:
            try:
                bill.enter_quantity(
                    row["Row"],
                    row["Qty"]
                )

                popup_found, msg = bill.handle_inventory_popup()

                if popup_found:
                    print(f"Inventory Popup: {msg}")
                    continue  # ✅ Valid here

                successful_rows.append(row)

            except Exception as e:
                print(f"Error: {e}")

        take_screenshot(driver, "quantities_entered")

    with allure.step("Get Product Name"):
        try:

         product_name = bill.get_product_name(1)
         print("Product:", product_name)

         take_screenshot(driver, "product_name")
        except Exception as e:
         soft.record_exception("Product Name", e)

    with allure.step("Calculate Bill"):

        bill.click_calculate()

        time.sleep(1)

        # Get Bill Summary
        summary = bill.get_bill_summary()

        print("\n" + "=" * 60)
        print("BILL SUMMARY")
        print("=" * 60)

        for key, value in summary.items():
            print(f"{key:<20}: {value}")

        print("=" * 60)

        # Verify Final Amount
        final_amount = bill.get_final_amount()
        soft.verify_true(
            final_amount > 0,
            "Final Amount should be greater than zero."
        )

        print(f"\nFinal Amount = {final_amount}")

        # Print Excel quantities entered
        print("\nEntered Quantities:")
        for row in successful_rows:
            print(
                f"Row={row['Row']}, "
                f"Excel Qty={row['Qty']}"
            )

        take_screenshot(driver, "calculated_bill")

    with allure.step("Save as Draft"):

        bill.click_draft()

        take_screenshot(driver, "draft_saved")

    with allure.step("Verify Draft Details"):

        draft = bill.get_latest_draft_details()

        expected_items = summary["Total Item"]
        expected_amount = summary["Amount"]

        print("\nLATEST DRAFT")
        print("=" * 60)
        for k, v in draft.items():
            print(f"{k:<18}: {v}")
        print("=" * 60)

        # Comparison Log
        print("\nCOMPARISON")
        print("=" * 60)
        print(f"Summary Total Item : {summary['Total Item']}")
        print(f"Draft No Of Items  : {draft['No Of Items']}")
        print(f"Summary Qty        : {summary['Qty (pcs)']}")
        print(f"Draft Qty          : {draft['Draft Qty']}")
        print(f"Summary Amount     : {summary['Amount']}")
        print(f"Draft Amount       : {draft['Draft Amount']}")
        print("=" * 60)

        soft.verify_equal(
            int(draft["No Of Items"]),
            int(summary["Total Item"]),
            "No Of Items Verification"
        )

        soft.verify_equal(
            int(draft["Draft Qty"]),
            int(summary["Qty (pcs)"]),
            "Draft Qty Verification"
        )

        soft.verify_equal(
            round(float(draft["Draft Amount"])),
            round(float(summary["Amount"])),
            "Draft Amount Verification"
        )

        take_screenshot(driver, "Draft Details")

    with allure.step("Click Order"):

        bill.go_to_product_page()

        take_screenshot(driver, "Order button opened")



    with allure.step("click save"):

        bill.click_save()

        take_screenshot(driver, "bill_Save")



    with allure.step("add discount"):
        bill.add_discount()
        time.sleep(1)
        take_screenshot(driver, "bill_Discount")

    with allure.step("Verify discount amount and total Payable"):
        take_screenshot(driver, "Before Verification")
        bill.verify_amount()
        time.sleep(1)
        take_screenshot(driver, "amount_Verified")


    with allure.step("Add to Cart"):
        bill.click_add_to_cart()
        time.sleep(1)
        take_screenshot(driver, "bill_07_Cart")

    with allure.step("Step 8: Confirm Order"):
        bill.confirm_order()
        time.sleep(5)
        take_screenshot(driver, "Confirm Order")

    with allure.step("Step 9: Print and Verify Invoice"):
        bill.click_print_and_switch()
        allure.attach(
            driver.current_url,
            name="Invoice URL",
            attachment_type=allure.attachment_type.TEXT
        )

    soft.assert_all()