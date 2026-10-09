import os
import time

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from pages.base_page import BasePage


class SaleReturnPage(BasePage):
    """Page object for the Sale Return module (DMSPages/ProductReceived.html), isolated from the
    Sale/Bill module in pages/product_page.py. New Sale Return scenarios should be added as new
    test functions in tests/test_sale_return_scenarios.py, reusing the methods here."""

    URL = "https://admin.massistcrm.com/DMSPages/ProductReceived.html"

    CUSTOMER_SEARCH_INPUT = (By.XPATH, "//input[@type='search']")
    PAGE_HEADER = (By.TAG_NAME, "h1")

    BILL_FOR_SELECT = (By.ID, "ddlBillFor")
    BILL_FOR_GO_BUTTON = (By.XPATH, "//button[normalize-space(text())='Go!']")

    # The "With Reference" invoice picker is a custom div-based grid (NOT a <table>), one
    # div.row[id="{Order_Id}"] per invoice, with a checkbox (not a per-row button) to select it.
    REFERENCE_INVOICE_ROWS = (By.CSS_SELECTOR, ".divGridSaleData .row[id]")

    PRODUCT_ROWS = (By.CSS_SELECTOR, "#productlist tbody tr")
    SALEABLE_QTY_INPUTS = (By.CSS_SELECTOR, "#productlist tbody tr input.C1")
    # With Reference: the sold qty is shown read-only in 'Saled Qty'; 'Select All' copies it into the
    # Qty boxes (there is no 'Full Sale Return' button any more -- finish with Save -> Goods Receive).
    SELECT_ALL_BUTTON = (By.CSS_SELECTOR, "input.btnSelectAllProduct")

    CALC_BUTTON = (By.ID, "lblCalculate")
    SUMMARY_TOTAL_ITEM = (By.CSS_SELECTOR, "#divitem span")
    SUMMARY_AMOUNT = (By.CSS_SELECTOR, "#divAmount span")
    SUMMARY_FINAL_AMOUNT = (By.CSS_SELECTOR, "#totalPayAmt span")

    # The "Insufficient Inventory" alert (jconfirm-type-blue, btn-godown-inv-ok) can appear after
    # applying a batch split or clicking Calc, driven by real production stock levels on the shared
    # demo account -- it must be dismissed opportunistically rather than treated as a failure.
    INVENTORY_ALERT_OK = (By.CSS_SELECTOR, ".jconfirm-box .btn-godown-inv-ok")

    VISIBLE_JCONFIRM_BOXES = (By.CSS_SELECTOR, ".jconfirm-box")

    VIEW_SELECTED_BUTTON = (By.ID, "btnViewAllSelectedItems")
    SELECTED_POPOVER = (By.ID, "viewSelectedItemsPopover")

    PRINT_BUTTON = (By.ID, "btnPrintPreview")
    PRINT_PREVIEW_TITLE = (By.XPATH, "//*[normalize-space(text())='Print Preview']")
    PRINT_PREVIEW_NOTE = (By.XPATH, "//*[contains(text(),'Invoice Preview Only')]")
    PRINT_PREVIEW_CLOSE = (
        By.XPATH,
        "//div[contains(@class,'jconfirm-box')][.//*[normalize-space(text())='Print Preview']]"
        "//div[contains(@class,'jconfirm-buttons')]/button[normalize-space(text())='Close']",
    )

    SAVE_BUTTON = (By.ID, "cartItemBtn")
    RECEIVE_GOODS_BUTTON = (By.ID, "btnProductsRecieve")

    # Confirmed live: the "With Reference" flow has no Print/Save/Receive Goods buttons at all --
    # it finalizes directly via this single "Full Sale Return" button instead.
    FULL_SALE_RETURN_BUTTON = (By.ID, "FullSaleReturn")

    def open(self):
        self.get(self.URL)
        # Confirmed live (same class as the product-grid slow-AJAX finding): this page can take
        # well over the default 20s wait to render its customer search input under current server
        # load, with no error -- just a slow initial page script. A longer explicit wait avoids a
        # false-negative timeout here without masking a genuine failure.
        self.wait_until(
            EC.presence_of_element_located(self.CUSTOMER_SEARCH_INPUT),
            timeout=60,
            message=f"{self.CUSTOMER_SEARCH_INPUT} never became present",
        )
        return self

    # Fallback customer to try if the primary one has no products assigned (the app shows a
    # blocking "Product not exists!" alert in that case rather than proceeding).
    FALLBACK_CUSTOMER = "Demo Dealer 4"

    @staticmethod
    def _wait_table_settled(wrapper, timeout=10):
        """Wait until the table's 'Showing X To Y Of Z Entries' text stops changing (filter/redraw done)."""
        end = time.time() + timeout
        last, stable = None, 0
        while time.time() < end:
            try:
                text = wrapper.find_element(By.CSS_SELECTOR, ".dataTables_info").text
            except Exception:
                text = ""
            if text == last:
                stable += 1
                if stable >= 3:
                    return
            else:
                last, stable = text, 0
            time.sleep(0.3)

    def _customer_table(self):
        """(search_input, table_wrapper) for the VISIBLE customer table only."""
        def _visible_search(d):
            for el in d.find_elements(*self.CUSTOMER_SEARCH_INPUT):
                if el.is_displayed():
                    return el
            return False

        search = self.wait_until(_visible_search, timeout=60, message="Customer search box never became visible")
        wrapper = search.find_element(By.XPATH, "./ancestor::div[contains(@class,'dataTables_wrapper')]")
        return search, wrapper

    def _select_customer_once(self, name):
        """The search matches each word separately across all columns ('Demo Dealer 2' also returns
        'Demo Dealer 11/12/20...'), which can push the wanted customer onto page 2. So: show All rows
        in this table, search, wait for the redraw, take an EXACT name match, and page through with
        Next only as a fallback."""
        search, wrapper = self._customer_table()
        try:
            selects = wrapper.find_elements(By.CSS_SELECTOR, "select[name$='_length']") or \
                wrapper.find_elements(By.CSS_SELECTOR, ".dataTables_length select")
            if selects:
                Select(selects[0]).select_by_value("-1")
                self._wait_table_settled(wrapper)
        except Exception as exc:
            print(f"Could not switch customer list to 'All' (will page through instead): {exc}")

        search.clear()
        search.send_keys(name)
        self._wait_table_settled(wrapper)

        row_xpath = f".//tbody/tr[td[normalize-space(.)='{name}']]"
        # On a fast machine the table can look 'settled' before the search results arrive, so give
        # the exact row up to 20s to appear before falling back to paging (seen on the Linux server).
        try:
            self.wait_until(lambda d: wrapper.find_elements(By.XPATH, row_xpath), timeout=20)
        except Exception:
            pass
        for _ in range(20):
            rows = wrapper.find_elements(By.XPATH, row_xpath)
            if rows:
                select_btn = rows[0].find_element(
                    By.XPATH,
                    ".//a[contains(normalize-space(.),'Select')] | .//button[contains(normalize-space(.),'Select')]",
                )
                self.js_click(select_btn)
                return
            next_btn = wrapper.find_elements(By.CSS_SELECTOR, ".paginate_button.next")
            if not next_btn or "disabled" in (next_btn[0].get_attribute("class") or ""):
                break
            target = next_btn[0].find_elements(By.TAG_NAME, "a") or [next_btn[0]]
            self.js_click(target[0])
            self._wait_table_settled(wrapper)

        raise TimeoutException(f"Customer row for '{name}' never appeared in the search results")

    def select_customer(self, name):
        self._select_customer_once(name)

        alert_message = self.dismiss_blocking_alert()
        if alert_message and "product not exist" in alert_message.lower():
            if name == self.FALLBACK_CUSTOMER:
                raise AssertionError(
                    f"Customer '{name}' has no products available, and it is "
                    f"already the fallback customer -- no further fallback to try"
                )
            if os.environ.get("PYTEST_XDIST_WORKER_COUNT", "1") not in ("", "1"):
                raise AssertionError(
                    f"Customer '{name}' has no products available. The fallback to "
                    f"'{self.FALLBACK_CUSTOMER}' is disabled in parallel runs (another worker may be using it)"
                )
            self._select_customer_once(self.FALLBACK_CUSTOMER)

        return self

    def choose_without_reference_and_go(self):
        ddl = self.wait_until(
            EC.presence_of_element_located(self.BILL_FOR_SELECT),
            timeout=60,
            message="'Sale Return For...' dialog (ddlBillFor) never appeared after selecting the customer",
        )
        Select(ddl).select_by_visible_text("Without Reference")
        self.click(self.BILL_FOR_GO_BUTTON)
        return self

    def _real_invoice_rows_present(self, d):
        return any((r.get_attribute("id") or "").isdigit() for r in d.find_elements(*self.REFERENCE_INVOICE_ROWS))

    def _open_with_reference_dialog_and_go(self):
        ddl = self.wait_until(
            EC.presence_of_element_located(self.BILL_FOR_SELECT),
            timeout=60,
            message="'Sale Return For...' dialog (ddlBillFor) never appeared after selecting the customer",
        )
        Select(ddl).select_by_visible_text("With Reference")
        self.click(self.BILL_FOR_GO_BUTTON)

    def choose_with_reference_and_go(self, customer_name=None):
        self._open_with_reference_dialog_and_go()
        self.wait_until(
            self._real_invoice_rows_present,
            timeout=30,
            # An empty placeholder row (id="") can render before the real, numbered invoice rows
            # load, so a plain "count > 0" check is satisfied too early -- require a numeric-id row.
            message="'With Reference' invoice list never populated with real invoices after clicking Go!",
        )
        return self

    def open_with_reference_and_select_invoice(self, customer_name, order_id, max_attempts=3):
        """Confirmed live: this whole 'With Reference' sub-flow (selecting the customer, opening
        the dialog, clicking Go!, checking an invoice and submitting Select) is prone to a
        silent click-registration flake on this shared environment that can revert all the way back
        to the Select Customer screen at any of those steps -- not a slow load, and re-clicking just
        the failed step in place isn't reliable once the surrounding state is gone. Retrying the
        whole sequence from a fresh page load matches this project's established login-retry
        convention and is what actually resolves it. Returns the matched invoice dict."""
        last_exc = None
        for _ in range(max_attempts):
            try:
                self.open()
                self.select_customer(customer_name)
                self.choose_with_reference_and_go(customer_name=customer_name)
                invoices = self.get_reference_invoices(limit=10)
                invoice = next((i for i in invoices if i["order_id"] == order_id), None)
                if invoice is None:
                    raise AssertionError(
                        f"Order_Id={order_id} not found in 'With Reference' list: "
                        f"{[i['order_id'] for i in invoices]}"
                    )
                self.select_reference_invoice(order_id)
                return invoice
            except Exception as exc:
                last_exc = exc
        raise last_exc

    def get_reference_invoices(self, limit=10):
        """Returns [{order_id, amount, noofitem}] read straight from the 'With Reference' invoice
        picker, in the order shown (newest first) -- confirmed live to match order_dtls exactly
        (Amount == Order_Amt, NoOfItem == NoOfProducts) for OrderType='sale' records."""
        rows = self.find_all(self.REFERENCE_INVOICE_ROWS)
        invoices = []
        for row in rows:
            if len(invoices) >= limit:
                break
            row_id = row.get_attribute("id")
            if not row_id or not row_id.isdigit():
                continue
            cells = row.find_elements(By.XPATH, "./div")
            invoices.append({
                "order_id": int(row_id),
                "amount": cells[4].text.strip(),
                "noofitem": cells[6].text.strip(),
            })
        return invoices

    def select_reference_invoice(self, order_id):
        row = self.find((By.CSS_SELECTOR, f".divGridSaleData .row[id='{order_id}']"))
        checkbox = row.find_element(By.CSS_SELECTOR, "input.SaleReferenceSelection")
        if not checkbox.is_selected():
            self.js_click(row.find_element(By.CSS_SELECTOR, "label"))
        select_btn = next(
            b for b in self.find_all((By.CSS_SELECTOR, ".jconfirm-buttons button"))
            if b.is_displayed() and b.text.strip() == "Select"
        )
        self.js_click(select_btn)
        self.wait_for_grid_loaded()
        # Quantities are NOT pre-filled any more (the Qty boxes start empty; use select_all_reference_items).
        return self

    def select_all_reference_items(self, timeout=30):
        """Click 'Select All' on a With Reference return so every invoice item gets its sold qty,
        then wait until the Qty boxes are filled. Returns True if quantities appeared."""
        self.dismiss_inventory_alert(timeout=1)
        buttons = [b for b in self.find_all(self.SELECT_ALL_BUTTON) if b.is_displayed()]
        if not buttons:
            raise AssertionError("'Select All' button not found on the With Reference return")
        self.js_click(buttons[0])
        time.sleep(1)
        self.dismiss_inventory_alert(timeout=2)
        filled = self._wait_for_any_qty(timeout)
        if not filled:
            print("No Qty box was filled after clicking Select All")
        return filled

    def _wait_for_any_qty(self, timeout):
        def _has_qty(d):
            for inp in d.find_elements(*self.SALEABLE_QTY_INPUTS):
                try:
                    value = (inp.get_attribute("value") or "").strip()
                    if value and float(value) > 0:
                        return True
                except (ValueError, StaleElementReferenceException):
                    continue
            return False
        try:
            self.wait_until(_has_qty, timeout=timeout, message="")
            return True
        except Exception:
            return False

    def complete_return_with_save(self):
        """Save -> Goods Receive -> returns the 'Return Confirm' text (call confirm_receive_proceed next)."""
        self.click_save()
        self.click_receive_goods()
        return self.get_receive_confirm_text()

    def wait_for_prefilled_quantities(self, timeout=45):
        """In the 'With Reference' flow the grid rows appear first and the originally sold quantities
        are filled into C1 a moment later by a second AJAX call. Clicking Calc before that gave
        'Total Item 0' (Scenario 7). Wait until at least one C1 input holds a non-zero number; if it
        never happens, carry on so the test's own Calc check reports it."""
        def _has_qty(d):
            for inp in d.find_elements(*self.SALEABLE_QTY_INPUTS):
                try:
                    value = (inp.get_attribute("value") or "").strip()
                    if value and float(value) > 0:
                        return True
                except (ValueError, StaleElementReferenceException):
                    continue
            return False

        try:
            self.wait_until(_has_qty, timeout=timeout, message="")
        except Exception:
            print("Referenced invoice quantities were not pre-filled within the wait")
        return self

    def wait_for_grid_loaded(self, timeout=120):
        # Confirmed via live diagnostics: this AJAX product load can genuinely take ~20s+ (and, under
        # heavier server load, up to ~90s -- confirmed with a clean, non-error 87s load with no
        # blocking dialog present the whole time), so it needs a much longer wait than the sale
        # page's equivalent grid load. A blocking "Alert!"
        # (e.g. "Product not exists!" for a since-deactivated product) can also sit in front of the
        # grid indefinitely -- BasePage's generic alert dismissal is reused here since the wait
        # itself doesn't go through click()'s own dismiss-alert retry loop.
        def _grid_ready(d):
            self.dismiss_blocking_alert(timeout=0.3)
            return len(d.find_elements(*self.SALEABLE_QTY_INPUTS)) > 0

        self.wait_until(
            _grid_ready,
            timeout=timeout,
            message="Sale Return product grid rows never appeared after clicking Go!",
        )
        return self

    def get_page_header_text(self):
        return self.text_of(self.PAGE_HEADER)

    def get_visible_product_row_count(self):
        return len(self.find_all(self.PRODUCT_ROWS))

    def product_row(self, index):
        rows = self.find_all(self.PRODUCT_ROWS)
        row = rows[index]
        display_name = row.find_element(By.CSS_SELECTOR, "span.Variant_Name").get_attribute(
            "product_name"
        ).strip()
        c1 = row.find_element(By.CSS_SELECTOR, "input.C1")
        c2 = row.find_element(By.CSS_SELECTOR, "input.C2")
        return {
            "display_name": display_name,
            "c1_input": c1,
            "c2_input": c2,
            "row": row,
        }

    def get_row_identifier(self, index):
        """A stable, unique id (variant_id, falling back to data-productid) for the row at this
        index -- unlike the display name, which can repeat across different rows/variants in this
        catalog (confirmed live), this is safe to use as a dict key when tracking distinct items."""
        row = self.find_all(self.PRODUCT_ROWS)[index]
        container = row.find_element(By.CSS_SELECTOR, "div.tbl_content_n")
        return container.get_attribute("variant_id") or container.get_attribute("data-productid")

    def enter_saleable_qty(self, row_index, qty):
        info = self.product_row(row_index)
        inp = info["c1_input"]
        self.js_click(inp)
        inp.clear()
        inp.send_keys(str(qty))
        inp.send_keys(Keys.TAB)
        return info["display_name"]

    def enter_damage_qty(self, row_index, qty):
        info = self.product_row(row_index)
        inp = info["c2_input"]
        self.js_click(inp)
        inp.clear()
        inp.send_keys(str(qty))
        inp.send_keys(Keys.TAB)
        return info["display_name"]

    def dismiss_inventory_alert(self, timeout=2):
        try:
            ok_btn = self.wait_until(EC.visibility_of_element_located(self.INVENTORY_ALERT_OK), timeout=timeout)
        except Exception:
            return False
        self.js_click(ok_btn)
        self.wait_until(
            EC.invisibility_of_element_located(self.INVENTORY_ALERT_OK),
            timeout=10,
            message="Insufficient Inventory alert did not close after clicking Okay",
        )
        return True

    def open_batch_split(self, row_index):
        """Opens the per-batch 'Batch List Of <product>' modal via the row's hamburger
        (ShowBatchWiseVariant) icon. Confirmed: entering a value directly in the row's Damage
        Item (C2) field alone is NOT enough for it to persist -- this modal's own per-batch
        inputs + Apply is what actually commits the saleable/damage split."""
        # The Tab key out of the qty field fires a blur-triggered AJAX recalculation; clicking the
        # hamburger immediately can land before the row settles, so give it a brief beat first
        # (confirmed live: identical code succeeds with this pause and fails without it).
        time.sleep(1)
        info = self.product_row(row_index)
        hamburger = info["row"].find_element(By.CSS_SELECTOR, "span.ShowBatchWiseVariant")
        self.js_click(hamburger)
        self._visible_box_containing("Batch List Of")
        return self

    def get_batch_split_text(self):
        return self._visible_box_containing("Batch List Of").text.strip()

    def apply_batch_split(self):
        modal = self._visible_box_containing("Batch List Of")
        apply_btn = modal.find_element(By.XPATH, ".//button[normalize-space(text())='Apply']")
        self.js_click(apply_btn)
        self.dismiss_inventory_alert(timeout=3)
        return self

    def cancel_batch_split(self):
        """Closes the 'Batch List Of...' modal without committing. Confirmed live: clicking Apply
        on a SALEABLE row silently clears that row's already-entered quantity back to empty (a real
        app defect -- Apply is only actually required for Damage rows, per open_batch_split's own
        docstring) -- use this instead when only verifying a saleable row's batch split, not
        committing a change to it."""
        modal = self._visible_box_containing("Batch List Of")
        cancel_btn = modal.find_element(By.XPATH, ".//button[normalize-space(text())='Cancel']")
        self.js_click(cancel_btn)
        return self

    def click_calc(self):
        self.click(self.CALC_BUTTON)
        for _ in range(5):
            if not self.dismiss_inventory_alert(timeout=2):
                break
        self.wait_until(
            lambda d: any(ch.isdigit() for ch in d.find_element(*self.SUMMARY_FINAL_AMOUNT).text),
            timeout=20,
            message="Final Amount never populated after clicking Calc",
        )
        return self

    def get_summary(self):
        return {
            "total_item": self.text_of(self.SUMMARY_TOTAL_ITEM),
            "amount": self.text_of(self.SUMMARY_AMOUNT),
            "final_amount": self.text_of(self.SUMMARY_FINAL_AMOUNT),
        }

    def click_print(self):
        # A straggler "Insufficient Inventory" alert can still be open here (its jconfirm-title
        # text doesn't match BasePage.click()'s generic "Alert..." dismiss pattern, so that retry
        # loop won't clear it) -- dismiss it explicitly before it blocks the Print button.
        self.dismiss_inventory_alert(timeout=2)
        self.click(self.PRINT_BUTTON)
        # Same slow-AJAX-under-load pattern already confirmed for the product grid and page open --
        # the Print Preview modal's content can take well over the default 20s to render.
        self.wait_until(
            EC.presence_of_element_located(self.PRINT_PREVIEW_TITLE),
            timeout=60,
            message="Print Preview modal never appeared after clicking Print",
        )
        return self

    def click_print_or_detect_error(self, timeout=60):
        """Click Print; return (True, None) if Print Preview opens, or (False, error_text) if an
        unrelated jconfirm error dialog appears instead (e.g. the Bill/New Invoice module's known
        'Something went wrong...Error Code : -1014' defect on repeated Print use -- TC-16)."""
        self.dismiss_inventory_alert(timeout=2)
        self.click(self.PRINT_BUTTON)

        def _outcome(d):
            if d.find_elements(*self.PRINT_PREVIEW_TITLE):
                return "preview"
            error_boxes = []
            for b in d.find_elements(By.CSS_SELECTOR, ".jconfirm-box"):
                try:
                    text = b.text.lower()
                    if b.is_displayed() and ("something went wrong" in text or "error code" in text):
                        error_boxes.append(b)
                except StaleElementReferenceException:
                    continue
            if error_boxes:
                return error_boxes[0].text
            return False

        result = self.wait_until(
            _outcome,
            timeout=timeout,
            message="Neither the Print Preview modal nor an error dialog appeared after clicking Print",
        )
        if result == "preview":
            return True, None
        return False, result

    def get_print_preview_note(self):
        return self.text_of(self.PRINT_PREVIEW_NOTE)

    def close_print_preview(self):
        self.click(self.PRINT_PREVIEW_CLOSE)
        self.wait_until(
            EC.invisibility_of_element_located(self.PRINT_PREVIEW_TITLE),
            message="Print Preview modal did not close after clicking Close",
        )
        return self

    def open_view_selected_items(self):
        self.dismiss_inventory_alert(timeout=2)
        self.click(self.VIEW_SELECTED_BUTTON)
        self.wait_until(
            EC.visibility_of_element_located(self.SELECTED_POPOVER),
            message="View Selected Items popover never appeared",
        )
        return self

    def get_selected_items(self):
        popover = self.find(self.SELECTED_POPOVER)
        rows = popover.find_elements(By.CSS_SELECTOR, "table tbody tr")
        items = []
        for r in rows:
            cells = r.find_elements(By.TAG_NAME, "td")
            if len(cells) < 3:
                continue
            items.append([c.text.strip() for c in cells])
        return items

    def close_selected_items(self):
        try:
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        except Exception:
            pass
        return self

    def click_full_sale_return(self):
        self.dismiss_inventory_alert(timeout=2)
        self.click(self.FULL_SALE_RETURN_BUTTON)
        self._visible_box_containing("Full Sale Return")
        return self

    def get_full_return_confirm_text(self):
        return self._visible_box_containing("Full Sale Return").text.strip()

    def confirm_full_return_proceed(self):
        box = self._visible_box_containing("Full Sale Return")
        proceed_btn = box.find_element(By.XPATH, ".//button[contains(normalize-space(.),'Proceed')]")
        self.js_click(proceed_btn)
        self._wait_for_success()
        return self

    def click_save(self):
        self.dismiss_inventory_alert(timeout=2)
        self.click(self.SAVE_BUTTON)
        self.wait_until(
            EC.visibility_of_element_located(self.RECEIVE_GOODS_BUTTON),
            message="Goods Receive button never became visible after clicking Save",
        )
        return self

    def _visible_box_containing(self, text, timeout=None):
        # jconfirm boxes briefly re-render right after appearing (shake-in animation), and one box
        # can be swapped out for another (e.g. Return Confirm -> Success) mid-poll -- WebDriverWait
        # does not ignore StaleElementReferenceException by default, so each element access here is
        # guarded individually instead of relying on a single find() reference staying valid.
        def _condition(d):
            for b in d.find_elements(*self.VISIBLE_JCONFIRM_BOXES):
                try:
                    if b.is_displayed() and text in b.text:
                        return b
                except StaleElementReferenceException:
                    continue
            return False

        return self.wait_until(_condition, timeout=timeout, message=f"No visible jconfirm-box containing {text!r} found")

    def click_receive_goods(self):
        self.click(self.RECEIVE_GOODS_BUTTON)
        self._visible_box_containing("Return Confirm")
        return self

    def get_receive_confirm_text(self):
        return self._visible_box_containing("Return Confirm").text.strip()

    def confirm_receive_proceed(self):
        box = self._visible_box_containing("Return Confirm")
        proceed_btn = box.find_element(By.XPATH, ".//button[contains(normalize-space(.),'Proceed')]")
        self.js_click(proceed_btn)
        self._wait_for_success()
        return self

    def _wait_for_success(self, timeout=60):
        """After 'Proceed' the server can take a while (up to a minute under load) to save the return.
        Wait for the Success dialog; if an error dialog shows up instead, fail with its text so the
        report says WHY (e.g. an app error code) rather than a bare timeout."""
        def _outcome(d):
            for b in d.find_elements(*self.VISIBLE_JCONFIRM_BOXES):
                try:
                    if not b.is_displayed():
                        continue
                    text = b.text
                    if "Success" in text:
                        return ("success", b)
                    lowered = text.lower()
                    if "error code" in lowered or "something went wrong" in lowered:
                        return ("error", text.strip().replace("\n", " | "))
                except StaleElementReferenceException:
                    continue
            return False

        kind, value = self.wait_until(
            _outcome, timeout=timeout, message="No Success (or error) dialog appeared after clicking Proceed"
        )
        if kind == "error":
            raise AssertionError(f"Return was not saved -- the app showed an error instead: {value}")
        return value

    def get_success_message(self):
        return self._visible_box_containing("Success").text.strip()

    def dismiss_success(self):
        box = self._visible_box_containing("Success")
        ok_btn = box.find_element(By.TAG_NAME, "button")
        self.js_click(ok_btn)

        def _no_longer_visible(d):
            for b in d.find_elements(*self.VISIBLE_JCONFIRM_BOXES):
                try:
                    if b.is_displayed() and "Success" in b.text:
                        return False
                except StaleElementReferenceException:
                    continue
            return True

        self.wait_until(_no_longer_visible, message="Success dialog did not close after clicking OK")
        return self
