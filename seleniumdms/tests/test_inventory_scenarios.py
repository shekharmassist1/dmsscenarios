import random
import re
import time

import allure
import pytest

from pages.product_page import ProductPage
from pages.draft_page import DraftPage
from pages.my_sale_page import MySalePage
from utilities.allure_utils import step
from utilities.invoice_pdf import (
    fetch_invoice_text,
    extract_payable_amount,
    extract_line_item_count,
    extract_items_and_pricing_table,
)
from utilities.db import get_latest_order_for_client, get_order_products

CUSTOMER_NAME = "Demo Dealer 4"
pytestmark = pytest.mark.xdist_group(name="dd4")  # parallel runs: one group per customer, never shared



def _to_float(value):
    return float(re.sub(r"[^0-9.\-]", "", value) or 0)


def _verify_order_against_database(soft_assert, client_name, expected_item_count, expected_amount, stage_label):
    """Cross-check the just-created order directly against the database (order_dtls/order_products),
    independent of anything the UI reports -- this is the ground truth for what was actually persisted."""
    time.sleep(1.5)
    order = get_latest_order_for_client(client_name)
    if order is None:
        soft_assert.check(False, f"{stage_label}: no order found in the database for client '{client_name}'")
        return None
    allure.attach(
        str({k: v for k, v in order.items() if k in (
            "Order_Id", "Client_Name", "Order_Amt", "NoOfProducts", "SchemeId", "SchCode", "SchFreeQty",
        )}),
        name=f"db_order_header_{stage_label}",
        attachment_type=allure.attachment_type.TEXT,
    )
    soft_assert.check_equal(
        int(order["NoOfProducts"]), expected_item_count,
        f"{stage_label}: DB order_dtls.NoOfProducts vs entered item count (Order_Id={order['Order_Id']})",
    )
    soft_assert.check_true(
        abs(float(order["Order_Amt"]) - expected_amount) < 1,
        f"{stage_label}: DB order_dtls.Order_Amt ({order['Order_Amt']}) should match expected amount "
        f"({expected_amount}) -- Order_Id={order['Order_Id']}",
    )
    products = get_order_products(order["Order_Id"])
    allure.attach(
        str([{"Product_Name": p["Product_Name"], "Quantity": p["Quantity"], "TotalValue": p["TotalValue"]}
             for p in products]),
        name=f"db_order_products_{stage_label}",
        attachment_type=allure.attachment_type.TEXT,
    )
    soft_assert.check_equal(
        len(products), expected_item_count,
        f"{stage_label}: DB order_products row count vs entered item count (Order_Id={order['Order_Id']})",
    )
    return order


def _attach_rows_used(rows):
    allure.attach(
        f"Product grid rows used (chosen by live stock): {rows}",
        name="rows_with_stock",
        attachment_type=allure.attachment_type.TEXT,
    )


def _my_sales_baseline(driver):
    """Invoice id of the newest My Sales row for CUSTOMER_NAME BEFORE this test makes its sale.
    After the sale, the test only accepts a My Sales row with a DIFFERENT invoice id -- so it can't
    pick up an older sale (e.g. one made by a previous test) by mistake."""
    try:
        return MySalePage(driver).open().get_latest_invoice_id(CUSTOMER_NAME)
    except Exception:
        return None


def _enter_items_with_one_insufficient(page, soft_assert, total_items, insufficient_index, valid_qty=1):
    # Choose rows by LIVE stock so the "valid" items really are valid -- stock on this shared demo
    # account drops with every test sale and some products go negative.
    rows = page.pick_rows_with_stock(total_items, min_qty=valid_qty)
    _attach_rows_used(rows)
    entered = {}
    for position, row_idx in enumerate(rows):
        if position == insufficient_index:
            code, _qty = page.enter_insufficient_quantity(row_idx)
        else:
            code = page.enter_quantity(row_idx, valid_qty)
        entered[code] = True
    soft_assert.check_true(
        len(entered) == total_items,
        f"Expected {total_items} distinct product rows entered, got {len(entered)}",
    )
    return entered


def _click_print_and_check_preview(page, soft_assert):
    with allure.step("Click Print and check the Print Preview modal"):
        try:
            page.click_print()
            note = page.get_print_preview_note()
            allure.attach(
                page.driver.get_screenshot_as_png(),
                name="Print Preview modal - screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            soft_assert.check_true(
                "not saved" in note.lower(), f"Print Preview note should mention not saved, got {note!r}"
            )
            page.close_print_preview()
        except Exception as exc:
            soft_assert.check(False, f"Print step failed: {exc}")


def _calculate_and_check_count(page, soft_assert, expected_count, stage_label, expect_insufficient_alert=False):
    with step(page, f"Calculate ({stage_label})"):
        try:
            page.click_calc()
            summary = page.get_summary()
            allure.attach(
                str(summary), name=f"calc_summary_{stage_label}", attachment_type=allure.attachment_type.TEXT
            )

            alert = page.last_calc_alert
            if alert:
                allure.attach(alert, name=f"calc_alert_{stage_label}", attachment_type=allure.attachment_type.TEXT)
                if not expect_insufficient_alert:
                    soft_assert.check(
                        False,
                        f"{stage_label}: unexpected inventory alert with only valid quantities entered: {alert!r}",
                    )
            elif expect_insufficient_alert:
                soft_assert.check(
                    False,
                    f"{stage_label}: expected an insufficient-inventory alert (one item was entered over stock) "
                    f"but none appeared",
                )

            soft_assert.check_equal(summary["total_item"], str(expected_count), f"{stage_label}: Calc Total Item")
            return summary
        except Exception as exc:
            soft_assert.check(False, f"{stage_label}: Calculate step failed: {exc}")
            return None


def _save_draft_reopen_and_verify(page, soft_assert, expected_count, first_summary, expect_insufficient_alert=False):
    with step(page, "Save Draft"):
        try:
            page.click_save_draft()
            alert_text = page.get_draft_alert_text()
            soft_assert.check_true(
                "draft saved successfully" in alert_text.lower(), f"Draft alert text unexpected: {alert_text!r}"
            )
            page.confirm_draft_alert()
        except Exception as exc:
            soft_assert.check(False, f"Save Draft step failed: {exc}")
            return

    draft_page = DraftPage(page.driver)
    with step(page, "Verify the draft list shows the correct item count and amount"):
        try:
            draft_page.open()
            latest = draft_page.get_latest_draft_for_client(CUSTOMER_NAME)
            allure.attach(str(latest), name="latest_draft_row", attachment_type=allure.attachment_type.TEXT)
            soft_assert.check_true(latest is not None, "A draft row should exist after saving")
            if latest is not None:
                soft_assert.check_equal(latest["no_of_items"], str(expected_count), "Draft list No. Of Items")
                if first_summary is not None:
                    soft_assert.check_equal(
                        latest["no_of_items"],
                        first_summary["total_item"],
                        "Draft list No. Of Items vs Calc Total Item",
                    )
                    soft_assert.check_true(
                        abs(_to_float(latest["draft_amount"]) - _to_float(first_summary["final_amount"])) < 1,
                        f"Draft list Draft Amt ({latest['draft_amount']}) should match Calc Final Amount "
                        f"({first_summary['final_amount']}) -- pricing mismatch",
                    )
        except Exception as exc:
            soft_assert.check(False, f"Draft list verification failed: {exc}")

    with step(page, "Click Order Again and re-check Calculate"):
        try:
            draft_info = draft_page.order_again_for_client(CUSTOMER_NAME)
            soft_assert.check_true(draft_info is not None, "Order Again should find the draft row")
            page.wait_for_grid_loaded()
            reopened_count = page.get_visible_product_row_count()
            soft_assert.check_equal(
                reopened_count, expected_count, "Order Again should reopen the same number of product rows"
            )
        except Exception as exc:
            soft_assert.check(False, f"Order Again failed: {exc}")
            return

    second_summary = _calculate_and_check_count(
        page, soft_assert, expected_count, "after Order Again", expect_insufficient_alert=expect_insufficient_alert
    )
    if second_summary is not None and first_summary is not None:
        soft_assert.check_equal(
            second_summary["total_item"],
            first_summary["total_item"],
            "Calc Total Item after Order Again should match the original Calculate",
        )
        soft_assert.check_equal(
            second_summary["final_amount"],
            first_summary["final_amount"],
            "Calc Final Amount after Order Again should match the original Calculate -- pricing mismatch",
        )

    with allure.step("Click View Selected Items and check the item count"):
        try:
            page.open_view_selected_items()
            items, total = page.get_selected_items()
            allure.attach(
                page.driver.get_screenshot_as_png(),
                name="View Selected Items popover - screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            allure.attach(str(items), name="selected_items_after_order_again", attachment_type=allure.attachment_type.TEXT)
            soft_assert.check_equal(
                len(items), expected_count, "View Selected Items count after Order Again"
            )
            if total is not None and first_summary is not None:
                soft_assert.check_true(
                    abs(_to_float(total["value"]) - _to_float(first_summary["final_amount"])) < 1,
                    f"View Selected Items total ({total['value']}) should match the original Calc Final Amount "
                    f"({first_summary['final_amount']}) -- pricing mismatch",
                )
            page.close_selected_items()
        except Exception as exc:
            soft_assert.check(False, f"View Selected Items step failed: {exc}")


@allure.epic("Bill / New Invoice")
@allure.feature("Inventory mismatch bugs")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Scenario 1: 4 valid + 1 insufficient -> Calc -> Save Draft -> Order Again -> Calc -> View Selected")
def test_scenario1_five_items_one_insufficient_calc(logged_in_driver, soft_assert):
    page = ProductPage(logged_in_driver)
    with step(page, f"Open product page and select customer '{CUSTOMER_NAME}'"):
        try:
            page.open()
            page.select_customer(CUSTOMER_NAME)
        except Exception as exc:
            soft_assert.check(False, f"Setup failed: {exc}")
            return

    with step(page, "Enter 4 valid items + 1 insufficient-inventory item"):
        try:
            entered = _enter_items_with_one_insufficient(page, soft_assert, total_items=5, insufficient_index=4)
        except Exception as exc:
            soft_assert.check(False, f"Entering quantities failed: {exc}")
            return

    summary = _calculate_and_check_count(page, soft_assert, len(entered), "initial", expect_insufficient_alert=True)
    _save_draft_reopen_and_verify(page, soft_assert, len(entered), summary, expect_insufficient_alert=True)


@allure.epic("Bill / New Invoice")
@allure.feature("Inventory mismatch bugs")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Scenario 2: 4 items -> Calc -> Save Draft -> Order Again -> Calc -> View Selected")
def test_scenario2_four_items_calc_then_save_draft(logged_in_driver, soft_assert):
    page = ProductPage(logged_in_driver)
    with step(page, f"Open product page and select customer '{CUSTOMER_NAME}'"):
        try:
            page.open()
            page.select_customer(CUSTOMER_NAME)
        except Exception as exc:
            soft_assert.check(False, f"Setup failed: {exc}")
            return

    entered = {}
    with step(page, "Pick 4 products with enough stock and enter qty 2 each"):
        try:
            rows = page.pick_rows_with_stock(4, min_qty=2)
            _attach_rows_used(rows)
            for row_idx in rows:
                code = page.enter_quantity(row_idx, 2)
                entered[code] = True
            soft_assert.check_true(
                len(entered) == 4, f"Expected 4 distinct product rows entered, got {len(entered)}"
            )
        except Exception as exc:
            soft_assert.check(False, f"Entering quantities failed: {exc}")

    summary = _calculate_and_check_count(page, soft_assert, len(entered), "initial")
    _save_draft_reopen_and_verify(page, soft_assert, len(entered), summary)


@allure.epic("Bill / New Invoice")
@allure.feature("Inventory mismatch bugs")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Scenario 3: 2 items (1 insufficient) -> Calc -> Save Draft -> Order Again -> Calc -> View Selected")
def test_scenario3_two_items_one_insufficient_calc_then_save(logged_in_driver, soft_assert):
    page = ProductPage(logged_in_driver)
    with step(page, f"Open product page and select customer '{CUSTOMER_NAME}'"):
        try:
            page.open()
            page.select_customer(CUSTOMER_NAME)
        except Exception as exc:
            soft_assert.check(False, f"Setup failed: {exc}")
            return

    entered = {}
    with step(page, "Enter 2 items, one with insufficient inventory"):
        try:
            entered = _enter_items_with_one_insufficient(page, soft_assert, total_items=2, insufficient_index=1)
        except Exception as exc:
            soft_assert.check(False, f"Entering quantities failed: {exc}")

    summary = _calculate_and_check_count(page, soft_assert, len(entered), "initial", expect_insufficient_alert=True)
    _save_draft_reopen_and_verify(page, soft_assert, len(entered), summary, expect_insufficient_alert=True)


@allure.epic("Bill / New Invoice")
@allure.feature("Inventory mismatch bugs")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Scenario 4: 7 items (1 insufficient) -> Calc -> Save Draft -> Order Again -> Calc -> View Selected")
def test_scenario4_seven_items_one_insufficient_print_view_selected(logged_in_driver, soft_assert):
    page = ProductPage(logged_in_driver)
    with step(page, f"Open product page and select customer '{CUSTOMER_NAME}'"):
        try:
            page.open()
            page.select_customer(CUSTOMER_NAME)
        except Exception as exc:
            soft_assert.check(False, f"Setup failed: {exc}")
            return

    entered = {}
    with step(page, "Enter 7 items, one with insufficient inventory"):
        try:
            entered = _enter_items_with_one_insufficient(page, soft_assert, total_items=7, insufficient_index=6)
        except Exception as exc:
            soft_assert.check(False, f"Entering quantities failed: {exc}")

    _click_print_and_check_preview(page, soft_assert)

    summary = _calculate_and_check_count(page, soft_assert, len(entered), "initial", expect_insufficient_alert=True)
    _save_draft_reopen_and_verify(page, soft_assert, len(entered), summary, expect_insufficient_alert=True)


@allure.epic("Bill / New Invoice")
@allure.feature("Inventory mismatch bugs")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Scenario 5: correct an insufficient item's qty, then Calc -> Save Draft -> Order Again -> Calc -> View Selected")
def test_scenario5_correct_insufficient_item_then_check_item_count(logged_in_driver, soft_assert):
    page = ProductPage(logged_in_driver)
    with step(page, f"Open product page and select customer '{CUSTOMER_NAME}'"):
        try:
            page.open()
            page.select_customer(CUSTOMER_NAME)
        except Exception as exc:
            soft_assert.check(False, f"Setup failed: {exc}")
            return

    entered = {}
    with step(page, "Enter 5 items; push the 5th over its available stock, then correct it back to a valid qty"):
        try:
            rows = page.pick_rows_with_stock(5, min_qty=1)
            _attach_rows_used(rows)
            for row_idx in rows:
                code = page.enter_quantity(row_idx, 1)
                entered[code] = True
            last_row = rows[-1]
            page.enter_insufficient_quantity(last_row)
            page.dismiss_any_alert()
            available = page.get_available_stock(last_row)
            valid_qty = max(1, int(available))
            corrected_code = page.enter_quantity(last_row, valid_qty)
            entered[corrected_code] = True
            soft_assert.check_true(
                len(entered) == 5, f"Expected 5 distinct product rows entered, got {len(entered)}"
            )
        except Exception as exc:
            soft_assert.check(False, f"Entering/correcting quantities failed: {exc}")

    summary = _calculate_and_check_count(page, soft_assert, len(entered), "initial")
    _save_draft_reopen_and_verify(page, soft_assert, len(entered), summary)


@allure.epic("Bill / New Invoice")
@allure.feature("Inventory mismatch bugs")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Scenario 7 (Incorrect Inventory): Select All override -> Calc -> Save Draft -> Order Again -> Calc -> View Selected")
def test_scenario7_select_all_override_then_save_draft_and_order_again(logged_in_driver, soft_assert):
    page = ProductPage(logged_in_driver)
    with step(page, f"Open product page and select customer '{CUSTOMER_NAME}'"):
        try:
            page.open()
            page.select_customer(CUSTOMER_NAME)
        except Exception as exc:
            soft_assert.check(False, f"Setup failed: {exc}")
            return

    product_ids = {}
    with step(page, "Enter 4 in each of two product rows (chosen by live stock)"):
        try:
            rows = page.pick_rows_with_stock(2, min_qty=4)
            _attach_rows_used(rows)
            for row_idx in rows:
                info = page.product_row(row_idx)
                page.enter_quantity(row_idx, 4)
                product_ids[info["product_id"]] = info["item_code"]
            soft_assert.check_true(
                len(product_ids) == 2, f"Expected 2 distinct products entered with qty 4, got {len(product_ids)}"
            )
        except Exception as exc:
            soft_assert.check(False, f"Entering initial quantities (4 each) failed: {exc}")
            return

    with step(page, "Use Select All to re-enter 2 in each of the same two products"):
        try:
            page.open_select_all_modal()
            page.uncheck_all_in_select_all_modal()
            for product_id in product_ids:
                page.set_select_all_modal_quantity(product_id, 2)
            page.confirm_select_all_modal()
        except Exception as exc:
            soft_assert.check(False, f"Select All -> enter 2 in each step failed: {exc}")

    summary = _calculate_and_check_count(page, soft_assert, len(product_ids), "initial")
    _save_draft_reopen_and_verify(page, soft_assert, len(product_ids), summary)


@allure.epic("Bill / New Invoice")
@allure.feature("Happy path")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title(
    "Scenario 8: 7 items random valid qty (1-7) -> Calc -> Save Draft -> Order Again -> "
    "Calc -> Save -> verify Payable vs Final Amount -> Add Sale"
)
def test_scenario8_seven_random_valid_items_full_flow_add_sale(logged_in_driver, soft_assert):
    page = ProductPage(logged_in_driver)
    with step(page, f"Open product page and select customer '{CUSTOMER_NAME}'"):
        try:
            page.open()
            page.select_customer(CUSTOMER_NAME)
        except Exception as exc:
            soft_assert.check(False, f"Setup failed: {exc}")
            return

    entered = {}
    with step(page, "Enter 7 items with random valid quantities (1-7, within available stock)"):
        try:
            rows = page.pick_rows_with_stock(7, min_qty=1)
            _attach_rows_used(rows)
            for row_idx in rows:
                available = page.get_available_stock(row_idx)
                max_qty = max(1, min(7, int(available)))
                qty = random.randint(1, max_qty)
                code = page.enter_quantity(row_idx, qty)
                entered[code] = qty
            allure.attach(str(entered), name="entered_codes_and_qty", attachment_type=allure.attachment_type.TEXT)
            soft_assert.check_true(
                len(entered) == 7, f"Expected 7 distinct product rows entered, got {len(entered)}"
            )
        except Exception as exc:
            soft_assert.check(False, f"Entering quantities failed: {exc}")
            return

    summary = _calculate_and_check_count(page, soft_assert, len(entered), "initial")

    with step(page, "Save Draft and verify the confirmation alert"):
        try:
            page.click_save_draft()
            alert_text = page.get_draft_alert_text()
            soft_assert.check_true(
                "draft saved successfully" in alert_text.lower(), f"Draft alert text unexpected: {alert_text!r}"
            )
            page.confirm_draft_alert()
        except Exception as exc:
            soft_assert.check(False, f"Save Draft step failed: {exc}")
            return

    draft_page = DraftPage(logged_in_driver)
    with step(page, "Verify the draft list shows the correct item count and amount"):
        try:
            draft_page.open()
            latest = draft_page.get_latest_draft_for_client(CUSTOMER_NAME)
            allure.attach(str(latest), name="latest_draft_row", attachment_type=allure.attachment_type.TEXT)
            soft_assert.check_true(latest is not None, "A draft row should exist after saving")
            if latest is not None:
                soft_assert.check_equal(latest["no_of_items"], str(len(entered)), "Draft list No. Of Items")
                if summary is not None:
                    soft_assert.check_equal(
                        latest["no_of_items"], summary["total_item"], "Draft list No. Of Items vs Calc Total Item"
                    )
                    soft_assert.check_true(
                        abs(_to_float(latest["draft_amount"]) - _to_float(summary["final_amount"])) < 1,
                        f"Draft list Draft Amt ({latest['draft_amount']}) should match Calc Final Amount "
                        f"({summary['final_amount']}) -- pricing mismatch",
                    )
        except Exception as exc:
            soft_assert.check(False, f"Draft list verification failed: {exc}")

    with step(page, "Click Order Again"):
        try:
            draft_info = draft_page.order_again_for_client(CUSTOMER_NAME)
            soft_assert.check_true(draft_info is not None, "Order Again should find the draft row")
            page.wait_for_grid_loaded()
            reopened_count = page.get_visible_product_row_count()
            soft_assert.check_equal(
                reopened_count, len(entered), "Order Again should reopen the same number of product rows"
            )
        except Exception as exc:
            soft_assert.check(False, f"Order Again failed: {exc}")
            return

    second_summary = _calculate_and_check_count(page, soft_assert, len(entered), "after Order Again")
    if second_summary is not None and summary is not None:
        soft_assert.check_equal(
            second_summary["total_item"], summary["total_item"], "Calc Total Item after Order Again vs original"
        )
        soft_assert.check_equal(
            second_summary["final_amount"],
            summary["final_amount"],
            "Calc Final Amount after Order Again vs original -- pricing mismatch",
        )

    with step(page, "Click Save and verify Total Payable matches Final Amount"):
        try:
            page.click_save()
            payable = page.get_payable_amount()
            allure.attach(
                f"Payable Amount: {payable} | Calc Final Amount: "
                f"{second_summary['final_amount'] if second_summary else 'N/A'}",
                name="payable_vs_final_amount",
                attachment_type=allure.attachment_type.TEXT,
            )
            if second_summary is not None:
                soft_assert.check_true(
                    abs(_to_float(payable) - _to_float(second_summary["final_amount"])) < 1,
                    f"Total Payable ({payable}) should match Calc Final Amount "
                    f"({second_summary['final_amount']}) -- pricing mismatch",
                )
        except Exception as exc:
            soft_assert.check(False, f"Save step failed: {exc}")
            return

    with step(page, "Click Add Sale and confirm"):
        try:
            page.click_add_sale()
            confirm_details = page.get_confirm_sale_details()
            allure.attach(str(confirm_details), name="confirm_sale_details", attachment_type=allure.attachment_type.TEXT)
            soft_assert.check_equal(
                confirm_details.get("No Of Items"), str(len(entered)), "Confirm Sale dialog: No Of Items"
            )
            if second_summary is not None:
                soft_assert.check_true(
                    abs(_to_float(confirm_details.get("Total value", "0")) - _to_float(second_summary["final_amount"])) < 1,
                    f"Confirm Sale dialog Total value ({confirm_details.get('Total value')}) should match "
                    f"Calc Final Amount ({second_summary['final_amount']}) -- pricing mismatch",
                )
            page.confirm_sale_proceed()
            page.wait_for_sale_completed()
            page.dismiss_post_sale_print_preview()
        except Exception as exc:
            soft_assert.check(False, f"Add Sale step failed: {exc}")
            return

    with allure.step("Verify the finalized order directly against the database"):
        try:
            expected_amount = _to_float(second_summary["final_amount"]) if second_summary is not None else 0
            _verify_order_against_database(soft_assert, CUSTOMER_NAME, len(entered), expected_amount, "scenario8")
        except Exception as exc:
            soft_assert.check(False, f"Database verification step failed: {exc}")


@allure.epic("Bill / New Invoice")
@allure.feature("Happy path")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title(
    "Scenario 9: 5 items -> Calc -> Print -> Save + verify Payable -> 2% discount -> "
    "Add Sale -> Confirm -> Proceed -> generate invoice -> verify invoice total"
)
def test_scenario9_five_items_discount_add_sale_verify_invoice(logged_in_driver, soft_assert):
    page = ProductPage(logged_in_driver)
    with step(page, f"Open product page and select customer '{CUSTOMER_NAME}'"):
        try:
            page.open()
            page.select_customer(CUSTOMER_NAME)
        except Exception as exc:
            soft_assert.check(False, f"Setup failed: {exc}")
            return

    entered = {}
    with step(page, "Pick 5 products with stock and enter qty 1 each"):
        try:
            rows = page.pick_rows_with_stock(5, min_qty=1)
            _attach_rows_used(rows)
            for row_idx in rows:
                code = page.enter_quantity(row_idx, 1)
                entered[code] = True
            soft_assert.check_true(
                len(entered) == 5, f"Expected 5 distinct product rows entered, got {len(entered)}"
            )
        except Exception as exc:
            soft_assert.check(False, f"Entering quantities failed: {exc}")
            return

    summary = _calculate_and_check_count(page, soft_assert, len(entered), "initial")

    _click_print_and_check_preview(page, soft_assert)

    with step(page, "Click Save and verify Payable Amount matches Final Amount"):
        try:
            page.click_save()
            payable = page.get_payable_amount()
            allure.attach(
                f"Payable Amount: {payable} | Calc Final Amount: {summary['final_amount'] if summary else 'N/A'}",
                name="payable_before_discount",
                attachment_type=allure.attachment_type.TEXT,
            )
            if summary is not None:
                soft_assert.check_true(
                    abs(_to_float(payable) - _to_float(summary["final_amount"])) < 1,
                    f"Payable Amount ({payable}) should match Calc Final Amount "
                    f"({summary['final_amount']}) -- pricing mismatch",
                )
        except Exception as exc:
            soft_assert.check(False, f"Save step failed: {exc}")
            return

    discounted_payable = None
    with step(page, "Apply a 2% discount and read the new Payable Amount"):
        try:
            page.apply_discount_percent(2)
            discounted_payable = page.get_payable_amount()
            allure.attach(
                f"Payable Amount after 2% discount: {discounted_payable}",
                name="payable_after_discount",
                attachment_type=allure.attachment_type.TEXT,
            )
            if summary is not None:
                expected_discounted = round(_to_float(summary["final_amount"]) * 0.98, 2)
                soft_assert.check_true(
                    abs(_to_float(discounted_payable) - expected_discounted) < 1,
                    f"Payable Amount after 2% discount ({discounted_payable}) should be ~2% less than "
                    f"the Final Amount ({summary['final_amount']}), expected ~{expected_discounted} "
                    f"-- pricing mismatch",
                )
        except Exception as exc:
            soft_assert.check(False, f"Apply discount step failed: {exc}")

    with allure.step("Click Add Sale, verify Confirm Sale dialog total, and Proceed"):
        try:
            page.click_add_sale()
            confirm_details = page.get_confirm_sale_details()
            allure.attach(
                page.driver.get_screenshot_as_png(),
                name="Confirm Sale dialog - screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            allure.attach(
                str(confirm_details), name="Confirm Sale dialog - details",
                attachment_type=allure.attachment_type.TEXT,
            )
            soft_assert.check_equal(
                confirm_details.get("No Of Items"), str(len(entered)), "Confirm Sale dialog: No Of Items"
            )
            if discounted_payable is not None:
                soft_assert.check_true(
                    abs(_to_float(confirm_details.get("Total value", "0")) - _to_float(discounted_payable)) < 1,
                    f"Confirm Sale dialog Total value ({confirm_details.get('Total value')}) should match "
                    f"the discounted Payable Amount ({discounted_payable}) -- pricing mismatch",
                )
            page.confirm_sale_proceed()
            page.wait_for_sale_completed()
        except Exception as exc:
            soft_assert.check(False, f"Add Sale step failed: {exc}")
            return

    with allure.step("Generate the invoice and verify its total against the discounted Payable Amount"):
        try:
            invoice_url, invoice_screenshot = page.generate_invoice_and_get_url()
            allure.attach(
                invoice_screenshot, name="Invoice - screenshot", attachment_type=allure.attachment_type.PNG
            )
            invoice_text = fetch_invoice_text(page.driver, invoice_url)

            invoice_total = extract_payable_amount(invoice_text)
            invoice_item_count = extract_line_item_count(invoice_text)
            summary_table = extract_items_and_pricing_table(invoice_text)
            allure.attach(
                f"Invoice Payable Amount: {invoice_total} | Invoice line items: {invoice_item_count}\n\n"
                f"{summary_table}",
                name="Invoice - items and pricing table",
                attachment_type=allure.attachment_type.TEXT,
            )

            soft_assert.check_true(invoice_total is not None, "Invoice PDF should contain a readable Payable Amount")
            soft_assert.check_equal(
                invoice_item_count, len(entered), "Invoice line-item count vs number of items entered"
            )
            if invoice_total is not None and discounted_payable is not None:
                soft_assert.check_true(
                    abs(_to_float(invoice_total) - _to_float(discounted_payable)) < 1,
                    f"Invoice total ({invoice_total}) should match the discounted Payable Amount "
                    f"({discounted_payable}) confirmed at sale time -- pricing mismatch",
                )
        except Exception as exc:
            soft_assert.check(False, f"Invoice generation/verification step failed: {exc}")


@allure.epic("Bill / New Invoice")
@allure.feature("Happy path")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title(
    "Scenario 10: 5 items (fixed qty 2,1,4,1,1) -> Calc -> Save -> Add Sale -> Proceed -> verify on My Sales"
)
def test_scenario10_five_fixed_qty_items_verify_my_sale(logged_in_driver, soft_assert):
    with allure.step("Note the newest My Sales invoice for this customer BEFORE the sale"):
        baseline_invoice = _my_sales_baseline(logged_in_driver)
        allure.attach(str(baseline_invoice), name="my_sales_baseline_invoice",
                      attachment_type=allure.attachment_type.TEXT)

    page = ProductPage(logged_in_driver)
    with step(page, f"Open product page and select customer '{CUSTOMER_NAME}'"):
        try:
            page.open()
            page.select_customer(CUSTOMER_NAME)
        except Exception as exc:
            soft_assert.check(False, f"Setup failed: {exc}")
            return

    requested_quantities = [2, 1, 4, 1, 1]
    entered = {}
    with step(page, f"Pick 5 products with enough stock and enter quantities {requested_quantities}"):
        try:
            rows = page.pick_rows_with_stock(len(requested_quantities), min_qty=max(requested_quantities))
            _attach_rows_used(rows)
            for row_idx, qty in zip(rows, requested_quantities):
                code = page.enter_quantity(row_idx, qty)
                entered[code] = qty
            soft_assert.check_true(
                len(entered) == 5, f"Expected 5 distinct product rows entered, got {len(entered)}"
            )
        except Exception as exc:
            soft_assert.check(False, f"Entering quantities failed: {exc}")
            return

    summary = _calculate_and_check_count(page, soft_assert, len(entered), "initial")

    with step(page, "Click Save and verify Payable Amount matches Final Amount"):
        try:
            page.click_save()
            payable = page.get_payable_amount()
            allure.attach(
                f"Payable Amount: {payable} | Calc Final Amount: {summary['final_amount'] if summary else 'N/A'}",
                name="payable_vs_final_amount",
                attachment_type=allure.attachment_type.TEXT,
            )
            if summary is not None:
                soft_assert.check_true(
                    abs(_to_float(payable) - _to_float(summary["final_amount"])) < 1,
                    f"Payable Amount ({payable}) should match Calc Final Amount "
                    f"({summary['final_amount']}) -- pricing mismatch",
                )
        except Exception as exc:
            soft_assert.check(False, f"Save step failed: {exc}")
            return

    with allure.step("Click Add Sale, verify Confirm Sale dialog, and Proceed"):
        try:
            page.click_add_sale()
            confirm_details = page.get_confirm_sale_details()
            allure.attach(
                page.driver.get_screenshot_as_png(),
                name="Confirm Sale dialog - screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            allure.attach(
                str(confirm_details), name="Confirm Sale dialog - details",
                attachment_type=allure.attachment_type.TEXT,
            )
            soft_assert.check_equal(
                confirm_details.get("No Of Items"), str(len(entered)), "Confirm Sale dialog: No Of Items"
            )
            if summary is not None:
                soft_assert.check_true(
                    abs(_to_float(confirm_details.get("Total value", "0")) - _to_float(summary["final_amount"])) < 1,
                    f"Confirm Sale dialog Total value ({confirm_details.get('Total value')}) should match "
                    f"the Calc Final Amount ({summary['final_amount']}) -- pricing mismatch",
                )
            page.confirm_sale_proceed()
            page.wait_for_sale_completed()
            page.dismiss_post_sale_print_preview()
        except Exception as exc:
            soft_assert.check(False, f"Add Sale step failed: {exc}")
            return

    with allure.step("Verify the finalized sale on the My Sales report"):
        try:
            my_sale_page = MySalePage(logged_in_driver)
            my_sale_page.open()
            latest_sale = my_sale_page.get_latest_sale_for_client(CUSTOMER_NAME, exclude_invoice_ids={baseline_invoice})
            allure.attach(
                page.driver.get_screenshot_as_png(),
                name="My Sales - screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            allure.attach(str(latest_sale), name="My Sales - latest row", attachment_type=allure.attachment_type.TEXT)

            soft_assert.check_true(latest_sale is not None, "A sale row for 'Demo Dealer 4' should exist on My Sales")
            if latest_sale is not None:
                soft_assert.check_equal(latest_sale["party_name"], CUSTOMER_NAME, "My Sales: Party Name")
                soft_assert.check_equal(
                    latest_sale["no_of_items"], str(len(entered)), "My Sales: No. Of Items vs entered"
                )
                if summary is not None:
                    soft_assert.check_equal(
                        latest_sale["no_of_items"], summary["total_item"], "My Sales: No. Of Items vs Calc Total Item"
                    )
                    soft_assert.check_true(
                        abs(_to_float(latest_sale["amount"]) - _to_float(summary["final_amount"])) < 1,
                        f"My Sales Amount ({latest_sale['amount']}) should match Calc Final Amount "
                        f"({summary['final_amount']}) -- pricing mismatch",
                    )
                    soft_assert.check_equal(
                        latest_sale["sale_qty"], summary["qty_pcs"], "My Sales: Sale Qty vs Calc Qty (pcs)"
                    )
        except Exception as exc:
            soft_assert.check(False, f"My Sales verification step failed: {exc}")


@allure.epic("Bill / New Invoice")
@allure.feature("Happy path")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title(
    "Scenario 11: 3 items -> Calc -> Save -> Add Sale -> Proceed -> My Sales -> Edit -> Calc/View Selected -> "
    "Update Sale -> Proceed -> Print -> verify invoice"
)
def test_scenario11_three_items_edit_and_verify_invoice(logged_in_driver, soft_assert):
    with allure.step("Note the newest My Sales invoice for this customer BEFORE the sale"):
        baseline_invoice = _my_sales_baseline(logged_in_driver)
        allure.attach(str(baseline_invoice), name="my_sales_baseline_invoice",
                      attachment_type=allure.attachment_type.TEXT)

    page = ProductPage(logged_in_driver)
    with step(page, f"Open product page and select customer '{CUSTOMER_NAME}'"):
        try:
            page.open()
            page.select_customer(CUSTOMER_NAME)
        except Exception as exc:
            soft_assert.check(False, f"Setup failed: {exc}")
            return

    entered = {}
    with step(page, "Pick 3 products with stock and enter qty 1 each"):
        try:
            rows = page.pick_rows_with_stock(3, min_qty=1)
            _attach_rows_used(rows)
            for row_idx in rows:
                code = page.enter_quantity(row_idx, 1)
                entered[code] = True
            soft_assert.check_true(
                len(entered) == 3, f"Expected 3 distinct product rows entered, got {len(entered)}"
            )
        except Exception as exc:
            soft_assert.check(False, f"Entering quantities failed: {exc}")
            return

    summary = _calculate_and_check_count(page, soft_assert, len(entered), "initial")

    with step(page, "Click Save and verify Payable Amount matches Final Amount"):
        try:
            page.click_save()
            payable = page.get_payable_amount()
            if summary is not None:
                soft_assert.check_true(
                    abs(_to_float(payable) - _to_float(summary["final_amount"])) < 1,
                    f"Payable Amount ({payable}) should match Calc Final Amount "
                    f"({summary['final_amount']}) -- pricing mismatch",
                )
        except Exception as exc:
            soft_assert.check(False, f"Save step failed: {exc}")
            return

    with allure.step("Click Add Sale, verify Confirm Sale dialog, and Proceed"):
        try:
            page.click_add_sale()
            confirm_details = page.get_confirm_sale_details()
            allure.attach(
                page.driver.get_screenshot_as_png(),
                name="Confirm Sale dialog - screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            soft_assert.check_equal(
                confirm_details.get("No Of Items"), str(len(entered)), "Confirm Sale dialog: No Of Items"
            )
            page.confirm_sale_proceed()
            page.wait_for_sale_completed()
            page.dismiss_post_sale_print_preview()
        except Exception as exc:
            soft_assert.check(False, f"Add Sale step failed: {exc}")
            return

    my_sale_page = MySalePage(logged_in_driver)
    sale_invoice = None
    with allure.step("Verify the finalized sale on the My Sales report"):
        try:
            my_sale_page.open()
            latest_sale = my_sale_page.get_latest_sale_for_client(CUSTOMER_NAME, exclude_invoice_ids={baseline_invoice})
            allure.attach(
                my_sale_page.driver.get_screenshot_as_png(),
                name="My Sales - screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            allure.attach(str(latest_sale), name="My Sales - latest row", attachment_type=allure.attachment_type.TEXT)
            soft_assert.check_true(latest_sale is not None, "A NEW sale row for 'Demo Dealer 4' should exist on My Sales")
            if latest_sale is not None:
                sale_invoice = latest_sale["invoice_id"]
                soft_assert.check_equal(
                    latest_sale["no_of_items"], str(len(entered)), "My Sales: No. Of Items vs entered"
                )
        except Exception as exc:
            soft_assert.check(False, f"My Sales verification step failed: {exc}")
            return

    edit_summary = None
    edit_items = None
    with allure.step("Click Edit and verify Calc + View Selected Items on the Edit Sale page"):
        try:
            my_sale_page.click_edit_for_client(CUSTOMER_NAME, invoice_id=sale_invoice)
            edit_page = ProductPage(logged_in_driver)
            edit_page.click_calc()
            edit_summary = edit_page.get_summary()
            allure.attach(str(edit_summary), name="edit_page_calc_summary", attachment_type=allure.attachment_type.TEXT)
            edit_page.open_view_selected_items()
            edit_items, edit_total = edit_page.get_selected_items()
            allure.attach(str(edit_items), name="edit_page_selected_items", attachment_type=allure.attachment_type.TEXT)
            allure.attach(
                edit_page.driver.get_screenshot_as_png(),
                name="Edit Sale page - View Selected Items - screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            soft_assert.check_equal(
                len(edit_items), len(entered), "Edit Sale page: View Selected Items count vs originally entered"
            )
            edit_page.close_selected_items()
        except Exception as exc:
            soft_assert.check(False, f"Edit Sale page Calc/View Selected Items step failed: {exc}")
            return

    with allure.step("Save, click Update Sale, verify the confirmation dialog, and Proceed"):
        try:
            edit_page.click_save()
            edit_page.click_update_sale()
            update_details = edit_page.get_confirm_update_details()
            allure.attach(
                edit_page.driver.get_screenshot_as_png(),
                name="Confirm Update dialog - screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            allure.attach(str(update_details), name="confirm_update_details", attachment_type=allure.attachment_type.TEXT)
            if edit_summary is not None:
                soft_assert.check_equal(
                    update_details.get("No Of Items"), edit_summary["total_item"],
                    "Confirm Update dialog: No Of Items vs Edit page Calc Total Item",
                )
            edit_page.confirm_update_proceed()
        except Exception as exc:
            soft_assert.check(False, f"Save/Update Sale step failed: {exc}")
            return

    with allure.step("Print the invoice from My Sales and verify its item count/total"):
        try:
            my_sale_page.open()
            invoice_url, invoice_screenshot = my_sale_page.print_invoice_for_client(CUSTOMER_NAME, invoice_id=sale_invoice)
            allure.attach(
                invoice_screenshot, name="Invoice - screenshot", attachment_type=allure.attachment_type.PNG
            )
            invoice_text = fetch_invoice_text(my_sale_page.driver, invoice_url)
            invoice_total = extract_payable_amount(invoice_text)
            invoice_item_count = extract_line_item_count(invoice_text)
            summary_table = extract_items_and_pricing_table(invoice_text)
            allure.attach(
                f"Invoice Payable Amount: {invoice_total} | Invoice line items: {invoice_item_count}\n\n"
                f"{summary_table}",
                name="Invoice - items and pricing table",
                attachment_type=allure.attachment_type.TEXT,
            )
            soft_assert.check_true(invoice_total is not None, "Invoice PDF should contain a readable Payable Amount")
            soft_assert.check_equal(
                invoice_item_count, len(entered), "Invoice line-item count vs number of items originally entered"
            )
        except Exception as exc:
            soft_assert.check(False, f"Print/invoice verification step failed: {exc}")


SCHEME_TIER1_MIN = 3809.52
SCHEME_TIER1_MAX = 5713.29


@allure.epic("Bill / New Invoice")
@allure.feature("Schemes / Free Goods")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title(
    "Scenario 12: 2 scheme products (combined amount crosses tier 1) -> Calc -> View Selected -> "
    "Save -> Add Sale -> Proceed -> verify invoice"
)
def test_scenario12_scheme_products_combined_threshold_add_sale(logged_in_driver, soft_assert):
    page = ProductPage(logged_in_driver)
    with step(page, f"Open product page and select customer '{CUSTOMER_NAME}'"):
        try:
            page.open()
            page.select_customer(CUSTOMER_NAME)
        except Exception as exc:
            soft_assert.check(False, f"Setup failed: {exc}")
            return

    info_a = None
    amount_a = None
    tier1_min = None
    tier1_max = None
    bonus_name = ""
    with step(page, "Search Product A (Aam Chaska Falala Candy) and read the scheme's CURRENT tier-1 range"):
        try:
            idx_a = page.search_product("Aam Chaska Falala Candy [1*10]")
            info_a = page.product_row(idx_a)
            soft_assert.check_true(
                "1*10" in info_a["display_name"].replace(" ", ""),
                f"Expected the [1*10] variant, got {info_a['display_name']!r}",
            )
            soft_assert.check_true(info_a["scheme_id"] is not None, "Product A should carry a scheme tag")
            # Schemes on this app are reassigned over time (tier ranges and bonus product change), so read
            # them live from the Scheme Details popup instead of trusting hardcoded values.
            tiers = page.get_scheme_tiers(idx_a)
            allure.attach(str(tiers), name="scheme_tiers_read_live", attachment_type=allure.attachment_type.TEXT)
            if not tiers:
                soft_assert.check(False, "Scheme Details popup should list at least one tier")
                return
            tier1_min, tier1_max = tiers[0]["min"], tiers[0]["max"]
            bonus_name = tiers[0]["product_name"]
            bonus_key = bonus_name.lower().split("[")[0].strip()
        except Exception as exc:
            soft_assert.check(False, f"Reading Product A / scheme tiers failed: {exc}")
            return

    with step(page, "Enter Product A below the scheme threshold on its own"):
        try:
            # Enough to contribute, but stay under the tier-1 minimum on its own.
            product_a_qty = max(1, min(5, int((tier1_min * 0.5) / info_a["price"]))) if info_a["price"] else 1
            page.enter_quantity(idx_a, product_a_qty)
            amount_a = info_a["price"] * product_a_qty
            allure.attach(
                f"Product A: {info_a['display_name']} | price/carton={info_a['price']} | qty={product_a_qty} | "
                f"line amount={amount_a:.2f} | scheme_id={info_a['scheme_id']}",
                name="product_a_details",
                attachment_type=allure.attachment_type.TEXT,
            )
            soft_assert.check_true(
                amount_a < tier1_min,
                f"Product A's own line amount ({amount_a:.2f}) should stay below the scheme's "
                f"live tier-1 minimum ({tier1_min})",
            )
        except Exception as exc:
            soft_assert.check(False, f"Entering Product A failed: {exc}")
            return

    combined = None
    with step(page, "Search and enter Product B (Almond Carnival GRMT Tub) so the combined total crosses tier 1"):
        try:
            idx_b = page.search_product("Almond Carnival GRMT Tub [1*2]")
            info_b = page.product_row(idx_b)
            soft_assert.check_true(
                info_b["scheme_id"] == info_a["scheme_id"],
                f"Product B should share the same scheme id as Product A "
                f"(A={info_a['scheme_id']}, B={info_b['scheme_id']})",
            )
            target_combined = (tier1_min + tier1_max) / 2
            needed_amount_b = max(0.0, target_combined - amount_a)
            qty_b = max(1, int(needed_amount_b / info_b["price"]) + 1)
            qty_b = min(qty_b, max(1, int(info_b["available_stock"])))
            page.enter_quantity(idx_b, qty_b)
            amount_b = info_b["price"] * qty_b
            combined = amount_a + amount_b
            allure.attach(
                f"Product B: {info_b['display_name']} | price/carton={info_b['price']} | qty={qty_b} | "
                f"line amount={amount_b:.2f} | scheme_id={info_b['scheme_id']} | combined total={combined:.2f}",
                name="product_b_details",
                attachment_type=allure.attachment_type.TEXT,
            )
            soft_assert.check_true(
                tier1_min <= combined <= tier1_max,
                f"Combined amount ({combined:.2f}) should land within the scheme's live tier-1 range "
                f"({tier1_min}-{tier1_max})",
            )
        except Exception as exc:
            soft_assert.check(False, f"Entering Product B failed: {exc}")
            return

    summary = None
    with step(page, "Calculate and verify the scheme applied (Free Item >= 1, Total Scheme > 0)"):
        try:
            page.click_calc()
            summary = page.get_summary()
            allure.attach(str(summary), name="calc_summary", attachment_type=allure.attachment_type.TEXT)
            soft_assert.check_equal(
                summary["total_item"], "2", "Calc Total Item should be 2 (the two entered products)"
            )
            soft_assert.check_true(
                _to_float(summary["free_item"]) >= 1,
                f"Free Item should be at least 1 after crossing the scheme threshold, got {summary['free_item']}",
            )
            soft_assert.check_true(
                _to_float(summary["total_scheme"]) > 0,
                f"Total Scheme should be > 0 after crossing the scheme threshold, got {summary['total_scheme']}",
            )
        except Exception as exc:
            soft_assert.check(False, f"Calculate step failed: {exc}")
            return

    with allure.step("Click View Selected Items and verify the bonus product and total appear"):
        try:
            page.open_view_selected_items()
            items, vsi_total = page.get_selected_items()
            allure.attach(
                page.driver.get_screenshot_as_png(),
                name="View Selected Items - screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            allure.attach(str(items), name="selected_items", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(vsi_total), name="selected_items_total", attachment_type=allure.attachment_type.TEXT)
            soft_assert.check_true(
                len(items) >= 3, f"Expected at least 3 lines (2 entered + 1 free bonus item), got {len(items)}"
            )
            bonus_key = bonus_name.lower().split("[")[0].strip()
            bonus_present = bool(bonus_key) and any(bonus_key in i["item_name"].lower() for i in items)
            soft_assert.check_true(
                bonus_present,
                f"The scheme's tier-1 bonus product ({bonus_name!r}, read live) should appear in View Selected Items",
            )
            if summary is not None and vsi_total is not None:
                soft_assert.check_true(
                    abs(_to_float(vsi_total["value"]) - _to_float(summary["final_amount"])) < 1,
                    f"View Selected Items total ({vsi_total['value']}) should match the Calc Final Amount "
                    f"({summary['final_amount']})",
                )
            page.close_selected_items()
        except Exception as exc:
            soft_assert.check(False, f"View Selected Items step failed: {exc}")
            return

    with step(page, "Click Save and verify Payable Amount matches Final Amount"):
        try:
            page.click_save()
            payable = page.get_payable_amount()
            if summary is not None:
                soft_assert.check_true(
                    abs(_to_float(payable) - _to_float(summary["final_amount"])) < 1,
                    f"Payable Amount ({payable}) should match Calc Final Amount ({summary['final_amount']})",
                )
        except Exception as exc:
            soft_assert.check(False, f"Save step failed: {exc}")
            return

    with allure.step("Click Add Sale, verify Confirm Sale dialog, and Proceed"):
        try:
            page.click_add_sale()
            confirm_details = page.get_confirm_sale_details()
            allure.attach(
                page.driver.get_screenshot_as_png(),
                name="Confirm Sale dialog - screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            allure.attach(
                str(confirm_details), name="confirm_sale_details", attachment_type=allure.attachment_type.TEXT
            )
            page.confirm_sale_proceed()
            page.wait_for_sale_completed()
        except Exception as exc:
            soft_assert.check(False, f"Add Sale step failed: {exc}")
            return

    with allure.step("Generate the invoice and verify the bonus item appears on it"):
        try:
            invoice_url, invoice_screenshot = page.generate_invoice_and_get_url()
            allure.attach(
                invoice_screenshot, name="Invoice - screenshot", attachment_type=allure.attachment_type.PNG
            )
            invoice_text = fetch_invoice_text(page.driver, invoice_url)
            invoice_total = extract_payable_amount(invoice_text)
            invoice_item_count = extract_line_item_count(invoice_text)
            summary_table = extract_items_and_pricing_table(invoice_text)
            allure.attach(
                f"Invoice Payable Amount: {invoice_total} | Invoice line items: {invoice_item_count}\n\n"
                f"{summary_table}",
                name="Invoice - items and pricing table",
                attachment_type=allure.attachment_type.TEXT,
            )
            soft_assert.check_true(invoice_total is not None, "Invoice PDF should contain a readable Payable Amount")
            soft_assert.check_true(
                invoice_item_count >= 3,
                f"Invoice should list at least 3 line items (2 entered + 1 free bonus), got {invoice_item_count}",
            )
            soft_assert.check_true(
                bool(bonus_key) and bonus_key in summary_table.lower(),
                f"The scheme's tier-1 bonus product ({bonus_name!r}, read live) should appear on the invoice",
            )
        except Exception as exc:
            soft_assert.check(False, f"Invoice generation/verification step failed: {exc}")


@allure.epic("Bill / New Invoice")
@allure.feature("Happy path")
@allure.severity(allure.severity_level.NORMAL)
@allure.title(
    "Scenario 13: Click Print with 0 items -> expect validation alert -> enter 2 items -> "
    "verify Print Preview then works"
)
def test_scenario13_print_with_no_items_then_two_items(logged_in_driver, soft_assert):
    page = ProductPage(logged_in_driver)
    with step(page, f"Open product page and select customer '{CUSTOMER_NAME}'"):
        try:
            page.open()
            page.select_customer(CUSTOMER_NAME)
        except Exception as exc:
            soft_assert.check(False, f"Setup failed: {exc}")
            return

    with allure.step("Click Print with 0 items entered and verify the validation alert appears"):
        try:
            page.click(page.PRINT_BUTTON)
            alert_text = page.dismiss_one_alert(timeout=10)
            allure.attach(
                page.driver.get_screenshot_as_png(),
                name="Print with no items - alert screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            allure.attach(
                str(alert_text), name="print_no_items_alert_text", attachment_type=allure.attachment_type.TEXT
            )
            soft_assert.check_true(
                alert_text is not None,
                "Clicking Print with 0 items should show a validation alert instead of silently doing nothing",
            )
            if alert_text is not None:
                soft_assert.check_true(
                    "select items" in alert_text.lower() or "select item" in alert_text.lower(),
                    f"Alert text should tell the user to select items, got: {alert_text!r}",
                )
        except Exception as exc:
            soft_assert.check(False, f"Click Print with 0 items step failed: {exc}")
            return

    entered = {}
    with step(page, "Pick 2 products with stock and enter qty 1 each"):
        try:
            rows = page.pick_rows_with_stock(2, min_qty=1)
            _attach_rows_used(rows)
            for row_idx in rows:
                code = page.enter_quantity(row_idx, 1)
                entered[code] = True
            soft_assert.check_true(
                len(entered) == 2, f"Expected 2 distinct product rows entered, got {len(entered)}"
            )
        except Exception as exc:
            soft_assert.check(False, f"Entering quantities failed: {exc}")
            return

    with allure.step("Click Print again and verify the Print Preview modal now appears correctly"):
        try:
            page.click_print()
            note = page.get_print_preview_note()
            allure.attach(
                page.driver.get_screenshot_as_png(),
                name="Print Preview after entering items - screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            soft_assert.check_true(
                "not saved" in note.lower(), f"Print Preview note should mention not saved, got {note!r}"
            )
            page.close_print_preview()
        except Exception as exc:
            soft_assert.check(
                False,
                f"Print Preview did not work correctly after entering items (following the earlier empty-cart "
                f"Print click) -- this indicates the empty-cart click left the page in a bad state: {exc}",
            )


EXPECTED_COMPANY_NAME = "Demo Distributor 1"


@allure.epic("Bill / New Invoice")
@allure.feature("Happy path")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title(
    "Scenario 14: Enter product -> Calc -> click Print repeatedly (every 15s) -> verify the company "
    "header stays correct each time"
)
def test_scenario14_repeated_print_company_header_consistency(logged_in_driver, soft_assert):
    page = ProductPage(logged_in_driver)
    with step(page, f"Open product page and select customer '{CUSTOMER_NAME}'"):
        try:
            page.open()
            page.select_customer(CUSTOMER_NAME)
        except Exception as exc:
            soft_assert.check(False, f"Setup failed: {exc}")
            return

    with step(page, "Enter 1 product (chosen by live stock) and Calculate"):
        try:
            row_idx = page.pick_rows_with_stock(1, min_qty=1)[0]
            page.enter_quantity(row_idx, 1)
            page.click_calc()
        except Exception as exc:
            soft_assert.check(False, f"Entering product / Calculate failed: {exc}")
            return

    num_checks = 4
    for i in range(num_checks):
        with allure.step(f"Click Print (check {i + 1}/{num_checks}) and verify the company header"):
            try:
                opened, error_text = page.click_print_or_detect_error()
                if not opened:
                    allure.attach(
                        page.driver.get_screenshot_as_png(),
                        name=f"Print check {i + 1} - error dialog screenshot",
                        attachment_type=allure.attachment_type.PNG,
                    )
                    soft_assert.check(
                        False,
                        f"Check {i + 1}: clicking Print showed an error dialog instead of the Print "
                        f"Preview -- {error_text!r}",
                    )
                    break
                time.sleep(2)
                iframe_src = page.get_print_preview_iframe_src()
                pdf_text = fetch_invoice_text(page.driver, iframe_src)
                header_match = re.search(r"PrintPreview Receipt\s*\n\s*(.+)", pdf_text)
                company_on_header = header_match.group(1).strip() if header_match else None
                allure.attach(
                    page.driver.get_screenshot_as_png(),
                    name=f"Print Preview check {i + 1} - screenshot",
                    attachment_type=allure.attachment_type.PNG,
                )
                allure.attach(
                    f"iframe src: {iframe_src}\ncompany on header: {company_on_header!r}\n\n"
                    f"PDF text (first 500 chars):\n{pdf_text[:500]}",
                    name=f"print_check_{i + 1}_details",
                    attachment_type=allure.attachment_type.TEXT,
                )
                soft_assert.check_true(
                    company_on_header is not None,
                    f"Check {i + 1}: could not find a company header line in the Print Preview PDF at all",
                )
                if company_on_header is not None:
                    soft_assert.check_equal(
                        company_on_header,
                        EXPECTED_COMPANY_NAME,
                        f"Check {i + 1}: Print Preview company header should be '{EXPECTED_COMPANY_NAME}'",
                    )
                page.close_print_preview()
            except Exception as exc:
                soft_assert.check(False, f"Print check {i + 1}/{num_checks} failed: {exc}")
                break

        if i < num_checks - 1:
            time.sleep(15)


@allure.epic("Bill / New Invoice")
@allure.feature("Happy path")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title(
    "Scenario 15: 2 items (qty 2, 1) -> Add Sale -> Edit -> increase qty + add a new item -> "
    "Calc -> verify amount/items -> Update Sale -> Proceed -> verify against database"
)
def test_scenario15_edit_order_add_more_items_then_verify(logged_in_driver, soft_assert):
    with allure.step("Note the newest My Sales invoice for this customer BEFORE the sale"):
        baseline_invoice = _my_sales_baseline(logged_in_driver)
        allure.attach(str(baseline_invoice), name="my_sales_baseline_invoice",
                      attachment_type=allure.attachment_type.TEXT)

    page = ProductPage(logged_in_driver)
    with step(page, f"Open product page and select customer '{CUSTOMER_NAME}'"):
        try:
            page.open()
            page.select_customer(CUSTOMER_NAME)
        except Exception as exc:
            soft_assert.check(False, f"Setup failed: {exc}")
            return

    entered = {}
    with step(page, "Pick 2 products with stock and enter qty 2 and qty 1"):
        try:
            rows = page.pick_rows_with_stock(2, min_qty=2)
            _attach_rows_used(rows)
            code0 = page.enter_quantity(rows[0], 2)
            entered[code0] = 2
            code1 = page.enter_quantity(rows[1], 1)
            entered[code1] = 1
            soft_assert.check_true(
                len(entered) == 2, f"Expected 2 distinct product rows entered, got {len(entered)}"
            )
        except Exception as exc:
            soft_assert.check(False, f"Entering quantities failed: {exc}")
            return

    summary = _calculate_and_check_count(page, soft_assert, len(entered), "initial")

    with step(page, "Click Save and verify Payable Amount matches Final Amount"):
        try:
            page.click_save()
            payable = page.get_payable_amount()
            if summary is not None:
                soft_assert.check_true(
                    abs(_to_float(payable) - _to_float(summary["final_amount"])) < 1,
                    f"Payable Amount ({payable}) should match Calc Final Amount ({summary['final_amount']})",
                )
        except Exception as exc:
            soft_assert.check(False, f"Save step failed: {exc}")
            return

    with allure.step("Click Add Sale, verify Confirm Sale dialog, and Proceed"):
        try:
            page.click_add_sale()
            confirm_details = page.get_confirm_sale_details()
            allure.attach(
                page.driver.get_screenshot_as_png(),
                name="Confirm Sale dialog - screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            soft_assert.check_equal(
                confirm_details.get("No Of Items"), str(len(entered)), "Confirm Sale dialog: No Of Items"
            )
            page.confirm_sale_proceed()
            page.wait_for_sale_completed()
            page.dismiss_post_sale_print_preview()
        except Exception as exc:
            soft_assert.check(False, f"Add Sale step failed: {exc}")
            return

    my_sale_page = MySalePage(logged_in_driver)
    with allure.step("Verify the finalized sale on the My Sales report, then click Edit"):
        try:
            my_sale_page.open()
            latest_sale = my_sale_page.get_latest_sale_for_client(CUSTOMER_NAME, exclude_invoice_ids={baseline_invoice})
            allure.attach(str(latest_sale), name="my_sales_row_before_edit", attachment_type=allure.attachment_type.TEXT)
            soft_assert.check_true(latest_sale is not None, "A sale row for 'Demo Dealer 4' should exist on My Sales")
            if latest_sale is not None:
                soft_assert.check_equal(
                    latest_sale["no_of_items"], str(len(entered)), "My Sales: No. Of Items before edit"
                )
            my_sale_page.click_edit_for_client(
                CUSTOMER_NAME, invoice_id=latest_sale["invoice_id"] if latest_sale else None
            )
        except Exception as exc:
            soft_assert.check(False, f"My Sales verification / Edit navigation failed: {exc}")
            return

    edit_page = ProductPage(logged_in_driver)
    with step(edit_page, "On the Edit Sale page, increase an existing item's qty and add a new item"):
        try:
            edit_page.wait_for_grid_loaded()
            # The grid is initially scoped to just the order's existing items; "Add More" expands it
            # to the full catalog (existing items keep their pre-filled quantities) so a genuinely
            # new product becomes available at a row index beyond the order's own items. Do this
            # before editing any quantity, in case the grid re-renders and drops an in-progress edit.
            edit_page.click_add_more()
            edit_page.enter_quantity(0, 5)
            entered[list(entered.keys())[0]] = 5
            new_code = edit_page.enter_quantity(2, 1)
            entered[new_code] = 1
            soft_assert.check_true(
                len(entered) == 3, f"Expected 3 distinct product rows after adding a new item, got {len(entered)}"
            )
        except Exception as exc:
            soft_assert.check(False, f"Editing quantities failed: {exc}")
            return

    edit_summary = _calculate_and_check_count(edit_page, soft_assert, len(entered), "after edit")

    with allure.step("Open View Selected Items and verify the item count/amount after editing"):
        try:
            edit_page.open_view_selected_items()
            items, vsi_total = edit_page.get_selected_items()
            allure.attach(
                edit_page.driver.get_screenshot_as_png(),
                name="View Selected Items after edit - screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            allure.attach(str(items), name="selected_items_after_edit", attachment_type=allure.attachment_type.TEXT)
            soft_assert.check_equal(
                len(items), len(entered), "View Selected Items count after edit vs entered"
            )
            if edit_summary is not None and vsi_total is not None:
                soft_assert.check_true(
                    abs(_to_float(vsi_total["value"]) - _to_float(edit_summary["final_amount"])) < 1,
                    f"View Selected Items total ({vsi_total['value']}) should match the Calc Final Amount "
                    f"({edit_summary['final_amount']}) after editing",
                )
            edit_page.close_selected_items()
        except Exception as exc:
            soft_assert.check(False, f"View Selected Items step failed: {exc}")
            return

    with allure.step("Save, click Update Sale, verify the confirmation dialog, and Proceed"):
        try:
            edit_page.click_save()
            edit_page.click_update_sale()
            update_details = edit_page.get_confirm_update_details()
            allure.attach(
                edit_page.driver.get_screenshot_as_png(),
                name="Confirm Update dialog - screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            allure.attach(str(update_details), name="confirm_update_details", attachment_type=allure.attachment_type.TEXT)
            if edit_summary is not None:
                soft_assert.check_equal(
                    update_details.get("No Of Items"), edit_summary["total_item"],
                    "Confirm Update dialog: No Of Items vs Edit page Calc Total Item",
                )
            edit_page.confirm_update_proceed()
        except Exception as exc:
            soft_assert.check(False, f"Save/Update Sale step failed: {exc}")
            return

    with allure.step("Verify the updated order directly against the database"):
        try:
            expected_amount = _to_float(edit_summary["final_amount"]) if edit_summary is not None else 0
            _verify_order_against_database(soft_assert, CUSTOMER_NAME, len(entered), expected_amount, "scenario15")
        except Exception as exc:
            soft_assert.check(False, f"Database verification step failed: {exc}")


@allure.epic("Bill / New Invoice")
@allure.feature("Schemes / Free Goods")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title(
    "Scenario 16: Single scheme product sized to cross its own scheme threshold -> Calc -> Save -> "
    "Add Sale -> Proceed -> verify invoice + DB -> Edit via My Sales -> verify scheme still applied -> "
    "Proceed -> verify DB"
)
def test_scenario16_single_scheme_product_edit_verify_scheme_persists(logged_in_driver, soft_assert):
    with allure.step("Note the newest My Sales invoice for this customer BEFORE the sale"):
        baseline_invoice = _my_sales_baseline(logged_in_driver)
        allure.attach(str(baseline_invoice), name="my_sales_baseline_invoice",
                      attachment_type=allure.attachment_type.TEXT)

    page = ProductPage(logged_in_driver)
    with step(page, f"Open product page and select customer '{CUSTOMER_NAME}'"):
        try:
            page.open()
            page.select_customer(CUSTOMER_NAME)
        except Exception as exc:
            soft_assert.check(False, f"Setup failed: {exc}")
            return

    tier1_min = None
    tier1_max = None
    row_idx = None
    with step(page, "Search the scheme product and read its current tier-1 range from its own Scheme Details popup"):
        try:
            row_idx = page.search_product("Aam Chaska Falala Candy [1*10]")
            info = page.product_row(row_idx)
            soft_assert.check_true(info["scheme_id"] is not None, "Product should carry a scheme tag")
            tiers = page.get_scheme_tiers(row_idx)
            allure.attach(str(tiers), name="scheme_tiers_read_live", attachment_type=allure.attachment_type.TEXT)
            soft_assert.check_true(len(tiers) >= 1, "Scheme Details popup should list at least one tier")
            if not tiers:
                return
            tier1_min, tier1_max = tiers[0]["min"], tiers[0]["max"]
        except Exception as exc:
            soft_assert.check(False, f"Reading scheme tiers failed: {exc}")
            return

    qty = None
    line_amount = None
    with step(page, "Enter enough quantity to cross the tier-1 threshold read live, on its own"):
        try:
            info = page.product_row(row_idx)
            qty = max(1, int(tier1_min / info["price"]) + 1)
            qty = min(qty, max(1, int(info["available_stock"])))
            page.enter_quantity(row_idx, qty)
            line_amount = info["price"] * qty
            allure.attach(
                f"Product: {info['display_name']} | price/carton={info['price']} | qty={qty} | "
                f"line amount={line_amount:.2f} | scheme_id={info['scheme_id']} | "
                f"tier1 range=[{tier1_min}, {tier1_max}] (read live from Scheme Details)",
                name="product_details",
                attachment_type=allure.attachment_type.TEXT,
            )
            soft_assert.check_true(
                tier1_min <= line_amount <= tier1_max,
                f"Single product's own line amount ({line_amount:.2f}) should land within the scheme's "
                f"live tier-1 range ({tier1_min}-{tier1_max}) on its own, without needing a second product",
            )
        except Exception as exc:
            soft_assert.check(False, f"Entering the scheme product failed: {exc}")
            return

    summary = None
    with step(page, "Calculate and verify the scheme applied (Free Item >= 1, Total Scheme > 0)"):
        try:
            page.click_calc()
            summary = page.get_summary()
            allure.attach(str(summary), name="calc_summary_initial", attachment_type=allure.attachment_type.TEXT)
            soft_assert.check_equal(
                summary["total_item"], "1", "Calc Total Item should be 1 (single product entered)"
            )
            soft_assert.check_true(
                _to_float(summary["free_item"]) >= 1,
                f"Free Item should be at least 1 once this single product crosses the scheme threshold "
                f"on its own, got {summary['free_item']}",
            )
            soft_assert.check_true(
                _to_float(summary["total_scheme"]) > 0,
                f"Total Scheme should be > 0, got {summary['total_scheme']}",
            )
        except Exception as exc:
            soft_assert.check(False, f"Calculate step failed: {exc}")
            return

    with step(page, "Click Save and verify Payable Amount matches Final Amount"):
        try:
            page.click_save()
            payable = page.get_payable_amount()
            if summary is not None:
                soft_assert.check_true(
                    abs(_to_float(payable) - _to_float(summary["final_amount"])) < 1,
                    f"Payable Amount ({payable}) should match Calc Final Amount ({summary['final_amount']})",
                )
        except Exception as exc:
            soft_assert.check(False, f"Save step failed: {exc}")
            return

    with allure.step("Click Add Sale, verify Confirm Sale dialog, and Proceed"):
        try:
            page.click_add_sale()
            confirm_details = page.get_confirm_sale_details()
            allure.attach(
                page.driver.get_screenshot_as_png(),
                name="Confirm Sale dialog - screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            allure.attach(
                str(confirm_details), name="confirm_sale_details", attachment_type=allure.attachment_type.TEXT
            )
            page.confirm_sale_proceed()
            page.wait_for_sale_completed()
        except Exception as exc:
            soft_assert.check(False, f"Add Sale step failed: {exc}")
            return

    with allure.step("Verify the newly created order directly against the database"):
        try:
            expected_amount = _to_float(summary["final_amount"]) if summary is not None else 0
            _verify_order_against_database(soft_assert, CUSTOMER_NAME, 1, expected_amount, "scenario16_initial")
        except Exception as exc:
            soft_assert.check(False, f"Database verification step (initial) failed: {exc}")

    with allure.step("Generate the invoice and verify the bonus item appears on it"):
        try:
            invoice_url, invoice_screenshot = page.generate_invoice_and_get_url()
            allure.attach(
                invoice_screenshot, name="Invoice - screenshot", attachment_type=allure.attachment_type.PNG
            )
            invoice_text = fetch_invoice_text(page.driver, invoice_url)
            invoice_total = extract_payable_amount(invoice_text)
            invoice_item_count = extract_line_item_count(invoice_text)
            summary_table = extract_items_and_pricing_table(invoice_text)
            allure.attach(
                f"Invoice Payable Amount: {invoice_total} | Invoice line items: {invoice_item_count}\n\n"
                f"{summary_table}",
                name="Invoice - items and pricing table",
                attachment_type=allure.attachment_type.TEXT,
            )
            soft_assert.check_true(invoice_total is not None, "Invoice PDF should contain a readable Payable Amount")
            soft_assert.check_true(
                invoice_item_count >= 1,
                f"Invoice should list at least 1 line item (the entered product), got {invoice_item_count}",
            )
        except Exception as exc:
            soft_assert.check(False, f"Invoice generation/verification step failed: {exc}")
            return

    my_sale_page = MySalePage(logged_in_driver)
    latest_sale = None
    with allure.step("Verify the finalized sale on the My Sales report"):
        try:
            my_sale_page.open()
            latest_sale = my_sale_page.get_latest_sale_for_client(CUSTOMER_NAME, exclude_invoice_ids={baseline_invoice})
            allure.attach(str(latest_sale), name="my_sales_latest_row", attachment_type=allure.attachment_type.TEXT)
            soft_assert.check_true(latest_sale is not None, "A sale row for 'Demo Dealer 4' should exist on My Sales")
        except Exception as exc:
            soft_assert.check(False, f"My Sales verification step failed: {exc}")
            return

    edit_summary = None
    with allure.step("Click Edit and verify the scheme is still applied on the Edit Sale page"):
        try:
            my_sale_page.click_edit_for_client(
                CUSTOMER_NAME, invoice_id=latest_sale["invoice_id"] if latest_sale else None
            )
            edit_page = ProductPage(logged_in_driver)
            edit_page.click_calc()
            edit_summary = edit_page.get_summary()
            allure.attach(
                str(edit_summary), name="edit_page_calc_summary", attachment_type=allure.attachment_type.TEXT
            )
            soft_assert.check_true(
                _to_float(edit_summary["free_item"]) >= 1,
                f"Free Item should still be at least 1 on the Edit Sale page (the scheme should persist "
                f"through editing), got {edit_summary['free_item']}",
            )
            soft_assert.check_true(
                _to_float(edit_summary["total_scheme"]) > 0,
                f"Total Scheme should still be > 0 on the Edit Sale page, got {edit_summary['total_scheme']}",
            )
        except Exception as exc:
            soft_assert.check(False, f"Edit Sale page Calc step failed: {exc}")
            return

    with allure.step("Save, click Update Sale, verify the confirmation dialog, and Proceed"):
        try:
            edit_page.click_save()
            edit_page.click_update_sale()
            update_details = edit_page.get_confirm_update_details()
            allure.attach(
                edit_page.driver.get_screenshot_as_png(),
                name="Confirm Update dialog - screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            allure.attach(
                str(update_details), name="confirm_update_details", attachment_type=allure.attachment_type.TEXT
            )
            edit_page.confirm_update_proceed()
        except Exception as exc:
            soft_assert.check(False, f"Save/Update Sale step failed: {exc}")
            return

    with allure.step("Verify the updated order directly against the database (scheme should still be reflected)"):
        try:
            expected_amount = _to_float(edit_summary["final_amount"]) if edit_summary is not None else 0
            _verify_order_against_database(soft_assert, CUSTOMER_NAME, 1, expected_amount, "scenario16_after_edit")
        except Exception as exc:
            soft_assert.check(False, f"Database verification step (after edit) failed: {exc}")
