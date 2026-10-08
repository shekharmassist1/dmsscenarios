import re
import time

import allure
import pytest

from config.config import USERNAME, PASSWORD
from pages.login_page import LoginPage
from pages.sale_return_cart_page import SaleReturnCartPage, to_number
from utilities.helpers import take_screenshot
from utilities.menu_utils import verify_menu_or_skip

CUSTOMER_NAME = "Demo Dealer 4"
QTY = 1
AMOUNT_TOLERANCE = 1.0   # rupees; allows for rounding between the header and the popup


def _login_and_open_without_reference(driver, tag):
    with allure.step("Login to DMS"):
        LoginPage(driver).login(USERNAME, PASSWORD)
        time.sleep(5)
        take_screenshot(driver, f"{tag}_01_login")
    with allure.step("Verify Sale Return menu availability"):
        verify_menu_or_skip(driver, "Sale Return")
    page = SaleReturnCartPage(driver)
    with allure.step(f"Open Sale Return, select '{CUSTOMER_NAME}', choose Without Reference"):
        page.open()
        page.select_customer(CUSTOMER_NAME)
        page.choose_without_reference()
        take_screenshot(driver, f"{tag}_02_without_reference_grid")
    return page


def _check_header_vs_view_selected(page, driver, expected_items, removed_items, label, tag):
    """Click Calc and open View Selected Items, then compare them with each other and with what is
    actually in the cart. Returns (header, view_selected, issues)."""
    issues = []
    with allure.step(f"{label}: Calc header vs View Selected Items"):
        header = page.calculate()
        take_screenshot(driver, f"{tag}_calc_header")
        vsi = page.view_selected_items()
        take_screenshot(driver, f"{tag}_view_selected")

        rows = vsi["rows"]
        row_sum = round(sum(r["value"] or 0 for r in rows), 2)
        vsi_total = vsi["footer_total"] if vsi["footer_total"] is not None else row_sum
        final_amt, amount = to_number(header["final_amount"]), to_number(header["amount"])
        expected_names = [i["name"] for i in expected_items]
        removed_names = [i["name"] for i in removed_items]

        allure.attach(
            f"expected items ({len(expected_names)}): {expected_names}\n"
            f"removed items: {removed_names}\n\n"
            f"Calc header: Total Item={header['total_item']!r} Amount={header['amount']!r} "
            f"Final Amount={header['final_amount']!r}\n\n"
            f"View Selected rows ({len(rows)}):\n" + "\n".join(r["text"] for r in rows) +
            f"\nView Selected row sum={row_sum} footer total={vsi['footer_total']}",
            name=f"{label} - details", attachment_type=allure.attachment_type.TEXT,
        )

        if to_number(header["total_item"]) != len(expected_items):
            issues.append(f"{label}: Calc header Total Item is {header['total_item']!r}, expected {len(expected_items)}")
        if len(rows) != len(expected_items):
            issues.append(f"{label}: View Selected Items lists {len(rows)} item(s), expected {len(expected_items)}")

        all_text = "\n".join(r["text"].lower() for r in rows)
        for name in removed_names:
            if name and name.lower() in all_text:
                issues.append(f"{label}: removed item {name!r} still appears in View Selected Items")
        for name in expected_names:
            if name and name.lower() not in all_text:
                issues.append(f"{label}: item {name!r} is missing from View Selected Items")

        if vsi["footer_total"] is not None and rows and abs(row_sum - vsi["footer_total"]) > AMOUNT_TOLERANCE:
            issues.append(
                f"{label}: View Selected rows add up to {row_sum} but its total shows {vsi['footer_total']}"
            )
        header_values = [v for v in (final_amt, amount) if v is not None]
        if header_values and not any(abs(vsi_total - v) <= AMOUNT_TOLERANCE for v in header_values):
            issues.append(
                f"{label}: amount mismatch -- View Selected total is {vsi_total} but Calc header shows "
                f"Amount={header['amount']!r} / Final Amount={header['final_amount']!r}"
            )
    return header, vsi, issues


def _receive_goods_and_print_credit_note(page, driver, expected_count, header, tag):
    """Save -> Goods Receive -> 'Yes! Proceed.' -> OK -> Return Details -> hover Action -> Print ->
    credit note. Checks the confirmation dialog and the new Return Details row against the Calc
    header. Returns a list of issues (an app error stops the flow and is reported as an issue)."""
    issues = []
    final_amt = to_number(header["final_amount"])

    with allure.step("Save"):
        opened, alerts = page.save()
        take_screenshot(driver, f"{tag}_save")
        if alerts:
            allure.attach(str(alerts), name="alerts_after_save", attachment_type=allure.attachment_type.TEXT)
        if not opened:
            return issues + [f"Save did not open the Goods Receive panel (alerts: {alerts})"]

    with allure.step("Goods Receive -> Yes! Proceed. -> OK"):
        try:
            result = page.receive_goods_and_confirm()
        except AssertionError as exc:
            take_screenshot(driver, f"{tag}_receive_error")
            return issues + [str(exc)]
        take_screenshot(driver, f"{tag}_received")
        allure.attach(
            f"Confirmation dialog:\n{result['confirm_text']}\n\nResult dialog:\n{result['result_text']}",
            name="goods_receive_dialogs", attachment_type=allure.attachment_type.TEXT,
        )
        m = re.search(r"No\.?\s*Of\s*Items\s*:?\s*(\d+)", result["confirm_text"], flags=re.IGNORECASE)
        if m and int(m.group(1)) != expected_count:
            issues.append(
                f"Goods Receive confirmation shows No Of Items {m.group(1)}, but {expected_count} items are in the cart"
            )
        m = re.search(r"Total\s*value\s*:?\s*([\d,]+(?:\.\d+)?)", result["confirm_text"], flags=re.IGNORECASE)
        if m and final_amt is not None and abs(to_number(m.group(1)) - final_amt) > AMOUNT_TOLERANCE:
            issues.append(
                f"Goods Receive confirmation shows Total value {m.group(1)}, but the Calc header Final Amount is "
                f"{header['final_amount']!r}"
            )
        low = result["result_text"].lower()
        if "success" not in low and "received" not in low:
            issues.append(f"After 'Yes! Proceed.' the result dialog did not say it succeeded: {result['result_text']!r}")

    with allure.step("Return Details page opens"):
        try:
            url = page.wait_for_return_details_page()
        except Exception as exc:
            take_screenshot(driver, f"{tag}_no_return_details")
            return issues + [f"Return Details page did not open after OK: {exc}"]
        row = page.newest_return_row()
        take_screenshot(driver, f"{tag}_return_details")
        allure.attach(f"URL: {url}\nNewest row: {row}", name="return_details_newest_row",
                      attachment_type=allure.attachment_type.TEXT)

        party = page.column(row, "Party Name") or row.get("_text", "")
        if CUSTOMER_NAME.lower() not in party.lower():
            issues.append(f"Newest Return Details row is not for {CUSTOMER_NAME!r}: Party Name {party!r}")

        items_cell = page.column(row, "No. Of Items", "No Of Items")
        if items_cell is not None and to_number(items_cell) != expected_count:
            issues.append(
                f"Return Details shows No. Of Items {items_cell!r}, but {expected_count} items were returned"
            )

        amount_cell = page.column(row, "Amount")
        if amount_cell is not None and final_amt is not None and abs((to_number(amount_cell) or 0) - final_amt) > AMOUNT_TOLERANCE:
            issues.append(
                f"Return Details shows Amount {amount_cell!r}, but the Calc header Final Amount was "
                f"{header['final_amount']!r}"
            )

    with allure.step("Hover Action -> Print -> credit note opens"):
        try:
            note = page.print_first_return_credit_note()
        except Exception as exc:
            take_screenshot(driver, f"{tag}_print_failed")
            return issues + [f"Credit note did not open from Return Details (Action -> Print): {exc}"]
        allure.attach(note["screenshot"], name="credit_note", attachment_type=allure.attachment_type.PNG)
        allure.attach(f"URL: {note['url']}\nTitle: {note['title']}", name="credit_note_url",
                      attachment_type=allure.attachment_type.TEXT)
        if not note["url"] or note["url"] == "about:blank":
            issues.append("Credit note tab opened but stayed blank")

    return issues


@allure.epic("DMS Application")
@allure.feature("Sale Return")
@allure.story("Remove an item: Calc header and View Selected Items must agree")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Sale Return (Without Reference, Demo Dealer 4): select 3, remove 1 -> Calc header = View Selected -> Save -> Goods Receive -> Return Details -> credit note")
@allure.tag("regression", "salereturn")
def test_salereturn_select_three_remove_one_header_matches_view_selected(driver):
    issues = []
    page = _login_and_open_without_reference(driver, "sr_remove_3")

    with allure.step("Select 3 items (qty 1 each)"):
        items = page.pick_rows(3)
        for item in items:
            page.set_saleable_qty(item["variant_id"], QTY)
        allure.attach(str(items), name="items_selected", attachment_type=allure.attachment_type.TEXT)
        take_screenshot(driver, "sr_remove_3_03_three_selected")

    with allure.step("Calc with 3 items (baseline)"):
        before = page.calculate()
        allure.attach(str(before), name="calc_with_3_items", attachment_type=allure.attachment_type.TEXT)

    removed = items[2]
    with allure.step(f"Remove one item ({removed['name']})"):
        page.set_saleable_qty(removed["variant_id"], "")
        take_screenshot(driver, "sr_remove_3_04_one_removed")

    header, _vsi, found = _check_header_vs_view_selected(
        page, driver, items[:2], [removed], "After removing 1 of 3", "sr_remove_3_05"
    )
    issues += found

    before_amt, after_amt = to_number(before["final_amount"]), to_number(header["final_amount"])
    if before_amt is not None and after_amt is not None and not after_amt < before_amt:
        issues.append(
            f"After removing an item the Final Amount should go down: was {before['final_amount']!r} "
            f"with 3 items, now {header['final_amount']!r}"
        )

    issues += _receive_goods_and_print_credit_note(page, driver, 2, header, "sr_remove_3_06")

    if issues:
        allure.attach("\n".join(issues), name="issues_found", attachment_type=allure.attachment_type.TEXT)
        pytest.fail("\n".join(issues))


@allure.epic("DMS Application")
@allure.feature("Sale Return")
@allure.story("Remove an item, Save, close the popup, add an item: Calc header and View Selected Items must agree")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Sale Return (Without Reference, Demo Dealer 4): select 5, remove 1, Save, close, add 1 -> Calc header = View Selected -> Save -> Goods Receive -> Return Details -> credit note")
@allure.tag("regression", "salereturn")
def test_salereturn_five_remove_save_close_add_header_matches_view_selected(driver):
    issues = []
    page = _login_and_open_without_reference(driver, "sr_remove_5")

    with allure.step("Select 5 items (qty 1 each)"):
        items = page.pick_rows(5)
        for item in items:
            page.set_saleable_qty(item["variant_id"], QTY)
        allure.attach(str(items), name="items_selected", attachment_type=allure.attachment_type.TEXT)
        take_screenshot(driver, "sr_remove_5_03_five_selected")

    removed = items[4]
    kept = items[:4]
    with allure.step(f"Remove one item ({removed['name']})"):
        page.set_saleable_qty(removed["variant_id"], "")
        take_screenshot(driver, "sr_remove_5_04_one_removed")

    with allure.step("Calc with 4 items (baseline before Save)"):
        before_save = page.calculate()
        allure.attach(str(before_save), name="calc_with_4_items", attachment_type=allure.attachment_type.TEXT)

    with allure.step("Click Save"):
        opened, alerts = page.save()
        take_screenshot(driver, "sr_remove_5_05_after_save")
        if alerts:
            allure.attach(str(alerts), name="alerts_after_save", attachment_type=allure.attachment_type.TEXT)
        if not opened:
            issues.append(f"Save did not open the Receive Goods step (alerts: {alerts})")

    with allure.step("Close the popup without receiving the goods"):
        how = page.close_popup()
        allure.attach(how, name="how_popup_was_closed", attachment_type=allure.attachment_type.TEXT)
        take_screenshot(driver, "sr_remove_5_06_popup_closed")
        if how == "popup still open":
            pytest.fail("Setup: could not close the popup after Save, so an item can't be added -- "
                        "send me a screenshot of that popup so the test can close it correctly")

    with allure.step("Check the 4 kept items still have their qty after Save + close"):
        for item in kept:
            q = page.saleable_qty(item["variant_id"])
            if to_number(q) != QTY:
                issues.append(f"After Save + closing the popup, {item['name']!r} qty is {q!r}, expected {QTY}")

    with allure.step("Add one more item (qty 1)"):
        (added,) = page.pick_rows(1, exclude_variants=[i["variant_id"] for i in items])
        page.set_saleable_qty(added["variant_id"], QTY)
        allure.attach(str(added), name="item_added", attachment_type=allure.attachment_type.TEXT)
        take_screenshot(driver, "sr_remove_5_07_one_added")

    header, _vsi, found = _check_header_vs_view_selected(
        page, driver, kept + [added], [removed], "After remove 1, Save, close, add 1", "sr_remove_5_08"
    )
    issues += found

    base_amt, after_amt = to_number(before_save["final_amount"]), to_number(header["final_amount"])
    if base_amt is not None and after_amt is not None and not after_amt > base_amt:
        issues.append(
            f"After adding an item the Final Amount should go up: was {before_save['final_amount']!r} "
            f"with 4 items, now {header['final_amount']!r}"
        )

    issues += _receive_goods_and_print_credit_note(page, driver, 5, header, "sr_remove_5_09")

    if issues:
        allure.attach("\n".join(issues), name="issues_found", attachment_type=allure.attachment_type.TEXT)
        pytest.fail("\n".join(issues))
