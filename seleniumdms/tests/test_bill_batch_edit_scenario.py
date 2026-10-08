"""Bill/New Invoice: an item's quantity is split across two batches -> Save -> Add Sale -> Proceed ->
My Sales -> Action -> Edit. The Edit Sale page must show the SAME batches with the SAME quantities;
if the batches differ, that is a bug."""
import re

import allure
import pytest

from pages.bill_batch_page import BillBatchPage
from pages.my_sale_page import MySalePage
from utilities.allure_utils import step

CUSTOMER_NAME = "Demo Dealer 3"
pytestmark = pytest.mark.xdist_group(name="dd3")  # parallel runs: one group per customer, never shared

QTY_PER_BATCH = 1
# Optional: name (or part of the name) of a product that has 2+ batches with stock, e.g. "Vanilla Cup".
# Leave empty to let the test search the grid for one (slower: it opens each row's batch popup).
BATCH_PRODUCT_SEARCH = "Red Velvet Badabite Candy [1*8] 80ML"   # 2 batches: OB and 001PPO0


def _num(value):
    match = re.search(r"-?\d+(?:\.\d+)?", str(value or "").replace(",", ""))
    return float(match.group()) if match else None


def _row_index_by_code(page, item_code):
    for i in range(len(page.find_all(page.PRODUCT_ROWS))):
        try:
            if page.product_row(i)["item_code"] == item_code:
                return i
        except Exception:
            continue
    return None


@allure.epic("Bill / New Invoice")
@allure.feature("Batches")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Bill: item split across 2 batches -> Save -> Add Sale -> My Sales Edit -> same batches and quantities")
def test_batch_split_kept_on_sale_edit(logged_in_driver, soft_assert):
    page = BillBatchPage(logged_in_driver)
    my_sales = MySalePage(logged_in_driver)

    with step(page, "Note the newest My Sales invoice for this customer (baseline)"):
        try:
            baseline = my_sales.open().get_latest_invoice_id(CUSTOMER_NAME)
        except Exception:
            baseline = None

    with step(page, f"Open Bill/New Invoice and select '{CUSTOMER_NAME}'"):
        page.open()
        page.select_customer(CUSTOMER_NAME)

    with step(page, "Find an in-stock item that has at least two batches"):
        row, info, batches = page.find_row_with_two_batches(
            min_stock=QTY_PER_BATCH, product_search=BATCH_PRODUCT_SEARCH or None
        )
        code = info["item_code"]
        allure.attach(f"row={row}\nproduct={info['display_name']}\nitem code={code}\nbatches used={batches}",
                      name="item_and_batches", attachment_type=allure.attachment_type.TEXT)

    with step(page, f"Unit Piece; put {QTY_PER_BATCH} in each of the two batches via the hamburger; Apply"):
        page.set_unit(row, "piece")
        wanted = {b: QTY_PER_BATCH for b in batches}
        popup_unit, alert = page.split_across_batches(row, wanted, unit="piece")
        soft_assert.check_true(
            popup_unit in (None, "piece", "pieces", "pcs"),
            f"The batch popup should be in Piece mode after selecting Piece, title shows unit {popup_unit!r}",
        )
        if alert:
            allure.attach(str(alert), name="alert_after_apply", attachment_type=allure.attachment_type.TEXT)
        sale_alloc, sale_popup = page.read_allocation(row, unit="piece")
        allure.attach(f"wanted={wanted}\nshown after Apply={sale_alloc}\n\n{sale_popup}",
                      name="batches_on_sale", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_true(
            sale_alloc == {b: float(q) for b, q in wanted.items()},
            f"On the sale, the batch split should be {wanted}, popup shows {sale_alloc}",
        )
        qty_box = (page.product_row(row)["qty_input"].get_attribute("value") or "").strip()
        soft_assert.check_equal(_num(qty_box), float(QTY_PER_BATCH * len(batches)), "Sale: row qty = sum of batch qty")

    with step(page, "Calculate, Save and Proceed (Add Sale -> Yes! Proceed.)"):
        page.click_calc()
        summary = page.get_summary()
        allure.attach(str(summary), name="sale_calc", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_equal(summary["total_item"], "1", "Sale: Calc Total Item")
        page.click_save()
        page.click_add_sale()
        page.confirm_sale_proceed()
        page.wait_for_sale_completed()
        page.dismiss_post_sale_print_preview()

    with step(page, "My Sales: hover Action on the new sale and click Edit"):
        my_sales.open()
        sale_row = my_sales.get_latest_sale_for_client(CUSTOMER_NAME, exclude_invoice_ids={baseline})
        allure.attach(str(sale_row), name="my_sales_row", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_true(sale_row is not None, "The new sale should appear on My Sales")
        my_sales.click_edit_for_client(CUSTOMER_NAME, invoice_id=sale_row["invoice_id"] if sale_row else None)
        page.wait_for_grid_loaded()

    with step(page, "Sale Edit: the item's batches must be the same as on the sale"):
        edit_row = _row_index_by_code(page, code)
        soft_assert.check_true(edit_row is not None, f"Item {code} should be on the Edit Sale page")
        if edit_row is not None:
            edit_alloc, edit_popup = page.read_allocation(edit_row, unit="piece")
            allure.attach(f"on sale={sale_alloc}\non edit={edit_alloc}\n\n{edit_popup}",
                          name="batches_sale_vs_edit", attachment_type=allure.attachment_type.TEXT)
            soft_assert.check_true(
                set(edit_alloc) == set(sale_alloc),
                f"BUG: Edit Sale shows different batches -- sold from {sorted(sale_alloc)}, edit shows {sorted(edit_alloc)} "
                f"({info['display_name']})",
            )
            for batch, qty in sale_alloc.items():
                if batch in edit_alloc:
                    soft_assert.check_true(
                        edit_alloc[batch] == qty,
                        f"BUG: batch {batch!r} qty changed on Edit Sale -- sold {qty:g}, edit shows {edit_alloc[batch]:g}",
                    )
            edit_qty = (page.product_row(edit_row)["qty_input"].get_attribute("value") or "").strip()
            soft_assert.check_equal(_num(edit_qty), float(QTY_PER_BATCH * len(batches)), "Edit Sale: row qty")
