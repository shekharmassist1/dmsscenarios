"""Bill/New Invoice: every product that shows inventory must have its batch(es) in the hamburger
batch popup, and the batches' total inventory must equal the product's 'Pcs. Inv.'.
A product with stock but no batch (or batches that don't add up) is a bug."""
import allure
import pytest

from pages.bill_batch_page import BillBatchPage
from utilities.allure_utils import step

CUSTOMER_NAME = "Demo Dealer 3"
pytestmark = pytest.mark.xdist_group(name="dd3")  # parallel runs: one group per customer, never shared

MAX_PRODUCTS = 20      # in-stock products to check per run (each needs its popup opened); raise to check more
TOLERANCE = 0.5        # pieces


@allure.epic("Bill / New Invoice")
@allure.feature("Batches")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Bill: every in-stock product has its batch(es) in the batch popup, and batch total = Pcs. Inv.")
def test_in_stock_products_have_batches(logged_in_driver, soft_assert):
    page = BillBatchPage(logged_in_driver)

    with step(page, f"Open Bill/New Invoice and select '{CUSTOMER_NAME}'; show all products"):
        page.open()
        page.select_customer(CUSTOMER_NAME)
        page.show_all_products()

    results, checked = [], 0
    with step(page, f"Open the batch popup of up to {MAX_PRODUCTS} in-stock products"):
        for i in range(len(page.find_all(page.PRODUCT_ROWS))):
            if checked >= MAX_PRODUCTS:
                break
            try:
                info = page.product_row(i)
            except Exception:
                continue
            pcs_inv = page.row_pcs_inventory(i)
            in_stock = (pcs_inv is not None and pcs_inv > 0) or info["available_stock"] > 0
            if not in_stock:
                continue
            checked += 1
            try:
                summary = page.batch_summary(i)
            except Exception as exc:
                results.append((info["display_name"], pcs_inv, "popup did not open", None))
                soft_assert.check(False, f"BUG: batch popup did not open for in-stock product {info['display_name']!r}: {exc}")
                continue

            batch_sum = sum(s for _, s in summary["batches"] if s is not None)
            popup_total = summary["total"] if summary["total"] is not None else batch_sum
            results.append((info["display_name"], pcs_inv, summary["batches"], popup_total))

            if summary["no_data"]:
                soft_assert.check(
                    False,
                    f"BUG: no batch present for in-stock product {info['display_name']!r} "
                    f"(Pcs. Inv. {pcs_inv}, inventory {info['available_stock']} carton)",
                )
                continue
            if pcs_inv is not None and abs(popup_total - pcs_inv) > TOLERANCE:
                soft_assert.check(
                    False,
                    f"BUG: batch inventory does not add up for {info['display_name']!r} -- batches "
                    f"{summary['batches']} total {popup_total:g}, but the grid shows Pcs. Inv. {pcs_inv:g}",
                )

    lines = [f"{name} | Pcs.Inv={pcs} | batches={b} | popup total={t}" for name, pcs, b, t in results]
    allure.attach(f"Checked {checked} in-stock products\n\n" + "\n".join(lines),
                  name="batch_presence_results", attachment_type=allure.attachment_type.TEXT)
    soft_assert.check_true(checked > 0, "No in-stock products were found to check")
