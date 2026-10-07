import time

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from pages.base_page import BasePage
from utilities.performance import attach_page_performance


class MySalePage(BasePage):
    """My Sales report.

    Why this was rewritten:
      * The search box matches each word separately across all columns, so searching 'Demo Dealer 4'
        also returns 'Demo Dealer 11' etc. -- the old code took the first row, which could belong to
        a different customer.
      * The old wait ('any rows present') was satisfied BEFORE the filter applied.
      * 'Latest row for this customer' could be an OLDER sale (e.g. from a previous test) if the
        new sale wasn't searchable yet. Tests now pass the invoice id that existed BEFORE their sale
        (exclude_invoice_ids) so only the genuinely new sale is accepted.
      * Edit/Print always used the first row on the page; they now act on the exact matched row.
    """

    URL = "https://admin.massistcrm.com/DMSPages/Reports/MyPreviousSale.html"

    SEARCH_INPUT = (By.CSS_SELECTOR, "#tbl_order_grid_filter input[type='search']")
    ROWS = (By.CSS_SELECTOR, "#tbl_order_grid tbody tr")
    LENGTH_SELECT = (By.CSS_SELECTOR, "#tbl_order_grid_length select")
    TABLE_INFO = (By.CSS_SELECTOR, "#tbl_order_grid_info")

    PRINT_PREVIEW_TITLE = (
        By.XPATH, "//span[contains(@class,'jconfirm-title')][contains(.,'Print Preview')]"
    )
    PRINT_PREVIEW_PRINT_BUTTON = (
        By.XPATH,
        "//span[contains(@class,'jconfirm-title')][contains(.,'Print Preview')]"
        "/ancestor::div[contains(@class,'jconfirm-box')]//div[contains(@class,'jconfirm-buttons')]"
        "/button[normalize-space(text())='Print']",
    )

    def open(self):
        self.get(self.URL)
        self.find(self.SEARCH_INPUT)
        attach_page_performance(self.driver, "My Sales page")
        return self

    # ------------------------------------------------------------------ table helpers

    def _wait_table_settled(self, timeout=10):
        """Wait until 'Showing X To Y Of Z Entries' stops changing (filter/redraw finished)."""
        end = time.time() + timeout
        last, stable = None, 0
        while time.time() < end:
            try:
                text = self.driver.find_element(*self.TABLE_INFO).text
            except Exception:
                text = ""
            if text == last:
                stable += 1
                if stable >= 3:  # unchanged for ~1 second
                    return
            else:
                last, stable = text, 0
            time.sleep(0.3)

    def _show_all_rows(self):
        """Switch the grid's Show dropdown to All (if offered) so no matching row hides on page 2."""
        try:
            selects = self.driver.find_elements(*self.LENGTH_SELECT)
            if selects:
                select = Select(selects[0])
                if any(o.get_attribute("value") == "-1" for o in select.options):
                    select.select_by_value("-1")
                    self._wait_table_settled()
        except Exception as exc:
            print(f"Could not switch My Sales grid to 'All': {exc}")

    def search(self, text):
        self._show_all_rows()
        box = self.find(self.SEARCH_INPUT)
        box.clear()
        box.send_keys(text)
        self._wait_table_settled()
        return self

    @staticmethod
    def _invoice_id(row):
        return row.find_element(By.CSS_SELECTOR, "td.SaleId").text.split("\n")[0].strip()

    @staticmethod
    def _party_name(row):
        return row.find_element(By.CSS_SELECTOR, "td:nth-child(5)").text.strip()

    def _row_data(self, row):
        return {
            "invoice_id": self._invoice_id(row),
            "party_name": self._party_name(row),
            "no_of_items": row.find_element(By.CSS_SELECTOR, "td:nth-child(8)").text.strip(),
            "amount": row.find_element(By.CSS_SELECTOR, "td.OrderAmt").text.strip(),
            "sale_qty": row.find_element(By.CSS_SELECTOR, "td.PreviousQty").text.strip(),
        }

    def _client_rows(self, client_name):
        """Real data rows (newest first, as the grid lists them) whose Party Name is EXACTLY client_name."""
        matches = []
        for row in self.driver.find_elements(*self.ROWS):
            try:
                if not row.find_elements(By.CSS_SELECTOR, "td.SaleId"):
                    continue  # DataTables' 'No matching records found' placeholder row
                if self._party_name(row) == client_name:
                    matches.append(row)
            except StaleElementReferenceException:
                continue
        return matches

    def _wait_for_client_row(self, client_name, exclude_invoice_ids=(), invoice_id=None,
                             timeout=30, poll_interval=3):
        """Re-search until a matching row appears.

        - invoice_id given: return that exact sale.
        - otherwise: return the newest row for client_name whose invoice id is NOT in
          exclude_invoice_ids (i.e. a sale made after the test took its baseline).
        A just-finalized sale can take a moment to become searchable, so re-search (not just
        re-read the DOM) to give the backend time to catch up."""
        exclude = {i for i in (exclude_invoice_ids or ()) if i}
        deadline = time.time() + timeout
        while True:
            self.search(client_name)
            for row in self._client_rows(client_name):
                try:
                    inv = self._invoice_id(row)
                except StaleElementReferenceException:
                    continue
                if invoice_id is not None:
                    if inv == invoice_id:
                        return row
                elif inv not in exclude:
                    return row
            if time.time() >= deadline:
                return None
            time.sleep(poll_interval)

    # ------------------------------------------------------------------ public API

    def get_latest_invoice_id(self, client_name):
        """Invoice id of the newest sale for client_name right now (None if there is none).
        Tests call this BEFORE making their sale, then pass it as exclude_invoice_ids."""
        self.search(client_name)
        rows = self._client_rows(client_name)
        return self._invoice_id(rows[0]) if rows else None

    def get_latest_sale_for_client(self, client_name, exclude_invoice_ids=None, timeout=30):
        row = self._wait_for_client_row(client_name, exclude_invoice_ids=exclude_invoice_ids, timeout=timeout)
        if row is None:
            return None
        return self._row_data(row)

    def _resolve_row(self, client_name, invoice_id=None):
        row = None
        if invoice_id:
            row = self._wait_for_client_row(client_name, invoice_id=invoice_id, timeout=20)
        if row is None:
            row = self._wait_for_client_row(client_name, timeout=20)
        return row

    def _find_visible_action_button(self, invoice_id, class_name):
        # The action buttons live in .actionButtonsWrapper (inside td.remarkstatus) -- the dedicated
        # td.Action column is empty/vestigial in the current markup. Look inside the SAME row we
        # opened the menu on (matched by invoice id), not just the first row on the page.
        def _finder(d):
            for r in d.find_elements(*self.ROWS):
                try:
                    if invoice_id and self._invoice_id(r) != invoice_id:
                        continue
                    btn = r.find_element(
                        By.XPATH,
                        f".//div[contains(@class,'actionButtonsWrapper')]//span[contains(@class,'{class_name}')]",
                    )
                    return btn if btn.is_displayed() else False
                except Exception:
                    continue
            return False

        return self.wait_until(_finder, message=f"'{class_name}' action button never became visible")

    def _click_action_toggle(self, row):
        # The Action menu opens on hover -- jQuery binds mouseover/mouseout delegated on
        # .dmsActionMenu, there is no click handler and no <input value="Action"> element anymore.
        action_menu = row.find_element(By.CSS_SELECTOR, ".dmsActionMenu")
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", action_menu)
        self.driver.execute_script(
            "arguments[0].dispatchEvent(new MouseEvent('mouseover', {bubbles: true, cancelable: true}));",
            action_menu,
        )

    def click_edit_for_client(self, client_name, invoice_id=None):
        row = self._resolve_row(client_name, invoice_id)
        if row is None:
            raise TimeoutException(f"No My Sales data row for '{client_name}' appeared to click Edit on")
        inv = self._invoice_id(row)
        self._click_action_toggle(row)
        edit_btn = self._find_visible_action_button(inv, "editOrder")
        self.js_click(edit_btn)
        self.wait_until(
            lambda d: "EditSaleProductListing" in d.current_url,
            timeout=20,
            message="Did not navigate to EditSaleProductListing.html after clicking Edit",
        )
        attach_page_performance(self.driver, "Edit Sale page")
        return self

    def print_invoice_for_client(self, client_name, invoice_id=None):
        row = self._resolve_row(client_name, invoice_id)
        if row is None:
            raise TimeoutException(f"No My Sales data row for '{client_name}' appeared to click Print on")
        inv = self._invoice_id(row)
        main_handle = self.driver.current_window_handle
        self._click_action_toggle(row)
        print_btn = self._find_visible_action_button(inv, "GetInvoiceDetails")
        self.js_click(print_btn)
        self.wait_until(
            EC.visibility_of_element_located(self.PRINT_PREVIEW_TITLE),
            timeout=15,
            message="'Print Preview!' options dialog never appeared after clicking Print",
        )
        self.click(self.PRINT_PREVIEW_PRINT_BUTTON)
        self.wait_until(
            lambda d: len(d.window_handles) > 1, timeout=15, message="Invoice tab did not open after clicking Print"
        )
        new_handle = next(h for h in self.driver.window_handles if h != main_handle)
        self.driver.switch_to.window(new_handle)
        self.wait_until(
            lambda d: "OrderId" in d.current_url, timeout=15, message="Invoice tab never loaded a report URL"
        )
        url = self.driver.current_url
        time.sleep(1.5)
        screenshot = self.driver.get_screenshot_as_png()
        self.driver.close()
        self.driver.switch_to.window(main_handle)
        return url, screenshot
