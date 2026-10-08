"""Unit type (Piece / Carton) must carry over from the sale to Sale Return 'With Reference'.

  Scenario 1: sale with 2 items, both unit Piece  -> invoice vs DB -> Sale Return With Reference ->
              same order -> Select All -> both items show unit Piece
  Scenario 2: sale with item 1 = Piece, item 2 = Carton -> invoice vs DB -> Sale Return With Reference ->
              same order -> Select All -> item 1 Piece, item 2 Carton (as on the sale)
"""
import re
import time

import allure
import pytest
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from pages.bill_unit_apply_page import BillUnitApplyPage
from pages.my_sale_page import MySalePage
from pages.sale_return_page import SaleReturnPage
from utilities.allure_utils import step
from utilities.db import get_order_header, get_order_products
from utilities.invoice_pdf import extract_line_item_count, extract_payable_amount, fetch_invoice_text

CUSTOMER_NAME = "Demo Dealer 4"
QTY = 1
TOLERANCE = 1.0


def _num(value):
    match = re.search(r"-?\d+(?:\.\d+)?", str(value or "").replace(",", ""))
    return float(match.group()) if match else None


def _close(a, b):
    a, b = _num(a), _num(b)
    return a is not None and b is not None and abs(a - b) <= TOLERANCE


def _unit_kind(text):
    t = (text or "").strip().lower()
    if t.startswith("cart"):
        return "carton"
    if t.startswith("pi") or t.startswith("pc"):
        return "piece"
    return t or None


def _norm(name):
    return re.sub(r"\s+", " ", (name or "")).strip().lower()


# ------------------------------------------------------------------ sale with chosen unit types

def _pick_items(page, units):
    """Pick distinct in-stock rows that have a Carton/Piece dropdown; an item that will be sold
    by Carton must have more than 1 piece per carton (so Carton and Piece really differ)."""
    picked, used = [], set()

    def _scan():
        for i in range(min(len(page.find_all(page.PRODUCT_ROWS)), 60)):
            if len(picked) == len(units) or i in used:
                continue
            try:
                info = page.product_row(i)
            except Exception:
                continue
            if info["available_stock"] < QTY or page._unit_select(i) is None:
                continue
            want = units[len(picked)]
            per_carton = page.pieces_per_carton(info["display_name"]) or 0
            if want == "carton" and per_carton <= 1:
                continue
            picked.append({"row": i, "unit": want, "name": info["display_name"],
                           "item_code": info["item_code"], "pieces_per_carton": per_carton})
            used.add(i)

    _scan()
    if len(picked) < len(units):
        page.show_all_products()
        _scan()
    if len(picked) < len(units):
        raise AssertionError(f"Could not find {len(units)} suitable in-stock items for units {units}: {picked}")
    return picked


def _create_sale_with_units(driver, soft_assert, units, tag):
    """Bill/New Invoice -> items with the given unit types (qty 1) -> Save -> Add Sale -> Proceed ->
    invoice. Returns {order_id, items, summary, payable, invoice_text}."""
    my_sales = MySalePage(driver)
    try:
        baseline = my_sales.open().get_latest_invoice_id(CUSTOMER_NAME)
    except Exception:
        baseline = None

    page = BillUnitApplyPage(driver)
    with step(page, f"Bill/New Invoice: select '{CUSTOMER_NAME}' and add {len(units)} items with units {units}"):
        page.open()
        page.select_customer(CUSTOMER_NAME)
        items = _pick_items(page, units)
        for item in items:
            item["unit_label"] = page.set_unit(item["row"], item["unit"])
            page.enter_quantity(item["row"], QTY)
            shown = _unit_kind(page.current_unit(item["row"]))
            soft_assert.check_equal(shown, item["unit"], f"Sale: unit selected for {item['name']!r}")
        allure.attach(str(items), name=f"{tag}_sale_items", attachment_type=allure.attachment_type.TEXT)

    with step(page, "Calculate, Save and create the order (Add Sale -> Yes! Proceed.)"):
        page.click_calc()
        summary = page.get_summary()
        allure.attach(str(summary), name=f"{tag}_calc", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_equal(summary["total_item"], str(len(units)), "Sale: Calc Total Item")
        page.click_save()
        payable = page.get_payable_amount()
        page.click_add_sale()
        confirm = page.get_confirm_sale_details()
        allure.attach(str(confirm), name=f"{tag}_confirm_sale", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_equal(confirm.get("No Of Items"), str(len(units)), "Sale: Confirm Sale No Of Items")
        page.confirm_sale_proceed()
        page.wait_for_sale_completed()

    with step(page, "Read the invoice"):
        invoice_url, png = page.generate_invoice_and_get_url()
        allure.attach(png, name=f"{tag}_invoice", attachment_type=allure.attachment_type.PNG)
        invoice_text = fetch_invoice_text(driver, invoice_url)
        allure.attach(f"URL: {invoice_url}\n\n{invoice_text[:3000]}", name=f"{tag}_invoice_text",
                      attachment_type=allure.attachment_type.TEXT)

    order_id = None
    m = re.search(r"OrderId=(\d+)", invoice_url, flags=re.IGNORECASE)
    if m:
        order_id = int(m.group(1))
    else:
        row = my_sales.open().get_latest_sale_for_client(CUSTOMER_NAME, exclude_invoice_ids={baseline})
        if row:
            head = row["invoice_id"].split("/")[0].strip()
            order_id = int(head) if head.isdigit() else None
    allure.attach(str(order_id), name=f"{tag}_order_id", attachment_type=allure.attachment_type.TEXT)
    return {"order_id": order_id, "items": items, "summary": summary, "payable": payable, "invoice_text": invoice_text}


def _verify_invoice_with_db(soft_assert, sale, tag):
    with allure.step("Verify the invoice against the database"):
        text = sale["invoice_text"]
        inv_payable = extract_payable_amount(text)
        inv_lines = extract_line_item_count(text)
        try:
            header = get_order_header(sale["order_id"])
            products = get_order_products(sale["order_id"])
        except Exception as exc:
            soft_assert.check(False, f"DB verification failed: {exc}")
            return
        allure.attach(
            f"DB header: {header}\n\nDB products:\n" + "\n".join(str(p) for p in products) +
            f"\n\nInvoice payable={inv_payable} lines={inv_lines}",
            name=f"{tag}_invoice_vs_db", attachment_type=allure.attachment_type.TEXT,
        )
        soft_assert.check_true(header is not None, f"DB: order {sale['order_id']} should exist")
        if header is None:
            return
        n = len(sale["items"])
        soft_assert.check_equal(int(float(header["NoOfProducts"])), n, "DB: NoOfProducts")
        soft_assert.check_equal(len(products), n, "DB: order product rows")
        soft_assert.check_true(
            inv_payable is not None and _close(inv_payable, header["Order_Amt"]),
            f"Invoice Payable ({inv_payable}) should match DB Order_Amt ({header['Order_Amt']})",
        )
        if inv_lines:
            soft_assert.check_equal(inv_lines, n, "Invoice line items vs DB NoOfProducts")
        db_names = " | ".join(_norm(str(p.get("Product_Name", ""))) for p in products)
        for item in sale["items"]:
            base = _norm(item["name"].split("[")[0])
            soft_assert.check_true(base in db_names, f"DB order products should include {item['name']!r}")


# ------------------------------------------------------------------ Sale Return With Reference + Select All

SELECT_ALL_XPATH = (
    "//input[@type='button' or @type='submit'][translate(normalize-space(@value),'SELCTA','selcta')='select all']"
    " | //*[self::button or self::a or self::span or self::label][translate(normalize-space(.),'SELCTA','selcta')='select all']"
    " | //input[contains(@class,'btnSelectAllProduct')]"
)


def _click_select_all(page):
    for el in page.driver.find_elements(By.XPATH, SELECT_ALL_XPATH):
        try:
            if el.is_displayed():
                page.js_click(el)
                time.sleep(2)
                return True
        except StaleElementReferenceException:
            continue
    return False


def _units_in(container_rows):
    """{normalized product name: (unit kind, unit text, qty)} read from table rows."""
    found = {}
    for tr in container_rows:
        try:
            if not tr.is_displayed():
                continue
            text = tr.text
            name_el = tr.find_elements(By.CSS_SELECTOR, "span.Variant_Name")
            name = (name_el[0].get_attribute("product_name") or name_el[0].text) if name_el else text.split("\n")[0]
            unit_text = None
            for sel in tr.find_elements(By.TAG_NAME, "select"):
                opts = [o.text.strip().lower() for o in sel.find_elements(By.TAG_NAME, "option")]
                if any(o.startswith("cart") for o in opts):
                    unit_text = Select(sel).first_selected_option.text.strip()
                    break
            if unit_text is None:
                m = re.search(r"\b(cartons?|pieces?|pcs|piec\w*)\b", text, flags=re.IGNORECASE)
                unit_text = m.group(1) if m else None
            qty = None
            for inp in tr.find_elements(By.CSS_SELECTOR, "input.C1, input.qty, input.SaleQty"):
                if (inp.get_attribute("value") or "").strip():
                    qty = inp.get_attribute("value").strip()
                    break
            found[_norm(name)] = (_unit_kind(unit_text), unit_text, qty)
        except StaleElementReferenceException:
            continue
    return found


def _check_units_after_select_all(driver, soft_assert, sale, tag):
    page = SaleReturnPage(driver)
    with step(page, f"Sale Return -> With Reference -> '{CUSTOMER_NAME}' -> select order {sale['order_id']}"):
        if sale["order_id"] is None:
            pytest.fail("Could not determine the new sale's order id (invoice URL / My Sales)")
        invoice = page.open_with_reference_and_select_invoice(CUSTOMER_NAME, sale["order_id"])
        allure.attach(str(invoice), name=f"{tag}_reference_invoice", attachment_type=allure.attachment_type.TEXT)

    with step(page, "Click Select All"):
        clicked = _click_select_all(page)
        soft_assert.check_true(clicked, "A 'Select All' control should be available on the With Reference return")
        # Units may be shown in a Select All popup or directly in the return grid -- read both.
        popup_rows = []
        for box in driver.find_elements(By.CSS_SELECTOR, ".jconfirm-box, .modal-content"):
            try:
                if box.is_displayed():
                    popup_rows += box.find_elements(By.CSS_SELECTOR, "tbody tr")
            except StaleElementReferenceException:
                continue
        popup_units = _units_in(popup_rows)
        grid_units = _units_in(driver.find_elements(*page.PRODUCT_ROWS))
        allure.attach(f"Select All popup: {popup_units}\n\nReturn grid: {grid_units}",
                      name=f"{tag}_units_after_select_all", attachment_type=allure.attachment_type.TEXT)

    with step(page, "Each item's unit type matches the sale"):
        for item in sale["items"]:
            key = _norm(item["name"])
            seen = popup_units.get(key) or grid_units.get(key)
            if seen is None:  # names can be truncated -- fall back to a prefix match
                base = _norm(item["name"].split("[")[0])
                seen = next((v for k, v in {**grid_units, **popup_units}.items() if k.startswith(base)), None)
            if seen is None:
                soft_assert.check(False, f"{item['name']!r} was not found in the return after Select All")
                continue
            kind, text, qty = seen
            soft_assert.check_true(
                kind == item["unit"],
                f"ISSUE: {item['name']!r} was sold as '{item['unit_label']}' but after Select All the return "
                f"shows unit '{text}'",
            )
            if qty is not None:
                soft_assert.check_true(
                    _num(qty) == QTY,
                    f"{item['name']!r}: return qty after Select All is {qty!r}, sold qty was {QTY} {item['unit_label']}",
                )


# ------------------------------------------------------------------ the two scenarios

@allure.epic("Sale Return")
@allure.feature("Unit type carried from sale to return")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Sale with 2 items as Piece -> invoice vs DB -> Sale Return With Reference -> Select All -> both still Piece")
def test_unit_piece_piece_carried_to_return(logged_in_driver, soft_assert):
    sale = _create_sale_with_units(logged_in_driver, soft_assert, ["piece", "piece"], "PP")
    _verify_invoice_with_db(soft_assert, sale, "PP")
    _check_units_after_select_all(logged_in_driver, soft_assert, sale, "PP")


@allure.epic("Sale Return")
@allure.feature("Unit type carried from sale to return")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Sale with item 1 as Piece and item 2 as Carton -> invoice vs DB -> Sale Return With Reference -> Select All -> Piece and Carton as on the sale")
def test_unit_piece_carton_carried_to_return(logged_in_driver, soft_assert):
    sale = _create_sale_with_units(logged_in_driver, soft_assert, ["piece", "carton"], "PC")
    _verify_invoice_with_db(soft_assert, sale, "PC")
    _check_units_after_select_all(logged_in_driver, soft_assert, sale, "PC")
