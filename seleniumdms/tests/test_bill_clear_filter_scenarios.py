"""Bill/New Invoice: Clear, and the Group1 filter keeping the cart intact.

  1. Add an item -> Clear -> OK -> Calculate: every header value must be 0.
  2. Add 2 items -> Calculate -> add a 3rd -> choose a Group1 option -> add a 4th from the filtered list ->
     Calculate: header must match View Selected Items (count, items, total).
  3. Add 2 items -> Calculate -> choose a Group1 option: the 2 selected items must stay at the top of the
     filtered list with their quantities.
"""
import re

import allure

from pages.bill_filter_page import BillFilterPage
from utilities.allure_utils import step

CUSTOMER_NAME = "Demo Dealer 4"
QTY = 1
TOLERANCE = 1.0
HEADER_FIELDS = ("total_item", "qty_pcs", "all_qty_pcs", "amount", "free_item", "total_scheme", "total_gst", "final_amount")


def _num(value):
    match = re.search(r"-?\d+(?:\.\d+)?", str(value or "").replace(",", ""))
    return float(match.group()) if match else None


def _open(driver):
    page = BillFilterPage(driver)
    page.open()
    page.select_customer(CUSTOMER_NAME)
    return page


def _add_items(page, count, exclude=()):
    """Enter QTY for `count` in-stock items (not in exclude). Returns their item codes."""
    codes = []
    for i in page.pick_rows_with_stock(count + len(exclude) + 2, min_qty=QTY):
        if len(codes) == count:
            break
        code = page.product_row(i)["item_code"]
        if code in exclude or code in codes:
            continue
        page.enter_quantity(i, QTY)
        codes.append(code)
    assert len(codes) == count, f"Could only add {len(codes)} of {count} in-stock items"
    return codes


@allure.epic("Bill / New Invoice")
@allure.feature("Clear")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Bill: add item -> Clear -> OK -> Calculate -> every header value is 0")
def test_clear_resets_header_to_zero(logged_in_driver, soft_assert):
    page = _open(logged_in_driver)

    with step(page, "Add an in-stock item and Calculate"):
        codes = _add_items(page, 1)
        page.click_calc()
        before = page.get_summary()
        allure.attach(f"items={codes}\n{before}", name="before_clear", attachment_type=allure.attachment_type.TEXT)

    with step(page, "Click Clear and OK"):
        text = page.click_clear_and_ok()
        allure.attach(str(text), name="clear_confirmation", attachment_type=allure.attachment_type.TEXT)

    with step(page, "Click Calculate: all header details should be 0"):
        after = page.calculate_allowing_empty()
        allure.attach(str(after), name="after_clear", attachment_type=allure.attachment_type.TEXT)
        not_zero = {k: after.get(k) for k in HEADER_FIELDS if k in after and (_num(after.get(k)) or 0) != 0}
        soft_assert.check_true(not not_zero, f"BUG: after Clear and Calculate the header is not all 0: {not_zero}")
        leftover = [(c, q) for _, c, q in page.row_codes() if c in codes and (_num(q) or 0) != 0]
        soft_assert.check_true(not leftover, f"BUG: item qty still filled after Clear: {leftover}")


@allure.epic("Bill / New Invoice")
@allure.feature("Group filter")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Bill: 2 items -> Calculate -> 3rd item -> Group1 filter -> 4th item -> Calculate = View Selected Items")
def test_group1_filter_keeps_cart_consistent(logged_in_driver, soft_assert):
    page = _open(logged_in_driver)

    with step(page, "Add 2 in-stock items and Calculate"):
        codes = _add_items(page, 2)
        page.click_calc()

    with step(page, "Add a 3rd item"):
        codes += _add_items(page, 1, exclude=codes)

    with step(page, "Choose a Group1 option and add an in-stock item from the filtered list"):
        chosen, row = None, None
        for value, text in page.group1_options()[:8]:
            shown = page.select_group1(value)
            row = page.first_in_stock_row_excluding(codes, QTY)
            if row is not None:
                chosen = shown
                break
        assert row is not None, "No Group1 option produced an in-stock item to add"
        code4 = page.product_row(row)["item_code"]
        page.enter_quantity(row, QTY)
        codes.append(code4)
        allure.attach(f"Group1 option={chosen}\nitems in cart={codes}", name="filter_and_items",
                      attachment_type=allure.attachment_type.TEXT)

    with step(page, "Calculate and compare with View Selected Items"):
        page.click_calc()
        header = page.get_summary()
        page.open_view_selected_items()
        items, total = page.get_selected_items()
        page.close_selected_items()
        vsi_codes = [i["vsku"] for i in items]
        allure.attach(f"header={header}\n\nView Selected={items}\ntotal={total}", name="header_vs_view_selected",
                      attachment_type=allure.attachment_type.TEXT)

        soft_assert.check_true(_num(header["total_item"]) == len(codes),
                               f"BUG: header Total Item is {header['total_item']}, {len(codes)} items were added")
        soft_assert.check_true(len(items) == len(codes),
                               f"BUG: View Selected Items lists {len(items)} items, {len(codes)} were added")
        if any(c in vsi_codes for c in codes):  # only compare codes when View Selected shows the same item codes
            missing = [c for c in codes if c not in vsi_codes]
            soft_assert.check_true(not missing, f"BUG: items missing from View Selected Items after the filter: {missing}")
        if total is not None:
            soft_assert.check_true(
                abs((_num(total["value"]) or 0) - (_num(header["final_amount"]) or 0)) <= TOLERANCE,
                f"BUG: View Selected total {total['value']} does not match header Final Amount {header['final_amount']}",
            )
            if total.get("qty_pcs"):
                soft_assert.check_true(
                    _num(total["qty_pcs"]) == _num(header["qty_pcs"]),
                    f"BUG: View Selected Qty (pcs) {total['qty_pcs']} does not match header Qty (pcs) {header['qty_pcs']}",
                )


@allure.epic("Bill / New Invoice")
@allure.feature("Group filter")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Bill: 2 items -> Calculate -> Group1 filter -> the selected items stay at the top")
def test_group1_filter_keeps_selected_items_on_top(logged_in_driver, soft_assert):
    page = _open(logged_in_driver)

    with step(page, "Add 2 in-stock items and Calculate"):
        codes = _add_items(page, 2)
        page.click_calc()

    with step(page, "Open Group1 and choose a filter option"):
        options = page.group1_options()
        assert options, "Group1 has no options to choose"
        value, text = options[0]
        shown = page.select_group1(value)

    with step(page, "The selected items should be at the top of the filtered list"):
        top = page.row_codes(limit=len(codes))
        allure.attach(f"Group1 option={shown}\nselected items={codes}\ntop rows={top}",
                      name="top_rows_after_filter", attachment_type=allure.attachment_type.TEXT)
        top_codes = [c for _, c, _ in top]
        soft_assert.check_true(
            sorted(top_codes) == sorted(codes),
            f"BUG: after choosing Group1 '{shown}' the selected items {codes} are not at the top -- top rows are {top_codes}",
        )
        wrong_qty = [(c, q) for _, c, q in top if c in codes and _num(q) != QTY]
        soft_assert.check_true(not wrong_qty, f"BUG: selected items lost their qty after the filter: {wrong_qty}")
