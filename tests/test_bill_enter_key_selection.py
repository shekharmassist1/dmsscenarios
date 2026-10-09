import time

import allure
import pytest

from config.config import USERNAME, PASSWORD
from pages.bill_enter_key_page import BillEnterKeyPage
from pages.login_page import LoginPage
from utilities.helpers import take_screenshot
from utilities.menu_utils import verify_menu_or_skip

CUSTOMER_NAME = "Demo Dealer 4"
TARGET_PAGES = (6, 7)   # the issue was seen on the 6th/7th page of the product grid
QTY = 1


def _num(value):
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


@allure.epic("DMS Application")
@allure.feature("Bill Management")
@allure.story("Selecting items with the ENTER key on later grid pages")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Bill/New Invoice: select 2 in-stock items on page 6/7 with ENTER -> both stay selected and the grid stays on that page")
@allure.description("""
    Expected (correct) behaviour -- this test PASSES once the app behaves like this:
    - Login, open Bill/New Invoice, select customer 'Demo Dealer 4'
    - Go to page 6 (or 7) of the product grid and pick two items that have inventory
    - Type a qty in the first item and press ENTER, then do the same for the second item
    - Both items stay selected (Calc Total Item = 2, both listed in View Selected Items)
    - The grid stays on the same page after each ENTER

    Known issues it reports today:
    - ISSUE 1: only one item can be selected at a time with ENTER (the previous one is lost)
    - ISSUE 2: after pressing ENTER the grid jumps back to page 1
""")
@allure.tag("regression", "bill", "keyboard")
def test_bill_enter_key_selects_multiple_items_on_later_page(driver):
    issues = []

    with allure.step("Step 1: Login to DMS"):
        LoginPage(driver).login(USERNAME, PASSWORD)
        time.sleep(5)
        take_screenshot(driver, "enterkey_01_login")

    with allure.step("Step 2: Verify Bill/New Invoice menu availability"):
        verify_menu_or_skip(driver, "Bill/New Invoice")

    page = BillEnterKeyPage(driver)

    with allure.step(f"Step 3: Open Bill/New Invoice and select '{CUSTOMER_NAME}'"):
        page.open()
        page.select_customer(CUSTOMER_NAME)
        take_screenshot(driver, "enterkey_02_customer_selected")

    with allure.step(f"Step 4: Go to page {TARGET_PAGES[0]} (or {TARGET_PAGES[1]}) and pick 2 items with inventory"):
        last_page = page.last_page_number()
        target_page, picked = None, []
        for candidate in TARGET_PAGES:
            if not page.go_to_page(candidate):
                continue
            in_stock = [r for r in page.rows_on_page() if r["stock"] >= QTY and r["item_code"]]
            if len(in_stock) >= 2:
                target_page, picked = candidate, in_stock[:2]
                break
        if target_page is None:
            pytest.fail(
                f"Setup: could not find 2 in-stock items on page {TARGET_PAGES[0]} or {TARGET_PAGES[1]} "
                f"(grid has {last_page} pages) -- not the bug itself, the test data needs checking"
            )
        item_a, item_b = picked
        allure.attach(
            f"page={target_page}\nitem A={item_a}\nitem B={item_b}",
            name="items_used", attachment_type=allure.attachment_type.TEXT,
        )
        take_screenshot(driver, f"enterkey_03_on_page_{target_page}")

    pages_after_enter = {}

    with allure.step(f"Step 5: Enter qty {QTY} for item A ({item_a['item_code']}) and press ENTER"):
        dialogs = page.enter_qty_and_press_enter(item_a["item_code"], QTY)
        pages_after_enter["after item A"] = page.current_page()
        take_screenshot(driver, "enterkey_04_after_enter_item_a")
        if dialogs:
            allure.attach(str(dialogs), name="dialogs_after_item_a", attachment_type=allure.attachment_type.TEXT)
        # Return to the target page so item B can still be tested even if the grid jumped.
        if pages_after_enter["after item A"] != target_page:
            page.go_to_page(target_page)

    with allure.step(f"Step 6: Enter qty {QTY} for item B ({item_b['item_code']}) and press ENTER"):
        dialogs = page.enter_qty_and_press_enter(item_b["item_code"], QTY)
        pages_after_enter["after item B"] = page.current_page()
        take_screenshot(driver, "enterkey_05_after_enter_item_b")
        if dialogs:
            allure.attach(str(dialogs), name="dialogs_after_item_b", attachment_type=allure.attachment_type.TEXT)

    with allure.step("Step 7: Check the grid stayed on the same page after ENTER (Issue 2)"):
        allure.attach(str(pages_after_enter), name="grid_page_after_each_enter", attachment_type=allure.attachment_type.TEXT)
        jumped = {when: p for when, p in pages_after_enter.items() if p != target_page}
        if jumped:
            issues.append(
                f"ISSUE 2: after pressing ENTER on page {target_page} the product grid jumped to another page "
                f"({', '.join(f'{w}: page {p}' for w, p in jumped.items())}) -- it should stay on page {target_page}"
            )

    with allure.step("Step 8: Check BOTH items are still selected (Issue 1)"):
        page.go_to_page(target_page)
        qty_a, qty_b = page.qty_of(item_a["item_code"]), page.qty_of(item_b["item_code"])
        total_item = page.calc_total_items()
        selected_codes = page.selected_item_codes()
        take_screenshot(driver, "enterkey_06_selection_check")
        summary = (
            f"item A {item_a['item_code']}: qty box={qty_a!r}\n"
            f"item B {item_b['item_code']}: qty box={qty_b!r}\n"
            f"Calc Total Item={total_item!r}\n"
            f"View Selected Items codes={selected_codes}"
        )
        allure.attach(summary, name="selection_after_enter", attachment_type=allure.attachment_type.TEXT)
        print(summary)

        lost = [code for code, q in ((item_a["item_code"], qty_a), (item_b["item_code"], qty_b)) if _num(q) != QTY]
        selected_ok = (_num(total_item) == 2) and not lost
        # View Selected lists SKU codes (e.g. FGIIJB020) while the grid label gives the barcode (8901...),
        # so only compare codes when they are in the same format; otherwise count the rows.
        if selected_codes and (item_a["item_code"] in selected_codes or item_b["item_code"] in selected_codes):
            selected_ok = selected_ok and item_a["item_code"] in selected_codes and item_b["item_code"] in selected_codes
        elif selected_codes:
            selected_ok = selected_ok and len(selected_codes) == 2
        if not selected_ok:
            issues.append(
                "ISSUE 1: selecting items with ENTER keeps only one item at a time -- "
                f"expected both {item_a['item_code']} and {item_b['item_code']} selected with qty {QTY}, "
                f"got Calc Total Item={total_item!r}, qty boxes A={qty_a!r} B={qty_b!r}, "
                f"View Selected={selected_codes}"
            )

    if issues:
        allure.attach("\n".join(issues), name="issues_found", attachment_type=allure.attachment_type.TEXT)
        pytest.fail("\n".join(issues))
