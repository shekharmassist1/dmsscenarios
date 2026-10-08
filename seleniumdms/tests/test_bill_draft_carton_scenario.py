"""Bill/New Invoice -> item with more than 1 piece per carton (sold by Carton) -> Calculate (header) ->
Save Draft -> Drafts list -> Order Again -> Calculate. The number of items, quantity, unit and price
must be the same in every place."""
import re

import allure
import pytest

from pages.bill_unit_apply_page import BillUnitApplyPage
from pages.draft_page import DraftPage
from utilities.allure_utils import step

CUSTOMER_NAME = "Demo Dealer 3"
pytestmark = pytest.mark.xdist_group(name="dd3")  # parallel runs: one group per customer, never shared

QTY = 1
TOLERANCE = 1.0


def _num(value):
    match = re.search(r"-?\d+(?:\.\d+)?", str(value or "").replace(",", ""))
    return float(match.group()) if match else None


def _close(a, b):
    a, b = _num(a), _num(b)
    return a is not None and b is not None and abs(a - b) <= TOLERANCE


def _row_index_by_code(page, item_code):
    for i in range(len(page.find_all(page.PRODUCT_ROWS))):
        try:
            if page.product_row(i)["item_code"] == item_code:
                return i
        except Exception:
            continue
    return None


def _snapshot(page, row):
    """Calc header + View Selected Items + the item's qty box and unit, as one dict."""
    page.click_calc()
    summary = page.get_summary()
    page.open_view_selected_items()
    items, vsi_total = page.get_selected_items()
    page.close_selected_items()
    info = page.product_row(row)
    return {
        "header": summary,
        "view_selected": items,
        "view_selected_total": vsi_total,
        "qty_box": (info["qty_input"].get_attribute("value") or "").strip(),
        "unit": page.current_unit(row),
        "row_price": info["price"],
    }


@allure.epic("Bill / New Invoice")
@allure.feature("Drafts")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Bill: item with >1 piece per carton (Carton) -> Calculate -> Save Draft -> Drafts list -> Order Again -> items and price unchanged")
def test_carton_item_draft_and_order_again_keep_items_and_price(logged_in_driver, soft_assert):
    page = BillUnitApplyPage(logged_in_driver)

    with step(page, f"Open Bill/New Invoice and select '{CUSTOMER_NAME}'"):
        page.open()
        page.select_customer(CUSTOMER_NAME)

    with step(page, "Add an in-stock item with more than 1 piece in a carton (unit Carton, qty 1)"):
        row, info = page.find_row_with_multi_piece_carton()
        code = info["item_code"]
        unit_label = page.set_unit(row, "carton")
        page.enter_quantity(row, QTY)
        allure.attach(
            f"product={info['display_name']}\nitem code={code}\npieces per carton={info['pieces_per_carton']}\n"
            f"unit={unit_label}\nqty={QTY}\nrow price={info['price']}",
            name="item_used", attachment_type=allure.attachment_type.TEXT,
        )

    with step(page, "Click Calculate (header) and View Selected Items -- before draft"):
        before = _snapshot(page, row)
        allure.attach(str(before), name="before_draft", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_equal(before["header"]["total_item"], "1", "Before draft: header Total Item")
        soft_assert.check_equal(len(before["view_selected"]), 1, "Before draft: View Selected Items count")
        if before["view_selected_total"] is not None:
            soft_assert.check_true(
                _close(before["view_selected_total"]["value"], before["header"]["final_amount"]),
                f"Before draft: View Selected total ({before['view_selected_total']['value']}) should match header "
                f"Final Amount ({before['header']['final_amount']})",
            )

    with step(page, "Save to Draft"):
        page.click_save_draft()
        alert = page.get_draft_alert_text()
        allure.attach(alert, name="draft_alert", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_true("draft saved successfully" in alert.lower(), f"Draft alert text unexpected: {alert!r}")
        page.confirm_draft_alert()

    drafts = DraftPage(logged_in_driver)
    with step(page, "Drafts list: the new draft shows the same number of items and amount"):
        drafts.open()
        draft = drafts.get_latest_draft_for_client(CUSTOMER_NAME)
        allure.attach(str(draft), name="draft_row", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_true(draft is not None, "A draft row should exist after saving")
        if draft is not None:
            soft_assert.check_equal(draft["no_of_items"], "1", "Drafts list: No. Of Items")
            soft_assert.check_true(
                _close(draft["draft_amount"], before["header"]["final_amount"]),
                f"Drafts list: Draft Amt ({draft['draft_amount']}) should match header Final Amount "
                f"({before['header']['final_amount']})",
            )
            soft_assert.check_true(
                _close(draft.get("draft_qty"), before["header"]["qty_pcs"]),
                f"Drafts list: Draft Qty ({draft.get('draft_qty')}) should match header Qty (pcs) "
                f"({before['header']['qty_pcs']})",
            )

    with step(page, "Go to the order again (Order Again)"):
        drafts.order_again_for_client(CUSTOMER_NAME)
        page.wait_for_grid_loaded()
        row_again = _row_index_by_code(page, code)
        soft_assert.check_true(row_again is not None, f"Item {code} should be in the reopened order")

    if row_again is not None:
        with step(page, "Click Calculate (header) and View Selected Items -- after Order Again"):
            after = _snapshot(page, row_again)
            allure.attach(str(after), name="after_order_again", attachment_type=allure.attachment_type.TEXT)

        with step(page, "Compare: number of items, qty, unit and price are unchanged"):
            hb, ha = before["header"], after["header"]
            soft_assert.check_equal(ha["total_item"], hb["total_item"], "Order Again: header Total Item")
            soft_assert.check_true(
                _close(ha["final_amount"], hb["final_amount"]),
                f"ISSUE: price changed after Order Again -- Final Amount {hb['final_amount']} -> {ha['final_amount']}",
            )
            soft_assert.check_true(
                _close(ha["amount"], hb["amount"]),
                f"ISSUE: Amount changed after Order Again -- {hb['amount']} -> {ha['amount']}",
            )
            soft_assert.check_true(
                _close(ha["qty_pcs"], hb["qty_pcs"]),
                f"ISSUE: Qty (pcs) changed after Order Again -- {hb['qty_pcs']} -> {ha['qty_pcs']}",
            )
            soft_assert.check_true(
                _num(after["qty_box"]) == _num(before["qty_box"]),
                f"ISSUE: item qty changed after Order Again -- {before['qty_box']} -> {after['qty_box']} "
                f"(looks converted to pieces if it equals {QTY} x {info['pieces_per_carton']})",
            )
            soft_assert.check_true(
                (after["unit"] or "").lower()[:4] == (before["unit"] or "").lower()[:4],
                f"ISSUE: unit changed after Order Again -- {before['unit']!r} -> {after['unit']!r}",
            )
            soft_assert.check_true(
                _close(after["row_price"], before["row_price"]),
                f"ISSUE: item rate changed after Order Again -- {before['row_price']} -> {after['row_price']}",
            )
            soft_assert.check_equal(len(after["view_selected"]), len(before["view_selected"]),
                                    "Order Again: View Selected Items count")
            if before["view_selected"] and after["view_selected"]:
                b, a = before["view_selected"][0], after["view_selected"][0]
                soft_assert.check_true(
                    _close(a["value"], b["value"]),
                    f"ISSUE: View Selected line value changed -- {b['value']} -> {a['value']}",
                )
                soft_assert.check_equal(a["qty"], b["qty"], "Order Again: View Selected qty")
