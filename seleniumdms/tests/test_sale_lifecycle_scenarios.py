"""End-to-end sale lifecycle scenarios for customer 'Demo Dealer 3':

  Scenario A: sale (3 in-stock items) -> invoice -> My Sales -> Edit -> Add More (2 pop-ups) ->
              add 1 item -> Save -> Update -> verify My Sales, invoice and DB show 4 items
  Scenario B: sale -> invoice -> wait 20s -> Sale Return 'With Reference' on that order ->
              Full return -> Return Details -> credit note -> verify against the sale and the DB
  Scenario C: sale -> invoice -> wait 20s -> Sale Return 'With Reference' on that order ->
              Partial return (2 of 3 items) -> Return Details -> credit note -> verify + DB
"""
import re
import time

import allure
import pytest

from pages.my_sale_page import MySalePage
from pages.product_page import ProductPage
from pages.return_details_page import ReturnDetailsPage
from pages.sale_return_page import SaleReturnPage
from utilities.allure_utils import step
from utilities.db import get_latest_return_for_client, get_order_header, get_order_products, get_return_products
from utilities.invoice_pdf import extract_line_item_count, extract_payable_amount, fetch_invoice_text

CUSTOMER_NAME = "Demo Dealer 3"
pytestmark = pytest.mark.xdist_group(name="dd3")  # parallel runs: one group per customer, never shared

SALE_ITEMS = 3
QTY = 1
WAIT_BEFORE_RETURN = 20      # seconds, as in the manual steps (lets the new invoice become returnable)
TOLERANCE = 1.0              # rupees


def _num(value):
    match = re.search(r"-?\d+(?:\.\d+)?", str(value or "").replace(",", ""))
    return float(match.group()) if match else None


def _close(a, b):
    a, b = _num(a), _num(b)
    return a is not None and b is not None and abs(a - b) <= TOLERANCE


def _text_has_amount(text, amount):
    target = _num(amount)
    if target is None:
        return False
    for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text or ""):
        value = _num(n)
        if value is not None and abs(value - target) <= TOLERANCE:
            return True
    return False


# ------------------------------------------------------------------ shared: create a sale and read its invoice

def _create_sale_and_read_invoice(driver, soft_assert, tag):
    """Bill/New Invoice for CUSTOMER_NAME with SALE_ITEMS in-stock items -> Save -> Add Sale -> Proceed ->
    invoice. Returns a dict with the order id, My Sales invoice id, item codes, Calc summary and
    invoice details."""
    my_sales = MySalePage(driver)
    with step(ProductPage(driver), "Note the newest My Sales invoice for this customer (baseline)"):
        try:
            baseline = my_sales.open().get_latest_invoice_id(CUSTOMER_NAME)
        except Exception:
            baseline = None
        allure.attach(str(baseline), name=f"{tag}_my_sales_baseline", attachment_type=allure.attachment_type.TEXT)

    page = ProductPage(driver)
    with step(page, f"Bill/New Invoice: select '{CUSTOMER_NAME}' and add {SALE_ITEMS} items that have inventory"):
        page.open()
        page.select_customer(CUSTOMER_NAME)
        rows = page.pick_rows_with_stock(SALE_ITEMS, min_qty=QTY)
        codes = [page.enter_quantity(r, QTY) for r in rows]
        allure.attach(f"rows={rows}\nitem codes={codes}", name=f"{tag}_items", attachment_type=allure.attachment_type.TEXT)

    with step(page, "Calculate"):
        page.click_calc()
        summary = page.get_summary()
        allure.attach(str(summary), name=f"{tag}_calc", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_equal(summary["total_item"], str(SALE_ITEMS), "Sale: Calc Total Item")

    with step(page, "Save and confirm the order (Add Sale -> Yes! Proceed.)"):
        page.click_save()
        payable = page.get_payable_amount()
        soft_assert.check_true(
            _close(payable, summary["final_amount"]),
            f"Sale: Payable Amount ({payable}) should match Calc Final Amount ({summary['final_amount']})",
        )
        page.click_add_sale()
        confirm = page.get_confirm_sale_details()
        allure.attach(str(confirm), name=f"{tag}_confirm_sale", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_equal(confirm.get("No Of Items"), str(SALE_ITEMS), "Sale: Confirm Sale dialog No Of Items")
        page.confirm_sale_proceed()
        page.wait_for_sale_completed()

    with step(page, "Get the details from the invoice"):
        invoice_url, invoice_png = page.generate_invoice_and_get_url()
        allure.attach(invoice_png, name=f"{tag}_invoice", attachment_type=allure.attachment_type.PNG)
        invoice_text = fetch_invoice_text(driver, invoice_url)
        invoice_payable = extract_payable_amount(invoice_text)
        invoice_lines = extract_line_item_count(invoice_text)
        allure.attach(f"URL: {invoice_url}\nPayable: {invoice_payable}\nLines: {invoice_lines}\n\n{invoice_text[:3000]}",
                      name=f"{tag}_invoice_text", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_true(invoice_payable is not None, "Sale: invoice should show a readable Payable Amount")
        if invoice_payable is not None:
            soft_assert.check_true(
                _close(invoice_payable, payable),
                f"Sale: invoice Payable ({invoice_payable}) should match the sale's Payable Amount ({payable})",
            )
        soft_assert.check_equal(invoice_lines, SALE_ITEMS, "Sale: invoice line-item count")

    with step(page, "Find the new sale on My Sales"):
        sale_row = my_sales.open().get_latest_sale_for_client(CUSTOMER_NAME, exclude_invoice_ids={baseline})
        allure.attach(str(sale_row), name=f"{tag}_my_sales_row", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_true(sale_row is not None, "Sale: the new sale should appear on My Sales")
        if sale_row is not None:
            soft_assert.check_equal(sale_row["no_of_items"], str(SALE_ITEMS), "Sale: My Sales No. Of Items")
            soft_assert.check_true(
                _close(sale_row["amount"], payable),
                f"Sale: My Sales Amount ({sale_row['amount']}) should match the sale's Payable ({payable})",
            )

    # Order id: from the invoice URL if it carries it, else from the My Sales invoice id (e.g. '254292904/tb3391').
    order_id = None
    m = re.search(r"OrderId=(\d+)", invoice_url, flags=re.IGNORECASE)
    if m:
        order_id = int(m.group(1))
    elif sale_row is not None:
        head = sale_row["invoice_id"].split("/")[0].strip()
        order_id = int(head) if head.isdigit() else None
    allure.attach(str(order_id), name=f"{tag}_order_id", attachment_type=allure.attachment_type.TEXT)

    return {
        "order_id": order_id,
        "invoice_id": sale_row["invoice_id"] if sale_row else None,
        "codes": codes,
        "summary": summary,
        "payable": payable,
        "invoice_payable": invoice_payable,
    }


def _verify_credit_note_and_db(driver, soft_assert, tag, expected_items, expected_amount, must_be_less_than=None):
    """Return Details: newest row -> Action -> Print -> credit note; then the latest return in the DB."""
    details = ReturnDetailsPage(driver)
    with step(SaleReturnPage(driver), "Return Details: check the newest row"):
        url = details.wait_for_page()
        row = details.newest_row(CUSTOMER_NAME)
        allure.attach(f"URL: {url}\nNewest row: {row}", name=f"{tag}_return_details_row",
                      attachment_type=allure.attachment_type.TEXT)
        party = details.column(row, "Party Name") or row.get("_text", "")
        soft_assert.check_true(CUSTOMER_NAME.lower() in party.lower(),
                               f"Return Details: newest row should be for {CUSTOMER_NAME!r}, got {party!r}")
        items_cell = details.column(row, "No. Of Items", "No Of Items")
        if items_cell is not None:
            soft_assert.check_equal(_num(items_cell), float(expected_items), "Return Details: No. Of Items")
        amount_cell = details.column(row, "Amount")
        if amount_cell is not None:
            soft_assert.check_true(
                _close(amount_cell, expected_amount),
                f"Return Details: Amount ({amount_cell}) should match the return amount ({expected_amount})",
            )

    with step(SaleReturnPage(driver), "Return Details: Action -> Print -> verify the credit note"):
        note = details.open_newest_credit_note(CUSTOMER_NAME)
        try:
            note_text = fetch_invoice_text(driver, note["url"])
        except Exception as exc:
            note_text = ""
            allure.attach(str(exc), name=f"{tag}_credit_note_read_error", attachment_type=allure.attachment_type.TEXT)
        details.close_credit_note(note)
        allure.attach(note["screenshot"], name=f"{tag}_credit_note", attachment_type=allure.attachment_type.PNG)
        allure.attach(f"URL: {note['url']}\nTitle: {note['title']}\n\n{note_text[:3000]}",
                      name=f"{tag}_credit_note_text", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_true(note["url"] not in ("", "about:blank"), "Credit note: tab should load a document")
        if note_text:
            soft_assert.check_true(
                _text_has_amount(note_text, expected_amount),
                f"Credit note: should show the return amount {expected_amount}",
            )
            lines = extract_line_item_count(note_text)
            if lines:
                soft_assert.check_equal(lines, expected_items, "Credit note: line-item count")

    with step(SaleReturnPage(driver), "Verify the return in the database"):
        try:
            ret = get_latest_return_for_client(CUSTOMER_NAME)
            soft_assert.check_true(ret is not None, f"DB: a return (CreditNote) should exist for {CUSTOMER_NAME!r}")
            if ret is not None:
                products = get_return_products(ret["Order_Id"])
                allure.attach(
                    str({k: v for k, v in ret.items() if k in ("Order_Id", "Client_Name", "OrderType", "Order_Amt", "NoOfProducts")})
                    + f"\nproduct rows: {len(products)}",
                    name=f"{tag}_db_return", attachment_type=allure.attachment_type.TEXT,
                )
                soft_assert.check_true(
                    _close(ret["Order_Amt"], expected_amount),
                    f"DB: return Order_Amt ({ret['Order_Amt']}) should match the return amount ({expected_amount})",
                )
                soft_assert.check_equal(int(float(ret["NoOfProducts"])), expected_items, "DB: return NoOfProducts")
                soft_assert.check_equal(len(products), expected_items, "DB: return product rows")
                if must_be_less_than is not None:
                    soft_assert.check_true(
                        float(ret["Order_Amt"]) < _num(must_be_less_than) - TOLERANCE,
                        f"DB: a partial return ({ret['Order_Amt']}) should be less than the sale ({must_be_less_than})",
                    )
        except Exception as exc:
            soft_assert.check(False, f"DB verification failed: {exc}")


def _open_with_reference(driver, soft_assert, sale, tag):
    """Sale Return -> wait 20s -> 'With Reference' -> select the sale's order. Returns (page, invoice)."""
    page = SaleReturnPage(driver)
    with step(page, f"Navigate to Sale Return and wait {WAIT_BEFORE_RETURN} seconds"):
        page.open()
        time.sleep(WAIT_BEFORE_RETURN)

    with step(page, f"With Reference: open order {sale['order_id']}"):
        assert sale["order_id"] is not None, "Could not determine the new sale's order id (invoice URL / My Sales)"
        invoice = page.open_with_reference_and_select_invoice(CUSTOMER_NAME, sale["order_id"])
        allure.attach(str(invoice), name=f"{tag}_reference_invoice", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_equal(invoice["noofitem"], str(SALE_ITEMS), "With Reference: invoice No Of Item")
        soft_assert.check_true(
            _close(invoice["amount"], sale["payable"]),
            f"With Reference: invoice Amount ({invoice['amount']}) should match the sale ({sale['payable']})",
        )
        soft_assert.check_equal(page.get_visible_product_row_count(), SALE_ITEMS,
                                "With Reference: grid shows exactly the invoice's items")
    return page, invoice


# ------------------------------------------------------------------ Scenario A

@allure.epic("Bill / New Invoice")
@allure.feature("Sale lifecycle")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Sale (3 items) -> invoice -> My Sales Edit -> Add More (2 pop-ups) -> add 1 item -> Save -> Update -> verify 4 items everywhere")
def test_sale_then_edit_add_more_item(logged_in_driver, soft_assert):
    sale = _create_sale_and_read_invoice(logged_in_driver, soft_assert, "A")

    my_sales = MySalePage(logged_in_driver)
    edit = ProductPage(logged_in_driver)
    with step(edit, "My Sales: hover Action on the new sale and click Edit"):
        my_sales.open()
        my_sales.click_edit_for_client(CUSTOMER_NAME, invoice_id=sale["invoice_id"])
        edit.wait_for_grid_loaded()

    with step(edit, "Click Add More and OK the two pop-ups"):
        edit.click_add_more()

    with step(edit, "Add another item that has inventory"):
        candidates = edit.pick_rows_with_stock(SALE_ITEMS + 3, min_qty=QTY)
        new_row = next((r for r in candidates if edit.product_row(r)["item_code"] not in sale["codes"]), None)
        assert new_row is not None, "No additional in-stock item found after Add More"
        new_code = edit.enter_quantity(new_row, QTY)
        allure.attach(new_code, name="A_added_item", attachment_type=allure.attachment_type.TEXT)

    expected = SALE_ITEMS + 1
    with step(edit, "Calculate and View Selected Items"):
        edit.click_calc()
        edit_summary = edit.get_summary()
        allure.attach(str(edit_summary), name="A_edit_calc", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_equal(edit_summary["total_item"], str(expected), "Edit: Calc Total Item")
        soft_assert.check_true(
            _num(edit_summary["final_amount"]) > _num(sale["payable"]),
            f"Edit: Final Amount ({edit_summary['final_amount']}) should be higher than the original sale ({sale['payable']})",
        )
        edit.open_view_selected_items()
        items, vsi_total = edit.get_selected_items()
        allure.attach(str(items), name="A_edit_view_selected", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_equal(len(items), expected, "Edit: View Selected Items count")
        if vsi_total is not None:
            soft_assert.check_true(
                _close(vsi_total["value"], edit_summary["final_amount"]),
                f"Edit: View Selected total ({vsi_total['value']}) should match Calc ({edit_summary['final_amount']})",
            )
        edit.close_selected_items()

    with step(edit, "Save and confirm (Update Sale -> Proceed)"):
        edit.click_save()
        edit.click_update_sale()
        update = edit.get_confirm_update_details()
        allure.attach(str(update), name="A_confirm_update", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_equal(update.get("No Of Items"), str(expected), "Edit: Confirm Update No Of Items")
        edit.confirm_update_proceed()
        edit.dismiss_post_sale_print_preview()

    with step(edit, "Verify the edited sale on My Sales and its invoice"):
        my_sales.open()
        row = my_sales._resolve_row(CUSTOMER_NAME, sale["invoice_id"])
        data = my_sales._row_data(row) if row is not None else None
        allure.attach(str(data), name="A_my_sales_after_edit", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_true(data is not None, "Edited sale should still be on My Sales")
        if data is not None:
            soft_assert.check_equal(data["no_of_items"], str(expected), "After edit: My Sales No. Of Items")
            soft_assert.check_true(
                _close(data["amount"], edit_summary["final_amount"]),
                f"After edit: My Sales Amount ({data['amount']}) should match Calc ({edit_summary['final_amount']})",
            )
        url, png = my_sales.print_invoice_for_client(CUSTOMER_NAME, invoice_id=sale["invoice_id"])
        allure.attach(png, name="A_invoice_after_edit", attachment_type=allure.attachment_type.PNG)
        text = fetch_invoice_text(logged_in_driver, url)
        soft_assert.check_equal(extract_line_item_count(text), expected, "After edit: invoice line-item count")
        inv_payable = extract_payable_amount(text)
        soft_assert.check_true(
            inv_payable is not None and _close(inv_payable, edit_summary["final_amount"]),
            f"After edit: invoice Payable ({inv_payable}) should match Calc ({edit_summary['final_amount']})",
        )

    with step(edit, "Verify the edited order in the database"):
        try:
            header = get_order_header(sale["order_id"])
            products = get_order_products(sale["order_id"])
            allure.attach(f"{header}\nproduct rows: {len(products)}", name="A_db_order",
                          attachment_type=allure.attachment_type.TEXT)
            soft_assert.check_equal(int(float(header["NoOfProducts"])), expected, "After edit: DB NoOfProducts")
            soft_assert.check_equal(len(products), expected, "After edit: DB product rows")
            soft_assert.check_true(
                _close(header["Order_Amt"], edit_summary["final_amount"]),
                f"After edit: DB Order_Amt ({header['Order_Amt']}) should match Calc ({edit_summary['final_amount']})",
            )
        except Exception as exc:
            soft_assert.check(False, f"DB verification failed: {exc}")


# ------------------------------------------------------------------ Scenario B

@allure.epic("Sale Return")
@allure.feature("Sale lifecycle")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Sale (3 items) -> invoice -> wait 20s -> Sale Return With Reference on that order -> Full return -> credit note + DB")
def test_sale_then_full_return_with_reference(logged_in_driver, soft_assert):
    sale = _create_sale_and_read_invoice(logged_in_driver, soft_assert, "B")
    page, invoice = _open_with_reference(logged_in_driver, soft_assert, sale, "B")

    with step(page, "Click Select All (copies each item's sold qty into Qty) and Calculate"):
        soft_assert.check_true(page.select_all_reference_items(), "Select All should fill the Qty boxes")
        page.click_calc()
        summary = page.get_summary()
        allure.attach(str(summary), name="B_return_calc", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_equal(summary["total_item"], str(SALE_ITEMS), "Full return: Calc Total Item")

    with step(page, "Save -> Goods Receive -> Yes! Proceed."):
        confirm_text = page.complete_return_with_save()
        allure.attach(confirm_text, name="B_return_confirm", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_true(f"No Of Items : {SALE_ITEMS}" in confirm_text,
                               f"Return Confirm should show {SALE_ITEMS} items: {confirm_text!r}")
        page.confirm_receive_proceed()
        msg = page.get_success_message()
        allure.attach(msg, name="B_success", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_true("success" in msg.lower(), f"Unexpected result message: {msg!r}")
        page.dismiss_success()

    _verify_credit_note_and_db(logged_in_driver, soft_assert, "B", SALE_ITEMS, invoice["amount"])


# ------------------------------------------------------------------ Scenario C

@allure.epic("Sale Return")
@allure.feature("Sale lifecycle")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Sale (3 items) -> invoice -> wait 20s -> Sale Return With Reference on that order -> Partial return (2 of 3) -> credit note + DB")
def test_sale_then_partial_return_with_reference(logged_in_driver, soft_assert):
    sale = _create_sale_and_read_invoice(logged_in_driver, soft_assert, "C")
    page, invoice = _open_with_reference(logged_in_driver, soft_assert, sale, "C")
    returned = SALE_ITEMS - 1

    with step(page, "Partial return: Select All, then remove one item (keep the others)"):
        soft_assert.check_true(page.select_all_reference_items(), "Select All should fill the Qty boxes")
        removed = page.enter_saleable_qty(SALE_ITEMS - 1, "")
        allure.attach(removed, name="C_item_not_returned", attachment_type=allure.attachment_type.TEXT)

    with step(page, "Calculate and View Selected Items"):
        page.click_calc()
        summary = page.get_summary()
        allure.attach(str(summary), name="C_return_calc", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_equal(summary["total_item"], str(returned), "Partial return: Calc Total Item")
        soft_assert.check_true(
            _num(summary["final_amount"]) < _num(invoice["amount"]) - TOLERANCE,
            f"Partial return amount ({summary['final_amount']}) should be less than the invoice ({invoice['amount']})",
        )
        page.open_view_selected_items()
        items = page.get_selected_items()
        allure.attach(str(items), name="C_view_selected", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_equal(len(items), returned, "Partial return: View Selected Items count")
        page.close_selected_items()

    with step(page, "Save -> Goods Receive -> Yes! Proceed. -> OK"):
        confirm_text = page.complete_return_with_save()
        allure.attach(confirm_text, name="C_return_confirm", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_true(f"No Of Items : {returned}" in confirm_text,
                               f"Return Confirm should show {returned} items: {confirm_text!r}")
        page.confirm_receive_proceed()
        msg = page.get_success_message()
        allure.attach(msg, name="C_success", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_true("success" in msg.lower(), f"Unexpected result message: {msg!r}")
        page.dismiss_success()

    _verify_credit_note_and_db(logged_in_driver, soft_assert, "C", returned, summary["final_amount"],
                               must_be_less_than=invoice["amount"])
