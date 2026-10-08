import time

import allure
import pytest

from config.config import USERNAME, PASSWORD
from pages.login_page import LoginPage
from pages.purchase_return_batch_page import PurchaseReturnBatchPage
from utilities.helpers import take_screenshot
from utilities.menu_utils import verify_menu_or_skip

SUPPLIER_NAME = "Vadilal Industries Ltd."
SUPPLIER_SUB_CATEGORY = "14"
ENTERED_QTY = 2          # entered in cartons; a carton -> pieces conversion makes this jump (e.g. 2 -> 24)
WAIT_BEFORE_APPLY = 2    # seconds to wait after opening the hamburger, as in the manual steps
MAX_ROWS_TO_CHECK = 15


def _to_number(value):
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _pick_row_with_batch_stock(page, min_qty):
    """First product row whose hamburger modal shows batch data with enough inventory.
    The modal is closed WITHOUT applying, so nothing changes while checking."""
    checked = []
    for i in range(min(page.row_count(), MAX_ROWS_TO_CHECK)):
        try:
            page.open_batch_modal(i)
            text = page.batch_modal_text()
            page.close_batch_modal()
        except Exception as exc:
            checked.append({"row": i, "error": str(exc)[:120]})
            continue
        total = page.batch_total(text)
        has_data = "no data available" not in text.lower()
        checked.append({"row": i, "has_data": has_data, "total": total})
        if has_data and (total is None or total >= min_qty):
            return i, checked
    raise AssertionError(f"No product row with batch inventory >= {min_qty} in the first rows: {checked}")


@allure.epic("DMS Application")
@allure.feature("purchage Return")
@allure.story("Hamburger Apply must keep the entered quantity")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Purchase Return: {field} qty must stay the same after hamburger Apply (not converted to pieces)")
@allure.description("""
    - Login to DMS
    - Open Purchase Return and select 'Vadilal Industries Ltd.' with Sub Category 14
    - Enter a quantity in the Saleable Item or Damage Item box
    - Click the hamburger menu, wait 2 seconds, click Apply
    - The entered quantity must be unchanged; if it changed (e.g. converted to pieces) it is an issue
""")
@allure.tag("regression", "purchasereturn")
@pytest.mark.parametrize("field", ["saleable", "damage"])
def test_purchase_return_apply_keeps_entered_qty(driver, field):
    other_field = "damage" if field == "saleable" else "saleable"
    issues = []

    with allure.step("Step 1: Login to DMS"):
        LoginPage(driver).login(USERNAME, PASSWORD)
        time.sleep(5)
        take_screenshot(driver, f"pr_apply_{field}_01_login")

    with allure.step("Step 2: Verify Purchase Return menu availability"):
        verify_menu_or_skip(driver, "Purchase Return")

    page = PurchaseReturnBatchPage(driver)

    with allure.step("Step 3: Open Purchase Return"):
        page.open()
        take_screenshot(driver, f"pr_apply_{field}_02_purchase_return")

    with allure.step(f"Step 4: Select '{SUPPLIER_NAME}' with Sub Category {SUPPLIER_SUB_CATEGORY}"):
        page.select_supplier(SUPPLIER_NAME, sub_category=SUPPLIER_SUB_CATEGORY)
        take_screenshot(driver, f"pr_apply_{field}_03_supplier")

    with allure.step(f"Step 5: Pick a product with at least {ENTERED_QTY} in batch inventory"):
        row, checked = _pick_row_with_batch_stock(page, ENTERED_QTY)
        product = page.product_name(row)
        allure.attach(str(checked), name="rows_checked", attachment_type=allure.attachment_type.TEXT)
        print(f"Using row {row}: {product}")

    with allure.step(f"Step 6: Enter {ENTERED_QTY} in the {field.title()} Item box"):
        page.enter_qty(row, field, ENTERED_QTY)
        before = page.get_qty(row, field)
        other_before = page.get_qty(row, other_field)
        print(f"Before Apply -> {field}={before!r} {other_field}={other_before!r}")
        take_screenshot(driver, f"pr_apply_{field}_04_qty_entered")
        if _to_number(before) != ENTERED_QTY:
            issues.append(f"The {field} box should show {ENTERED_QTY} before Apply, shows {before!r}")

    with allure.step(f"Step 7: Click hamburger, wait {WAIT_BEFORE_APPLY}s, click Apply"):
        page.open_batch_modal(row)
        time.sleep(WAIT_BEFORE_APPLY)
        allure.attach(page.batch_modal_text(), name="batch_modal_text", attachment_type=allure.attachment_type.TEXT)
        take_screenshot(driver, f"pr_apply_{field}_05_hamburger")
        alert = page.apply_batch_modal()
        if alert:
            allure.attach(alert, name="alert_after_apply", attachment_type=allure.attachment_type.TEXT)

    with allure.step(f"Step 8: Verify the {field.title()} Item qty is unchanged"):
        after = page.get_qty(row, field)
        other_after = page.get_qty(row, other_field)
        take_screenshot(driver, f"pr_apply_{field}_06_after_apply")
        summary = (
            f"product={product!r}\n"
            f"{field}: entered={ENTERED_QTY} before_apply={before!r} after_apply={after!r}\n"
            f"{other_field}: before_apply={other_before!r} after_apply={other_after!r}"
        )
        allure.attach(summary, name="quantities_before_vs_after_apply", attachment_type=allure.attachment_type.TEXT)
        print(summary)

        after_num = _to_number(after)
        if after_num != ENTERED_QTY:
            hint = ""
            if after_num and after_num % ENTERED_QTY == 0:
                hint = f" -- looks converted to pieces ({ENTERED_QTY} x {after_num / ENTERED_QTY:g})"
            issues.append(
                f"ISSUE: after Apply the {field.title()} Item qty changed from {ENTERED_QTY} to {after!r}"
                f"{hint} (product {product!r})"
            )
        if _to_number(other_after or 0) != _to_number(other_before or 0):
            issues.append(
                f"After Apply the {other_field.title()} Item qty should not change: "
                f"was {other_before!r}, now {other_after!r} (product {product!r})"
            )

    if issues:
        pytest.fail("\n".join(issues))
