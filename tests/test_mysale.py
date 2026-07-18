import pytest
import allure
import time
from pages.login_page import LoginPage
from pages.mysale_page import MySalePage
from utilities.helpers import take_screenshot
from config.config import USERNAME, PASSWORD
from utilities.menu_utils import verify_menu_or_skip
from utilities.db_utils import DatabaseUtils

@allure.epic("DMS Application")
@allure.feature("My Sales")
@allure.story("Edit Existing Sale")
def test_edit_mysale(driver):

    with allure.step("Login"):
        login = LoginPage(driver)
        login.login(USERNAME, PASSWORD)
        time.sleep(5)
        take_screenshot(driver, "login")


    with allure.step("Navigate to My Sales"):
        mysale = MySalePage(driver)
        mysale.navigate_to_mysale()
        take_screenshot(driver, "mysale_page")

    with allure.step("orders from UI"):
        ui_orders=mysale.get_orders_from_ui()
        take_screenshot(driver, "orders_from_ui")

    with allure.step("Verify Order ID, Amount, Items with DB"):
        db         = DatabaseUtils()
        all_failed = []

        for ui_order in ui_orders:
            order_id = ui_order["order_id"]
            print(f"\n{'='*50}")
            print(f"🔍 Order ID : {order_id}")
            print(f"   UI Amount: {ui_order['amount']}")
            print(f"   UI Items : {ui_order['no_of_items']}")

            db_order = mysale.get_order_from_db(db, order_id)

            if not db_order:
                all_failed.append(f"❌ Order {order_id} — DB mein nahi mila")
                continue

            # ── Amount verify ──
            ui_amt = round(float(str(ui_order["amount"]).replace(",", "") or 0))
            db_amt = round(float(db_order.get("total_amount") or 0))
            if ui_amt == db_amt:
                print(f"  ✅ Amount match     : UI={ui_amt} | DB={db_amt}")
            else:
                all_failed.append(
                    f"❌ {order_id} Amount → UI: {ui_amt} | DB: {db_amt}"
                )

            # Items check
            ui_items = int(ui_order["no_of_items"] or 0)
            db_items = int(float(db_order.get("no_of_items") or 0))  # 2.00 → 2
            if ui_items == db_items:
                print(f"  ✅ Items match      : UI={ui_items} | DB={db_items}")
            else:
                all_failed.append(
                    f"❌ {order_id} Items → UI: {ui_items} | DB: {db_items}"
                )

        # ── Final result ──
        print(f"\n{'='*50}")
        if all_failed:
            pytest.fail("\n".join(all_failed))
        else:
            print(f"✅ Saare {len(ui_orders)} orders verified — Order ID, Amount, Items sab match!")
            take_screenshot(driver, "verify_passed")


    with allure.step("Click first row edit"):
        mysale.click_first_row_edit()
        time.sleep(5)
        take_screenshot(driver, "edit_clicked")


    with allure.step("click calculate"):
        mysale.click_calculate()
        take_screenshot(driver, "calculate")

    with allure.step("Save changes"):
        mysale.click_save()
        take_screenshot(driver, "saved")

    with allure.step("Update sale"):
        mysale.click_update_sale()
        take_screenshot(driver, "updated")

    with allure.step("Confirm order"):
        mysale.confirm_order()
        take_screenshot(driver, "confirmed")

    with allure.step("click print"):
        mysale.click_print()
        take_screenshot(driver, "print")

    with allure.step("verify amount and screenshot"):
        mysale.verify_amount_and_screenshot()
        take_screenshot(driver, "verify amount and screenshot")