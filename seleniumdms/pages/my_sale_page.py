import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from pages.base_page import BasePage
from utilities.performance import attach_page_performance


class MySalePage(BasePage):
    URL = "https://admin.massistcrm.com/DMSPages/Reports/MyPreviousSale.html"

    SEARCH_INPUT = (By.CSS_SELECTOR, "#tbl_order_grid_filter input[type='search']")
    ROWS = (By.CSS_SELECTOR, "#tbl_order_grid tbody tr")

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

    def search(self, text):
        box = self.find(self.SEARCH_INPUT)
        box.clear()
        box.send_keys(text)
        self.wait_until(
            lambda d: len(d.find_elements(*self.ROWS)) > 0,
            timeout=15,
            message=f"No My Sales rows appeared after searching for '{text}'",
        )
        return self

    def _first_data_row(self):
        # DataTables renders its own "No matching records found" placeholder as a <tr> too, so it
        # satisfies search()'s len(rows) > 0 wait just like a real result -- only a row with a
        # td.SaleId cell is an actual data row.
        rows = self.find_all(self.ROWS)
        if not rows:
            return None
        row = rows[0]
        return row if row.find_elements(By.CSS_SELECTOR, "td.SaleId") else None

    def _wait_for_data_row(self, client_name, timeout=20, poll_interval=2):
        # A sale/return that was just finalized can take a moment to become searchable here, during
        # which the grid shows the "No matching records found" placeholder -- re-searching (not just
        # re-checking the DOM) gives the backend repeated chances to catch up.
        deadline = time.time() + timeout
        while True:
            self.search(client_name)
            row = self._first_data_row()
            if row is not None:
                return row
            if time.time() >= deadline:
                return None
            time.sleep(poll_interval)

    def get_latest_sale_for_client(self, client_name):
        row = self._wait_for_data_row(client_name)
        if row is None:
            return None
        return {
            "invoice_id": row.find_element(By.CSS_SELECTOR, "td.SaleId").text.split("\n")[0].strip(),
            "party_name": row.find_element(By.CSS_SELECTOR, "td:nth-child(5)").text.strip(),
            "no_of_items": row.find_element(By.CSS_SELECTOR, "td:nth-child(8)").text.strip(),
            "amount": row.find_element(By.CSS_SELECTOR, "td.OrderAmt").text.strip(),
            "sale_qty": row.find_element(By.CSS_SELECTOR, "td.PreviousQty").text.strip(),
        }

    def _find_visible_action_button(self, class_name):
        # The action buttons live in .actionButtonsWrapper (inside td.remarkstatus) now -- the
        # dedicated td.Action column is empty/vestigial in the current markup.
        def _finder(d):
            try:
                r = d.find_elements(*self.ROWS)[0]
                btn = r.find_element(
                    By.XPATH,
                    f".//div[contains(@class,'actionButtonsWrapper')]//span[contains(@class,'{class_name}')]",
                )
                return btn if btn.is_displayed() else False
            except Exception:
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

    def click_edit_for_client(self, client_name):
        row = self._wait_for_data_row(client_name)
        if row is None:
            raise TimeoutException(f"No My Sales data row for '{client_name}' appeared to click Edit on")
        self._click_action_toggle(row)
        edit_btn = self._find_visible_action_button("editOrder")
        self.js_click(edit_btn)
        self.wait_until(
            lambda d: "EditSaleProductListing" in d.current_url,
            timeout=20,
            message="Did not navigate to EditSaleProductListing.html after clicking Edit",
        )
        attach_page_performance(self.driver, "Edit Sale page")
        return self

    def print_invoice_for_client(self, client_name):
        row = self._wait_for_data_row(client_name)
        if row is None:
            raise TimeoutException(f"No My Sales data row for '{client_name}' appeared to click Print on")
        main_handle = self.driver.current_window_handle
        self._click_action_toggle(row)
        print_btn = self._find_visible_action_button("GetInvoiceDetails")
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
