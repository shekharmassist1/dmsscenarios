import re
import time

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


def _parse_number(text):
    """First number in text, keeping a minus sign and ignoring thousands commas ('-12 Carton' -> -12)."""
    match = re.search(r"-?\d+(?:\.\d+)?", (text or "").replace(",", ""))
    return float(match.group()) if match else 0.0


class BillEnterKeyPage:
    """Bill/New Invoice page, used to check selecting items with the ENTER key on later grid pages."""

    URL = "https://admin.massistcrm.com/DMSPages/SaleProduct.html"

    CUSTOMER_SEARCH_INPUT = (By.XPATH, "//input[@type='search']")
    PRODUCT_ROWS = (By.CSS_SELECTOR, "#productlist tbody tr")
    QTY_INPUTS = (By.CSS_SELECTOR, "#productlist tbody tr input.SaleQty")
    CURRENT_PAGE = (By.CSS_SELECTOR, "#productlist_paginate .paginate_button.current")
    NEXT_BUTTON = (By.CSS_SELECTOR, "#productlist_paginate .paginate_button.next")
    PREVIOUS_BUTTON = (By.CSS_SELECTOR, "#productlist_paginate .paginate_button.previous")
    GRID_INFO = (By.ID, "productlist_info")

    CALC_BUTTON = (By.ID, "lblCalculate")
    SUMMARY_TOTAL_ITEM = (By.CSS_SELECTOR, "#divitem span")
    SUMMARY_FINAL_AMOUNT = (By.CSS_SELECTOR, "#totalPayAmt span")
    VIEW_SELECTED_BUTTON = (By.ID, "btnViewAllSelectedItems")
    SELECTED_POPOVER = (By.ID, "viewSelectedItemsPopover")

    VISIBLE_JCONFIRM_BOXES = (By.CSS_SELECTOR, ".jconfirm-box")

    def __init__(self, driver):
        self.driver = driver
        # This project's driver fixture sets a 60s IMPLICIT wait, which makes every "is it there?"
        # check hang for a minute when the answer is no. Use explicit waits only.
        self.driver.implicitly_wait(0)

    # ------------------------------------------------------------------ helpers

    def wait_until(self, condition, timeout=20, message=""):
        return WebDriverWait(self.driver, timeout).until(condition, message)

    def js_click(self, element):
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        self.driver.execute_script("arguments[0].click();", element)

    def dismiss_dialogs(self, timeout=2):
        """Close any visible jconfirm dialog (alerts such as 'Insufficient inventory') by clicking its
        first button. Returns the texts of the dialogs that were closed."""
        texts = []
        end = time.time() + timeout
        while time.time() < end:
            closed_one = False
            for box in self.driver.find_elements(*self.VISIBLE_JCONFIRM_BOXES):
                try:
                    if not box.is_displayed():
                        continue
                    buttons = box.find_elements(By.CSS_SELECTOR, ".jconfirm-buttons button")
                    if not buttons:
                        continue
                    texts.append(box.text.strip().replace("\n", " | "))
                    self.js_click(buttons[0])
                    closed_one = True
                    time.sleep(0.5)
                except StaleElementReferenceException:
                    continue
            if not closed_one:
                time.sleep(0.3)
        return texts

    @staticmethod
    def _wait_table_settled(wrapper, timeout=10):
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

    # ------------------------------------------------------------------ open + customer

    def open(self):
        self.driver.get(self.URL)
        self.wait_until(
            EC.presence_of_element_located(self.CUSTOMER_SEARCH_INPUT),
            timeout=60,
            message="Bill/New Invoice customer search never appeared",
        )
        return self

    def select_customer(self, name):
        """Exact-name customer selection (the search matches each word separately, so 'Demo Dealer 4'
        also returns 'Demo Dealer 11', etc.). Shows all rows, takes the exact match, pages as fallback."""
        def _visible_search(d):
            for el in d.find_elements(*self.CUSTOMER_SEARCH_INPUT):
                if el.is_displayed():
                    return el
            return False

        search = self.wait_until(_visible_search, timeout=60, message="Customer search box never became visible")
        wrapper = search.find_element(By.XPATH, "./ancestor::div[contains(@class,'dataTables_wrapper')]")
        try:
            selects = wrapper.find_elements(By.CSS_SELECTOR, "select[name$='_length']")
            if selects:
                Select(selects[0]).select_by_value("-1")
                self._wait_table_settled(wrapper)
        except Exception:
            pass

        search.clear()
        search.send_keys(name)
        self._wait_table_settled(wrapper)

        row_xpath = f".//tbody/tr[td[normalize-space(.)='{name}']]"
        for _ in range(20):
            rows = wrapper.find_elements(By.XPATH, row_xpath)
            if rows:
                btn = rows[0].find_element(
                    By.XPATH, ".//a[contains(normalize-space(.),'Select')] | .//button[contains(normalize-space(.),'Select')]"
                )
                self.js_click(btn)
                self.dismiss_dialogs(timeout=2)
                self.wait_until(
                    lambda d: len(d.find_elements(*self.QTY_INPUTS)) > 0,
                    timeout=90,
                    message=f"Product grid never loaded after selecting '{name}'",
                )
                return self
            nxt = wrapper.find_elements(By.CSS_SELECTOR, ".paginate_button.next")
            if not nxt or "disabled" in (nxt[0].get_attribute("class") or ""):
                break
            target = nxt[0].find_elements(By.TAG_NAME, "a") or [nxt[0]]
            self.js_click(target[0])
            self._wait_table_settled(wrapper)
        raise TimeoutException(f"Customer '{name}' not found in the customer list")

    # ------------------------------------------------------------------ product grid paging

    def current_page(self):
        try:
            return int(self.driver.find_element(*self.CURRENT_PAGE).text.strip())
        except Exception:
            return None

    def _click_pager(self, locator):
        btns = self.driver.find_elements(*locator)
        if not btns or "disabled" in (btns[0].get_attribute("class") or ""):
            return False
        before = self.current_page()
        target = btns[0].find_elements(By.TAG_NAME, "a") or [btns[0]]
        self.js_click(target[0])
        try:
            self.wait_until(lambda d: self.current_page() != before, timeout=15)
        except TimeoutException:
            return False
        time.sleep(0.5)
        return True

    def go_to_page(self, page_number):
        """Move the product grid to the given page with Next/Previous (page numbers in between are
        hidden behind '...', so they can't always be clicked directly)."""
        for _ in range(60):
            current = self.current_page()
            if current == page_number:
                return True
            moved = self._click_pager(self.NEXT_BUTTON if (current or 0) < page_number else self.PREVIOUS_BUTTON)
            if not moved:
                return self.current_page() == page_number
        return self.current_page() == page_number

    def last_page_number(self):
        numbers = [
            int(a.text) for a in self.driver.find_elements(By.CSS_SELECTOR, "#productlist_paginate .paginate_button")
            if a.text.strip().isdigit()
        ]
        return max(numbers) if numbers else 1

    # ------------------------------------------------------------------ rows on the current page

    def rows_on_page(self):
        """[{index, item_code, name, stock}] for the rows currently shown."""
        result = []
        for i, row in enumerate(self.driver.find_elements(*self.PRODUCT_ROWS)):
            try:
                if not row.find_elements(By.CSS_SELECTOR, "input.SaleQty"):
                    continue
                name_cell = row.find_element(By.CSS_SELECTOR, "td.Variant_Name")
                codes = name_cell.find_elements(By.CSS_SELECTOR, "label.barcode")
                item_code = (codes[0].get_attribute("barcode") or codes[0].text).strip() if codes else ""
                names = name_cell.find_elements(By.CSS_SELECTOR, "span.Variant_Name")
                name = (names[0].get_attribute("product_name") or names[0].text).strip() if names else name_cell.text.strip()
                stock_cells = row.find_elements(By.CSS_SELECTOR, "td.InventoryLabel")
                stock = _parse_number(stock_cells[0].text) if stock_cells else 0.0
                result.append({"index": i, "item_code": item_code, "name": name, "stock": stock})
            except StaleElementReferenceException:
                continue
        return result

    def _row_by_code(self, item_code):
        for row in self.driver.find_elements(*self.PRODUCT_ROWS):
            try:
                codes = row.find_elements(By.CSS_SELECTOR, "td.Variant_Name label.barcode")
                if codes and (codes[0].get_attribute("barcode") or codes[0].text).strip() == item_code:
                    return row
            except StaleElementReferenceException:
                continue
        return None

    def qty_of(self, item_code):
        """Qty currently in the item's box, or None if the item isn't on the current page."""
        row = self._row_by_code(item_code)
        if row is None:
            return None
        return (row.find_element(By.CSS_SELECTOR, "input.SaleQty").get_attribute("value") or "").strip()

    def enter_qty_and_press_enter(self, item_code, qty):
        """Type the qty into the item's Sale Qty box and press ENTER (the keyboard way of selecting).
        Returns the texts of any dialogs that appeared and were dismissed."""
        row = self._row_by_code(item_code)
        if row is None:
            raise AssertionError(f"Item {item_code} is not on the current grid page ({self.current_page()})")
        inp = row.find_element(By.CSS_SELECTOR, "input.SaleQty")
        self.js_click(inp)
        inp.clear()
        inp.send_keys(str(qty))
        inp.send_keys(Keys.ENTER)
        time.sleep(2)  # let whatever ENTER triggers (recalc / redraw) finish
        return self.dismiss_dialogs(timeout=2)

    # ------------------------------------------------------------------ what got selected

    def calc_total_items(self):
        self.js_click(self.wait_until(EC.element_to_be_clickable(self.CALC_BUTTON), timeout=20))

        def _ready(d):
            self.dismiss_dialogs(timeout=0.3)
            return any(ch.isdigit() for ch in d.find_element(*self.SUMMARY_FINAL_AMOUNT).text)

        try:
            self.wait_until(_ready, timeout=30)
        except TimeoutException:
            pass
        self.dismiss_dialogs(timeout=2)
        return self.driver.find_element(*self.SUMMARY_TOTAL_ITEM).text.strip()

    def selected_item_codes(self):
        """Item codes listed in 'View All Selected Items' (empty list if the popover can't be read)."""
        try:
            self.js_click(self.wait_until(EC.element_to_be_clickable(self.VIEW_SELECTED_BUTTON), timeout=15))
            popover = self.wait_until(EC.visibility_of_element_located(self.SELECTED_POPOVER), timeout=15)
            codes = []
            for r in popover.find_elements(By.CSS_SELECTOR, "table tbody tr"):
                cells = r.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 3:
                    codes.append(cells[1].text.strip())
            try:
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            except Exception:
                pass
            return codes
        except Exception:
            return []
