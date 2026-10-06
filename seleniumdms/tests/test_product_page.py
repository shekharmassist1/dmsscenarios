import re

import allure

from pages.product_page import ProductPage
from pages.draft_page import DraftPage
from utilities.allure_utils import step

CUSTOMER_NAME = "Demo Dealer 4"
QUANTITIES = {0: 2, 1: 3}


def _to_float(value):
    return float(re.sub(r"[^0-9.\-]", "", value) or 0)


@allure.epic("Bill / New Invoice")
@allure.feature("Product Page")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Enter products -> Calc -> View Selected Items -> Print -> Save Draft")
@allure.description(
    "Selects customer 'Demo Dealer 4', enters quantities for two products, and cross-checks the Calc "
    "summary, the View Selected Items overview, the Print Preview modal, and the saved draft "
    "(verified in the drafts list) against each other. Soft assertions are used so every check "
    "runs and all failures are reported together instead of stopping at the first one."
)
def test_product_entry_calc_print_draft_view_selected(logged_in_driver, soft_assert):
    page = ProductPage(logged_in_driver)

    with step(page, f"Open product page and select customer '{CUSTOMER_NAME}'"):
        try:
            page.open()
            page.select_customer(CUSTOMER_NAME)
        except Exception as exc:
            soft_assert.check(False, f"Setup (open product page / select customer '{CUSTOMER_NAME}') failed: {exc}")
            return

    entered_codes = {}
    with step(page, "Enter quantities for two products"):
        try:
            for row_index, qty in QUANTITIES.items():
                code = page.enter_quantity(row_index, qty)
                entered_codes[code] = qty
            allure.attach(str(entered_codes), name="entered_codes", attachment_type=allure.attachment_type.TEXT)
            soft_assert.check_true(
                len(entered_codes) == len(QUANTITIES),
                f"Expected {len(QUANTITIES)} distinct product rows entered, got {len(entered_codes)}",
            )
        except Exception as exc:
            soft_assert.check(False, f"Entering product quantities failed: {exc}")

    summary = None
    with step(page, "Click Calc and verify the summary bar"):
        try:
            page.click_calc()
            summary = page.get_summary()
            allure.attach(str(summary), name="calc_summary", attachment_type=allure.attachment_type.TEXT)
            soft_assert.check_equal(summary["total_item"], str(len(QUANTITIES)), "Calc summary: Total Item")
            soft_assert.check_true(
                _to_float(summary["final_amount"]) > 0,
                f"Calc summary: Final Amount should be > 0, got {summary['final_amount']!r}",
            )
            soft_assert.check_true(
                _to_float(summary["qty_pcs"]) > 0,
                f"Calc summary: Qty (pcs) should be > 0, got {summary['qty_pcs']!r}",
            )
        except Exception as exc:
            soft_assert.check(False, f"Calc step failed: {exc}")

    with step(page, "Open View Selected Items and verify it matches what was entered"):
        try:
            page.open_view_selected_items()
            items, total = page.get_selected_items()
            allure.attach(str(items), name="selected_items", attachment_type=allure.attachment_type.TEXT)
            found = {item["vsku"]: item for item in items}
            for code, qty in entered_codes.items():
                soft_assert.check_true(code in found, f"Selected Items Overview should list item {code}")
                if code in found:
                    unit_qty_text = found[code]["unit_qty"]
                    soft_assert.check_true(
                        unit_qty_text.startswith(str(qty)),
                        f"Selected Items Overview qty for {code}: expected to start with {qty}, got {unit_qty_text!r}",
                    )
            if summary is not None and total is not None:
                soft_assert.check_equal(
                    _to_float(total["value"]),
                    _to_float(summary["final_amount"]),
                    "Selected Items Overview total value vs Calc final amount",
                )
            page.close_selected_items()
        except Exception as exc:
            soft_assert.check(False, f"View Selected Items step failed: {exc}")

    with step(page, "Click Print and verify the Print Preview modal"):
        try:
            page.click_print()
            note = page.get_print_preview_note()
            soft_assert.check_true(
                "not saved" in note.lower(),
                f"Print Preview note should mention the invoice is not saved yet, got {note!r}",
            )
            page.close_print_preview()
        except Exception as exc:
            soft_assert.check(False, f"Print preview step failed: {exc}")

    with step(page, "Save Draft and verify the confirmation alert"):
        try:
            page.click_save_draft()
            alert_text = page.get_draft_alert_text()
            soft_assert.check_true(
                "draft saved successfully" in alert_text.lower(),
                f"Draft alert should confirm the save, got {alert_text!r}",
            )
            page.confirm_draft_alert()
        except Exception as exc:
            soft_assert.check(False, f"Save Draft step failed: {exc}")

    with step(page, "Verify the saved draft appears in the drafts list"):
        try:
            draft_page = DraftPage(logged_in_driver)
            draft_page.open()
            latest = draft_page.get_latest_draft_for_client(CUSTOMER_NAME)
            allure.attach(str(latest), name="latest_draft_row", attachment_type=allure.attachment_type.TEXT)
            soft_assert.check_true(latest is not None, f"A draft row for '{CUSTOMER_NAME}' should exist after saving")
            if latest is not None:
                soft_assert.check_equal(latest["client"], CUSTOMER_NAME, "Draft list: Client name")
                soft_assert.check_equal(latest["no_of_items"], str(len(QUANTITIES)), "Draft list: No. Of Items")
                if summary is not None:
                    soft_assert.check_equal(
                        latest["draft_qty"], summary["all_qty_pcs"], "Draft list: Draft Qty vs Calc All Qty (pcs)"
                    )
        except Exception as exc:
            soft_assert.check(False, f"Draft verification step failed: {exc}")
