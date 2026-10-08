import re
import time

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


def to_number(text):
    """First number in text ('Rs. 1,234.50' -> 1234.5, '-12' -> -12), or None."""
    match = re.search(r"-?\d+(?:\.\d+)?", str(text or "").replace(",", ""))
    return float(match.group()) if match else None


class SaleReturnCartPage:
    """Sale Return (Without Reference): select items, remove items, Save, and read back the
    Calc header and 'View All Selected Items' so they can be compared."""

    URL = "https://admin.massistcrm.com/DMSPages/ProductReceived.html"

    CUSTOMER_SEARCH_INPUT = (By.XPATH, "//input[@type='search']")
    BILL_FOR_SELECT = (By.ID, "ddlBillFor")
    GO_BUTTON = (By.XPATH, "//button[normalize-space()='Go!']")

    PRODUCT_ROWS = (By.CSS_SELECTOR, "#productlist tbody tr")
    SALEABLE_INPUTS = (By.CSS_SELECTOR, "#productlist tbody tr input.C1")

    CALC_BUTTON = (By.ID, "lblCalculate")
    SUMMARY_TOTAL_ITEM = (By.CSS_SELECTOR, "#divitem span")
    SUMMARY_AMOUNT = (By.CSS_SELECTOR, "#divAmount span")
    SUMMARY_FINAL_AMOUNT = (By.CSS_SELECTOR, "#totalPayAmt span")

    VIEW_SELECTED_BUTTON = (By.ID, "btnViewAllSelectedItems")
    SELECTED_POPOVER = (By.ID, "viewSelectedItemsPopover")

    SAVE_BUTTON = (By.ID, "cartItemBtn")
    RECEIVE_GOODS_BUTTON = (By.ID, "btnProductsRecieve")

    JCONFIRM_BOXES = (By.CSS_SELECTOR, ".jconfirm-box")
    INVENTORY_ALERT_OK = (By.CSS_SELECTOR, ".jconfirm-box .btn-godown-inv-ok")

    def __init__(self, driver):
        self.driver = driver
        # The project's driver fixture sets a 60s IMPLICIT wait; it makes every "is it there?"
        # check hang for a minute when the answer is no. Use explicit waits only.
        self.driver.implicitly_wait(0)

    # ------------------------------------------------------------------ helpers

    def wait_until(self, condition, timeout=20, message=""):
        return WebDriverWait(self.driver, timeout).until(condition, message)

    def js_click(self, element):
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        self.driver.execute_script("arguments[0].click();", element)

    def _visible(self, locator):
        for el in self.driver.find_elements(*locator):
            try:
                if el.is_displayed():
                    return el
            except StaleElementReferenceException:
                continue
        return None

    def dismiss_alerts(self, timeout=2):
        """Close alert-style dialogs (inventory warnings, 'Alert!' boxes). Batch modals are left alone.
        Returns the texts of what was closed."""
        texts = []
        end = time.time() + timeout
        while time.time() < end:
            closed = False
            for box in self.driver.find_elements(*self.JCONFIRM_BOXES):
                try:
                    if not box.is_displayed() or "Batch List Of" in box.text:
                        continue
                    ok = box.find_elements(By.CSS_SELECTOR, ".btn-godown-inv-ok") or \
                        box.find_elements(By.CSS_SELECTOR, ".jconfirm-buttons button")
                    if not ok:
                        continue
                    texts.append(box.text.strip().replace("\n", " | "))
                    self.js_click(ok[0])
                    closed = True
                    time.sleep(0.5)
                except StaleElementReferenceException:
                    continue
            if not closed:
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

    # ------------------------------------------------------------------ open, customer, Without Reference

    def open(self):
        self.driver.get(self.URL)
        self.wait_until(
            EC.presence_of_element_located(self.CUSTOMER_SEARCH_INPUT), timeout=60,
            message="Sale Return customer search never appeared",
        )
        return self

    def select_customer(self, name):
        """Exact-name selection (the search matches words separately, so 'Demo 4' also returns
        'Demo Dealer 4' etc.). Shows all rows, takes the exact match, pages as a fallback."""
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
                self.dismiss_alerts(timeout=2)
                return self
            nxt = wrapper.find_elements(By.CSS_SELECTOR, ".paginate_button.next")
            if not nxt or "disabled" in (nxt[0].get_attribute("class") or ""):
                break
            target = nxt[0].find_elements(By.TAG_NAME, "a") or [nxt[0]]
            self.js_click(target[0])
            self._wait_table_settled(wrapper)
        raise TimeoutException(f"Customer '{name}' not found in the Sale Return customer list")

    def choose_without_reference(self):
        ddl = self.wait_until(
            EC.presence_of_element_located(self.BILL_FOR_SELECT), timeout=60,
            message="'Sale Return For...' dialog (ddlBillFor) never appeared after selecting the customer",
        )
        Select(ddl).select_by_visible_text("Without Reference")
        self.js_click(self.wait_until(EC.element_to_be_clickable(self.GO_BUTTON), timeout=20))

        def _grid_ready(d):
            self.dismiss_alerts(timeout=0.3)
            return len(d.find_elements(*self.SALEABLE_INPUTS)) > 0

        # The product list loads by a slow AJAX call (up to ~90s under load).
        self.wait_until(_grid_ready, timeout=150, message="Sale Return product grid never loaded after Go!")
        return self

    # ------------------------------------------------------------------ product rows

    def _rows(self):
        return self.driver.find_elements(*self.PRODUCT_ROWS)

    def row_count(self):
        return len(self._rows())

    def row_info(self, index):
        row = self._rows()[index]
        names = row.find_elements(By.CSS_SELECTOR, "span.Variant_Name")
        name = (names[0].get_attribute("product_name") or names[0].text).strip() if names else row.text.split("\n")[0]
        ids = row.find_elements(By.CSS_SELECTOR, "div.tbl_content_n")
        variant = (ids[0].get_attribute("variant_id") or ids[0].get_attribute("data-productid")) if ids else None
        return {"index": index, "name": name, "variant_id": variant or name}

    def _row_by_variant(self, variant_id):
        for i in range(self.row_count()):
            try:
                if self.row_info(i)["variant_id"] == variant_id:
                    return self._rows()[i]
            except StaleElementReferenceException:
                continue
        return None

    def _batch_modal(self, timeout=30):
        def _cond(d):
            for box in d.find_elements(*self.JCONFIRM_BOXES):
                try:
                    if box.is_displayed() and "Batch List Of" in box.text:
                        return box
                except StaleElementReferenceException:
                    continue
            return False
        return self.wait_until(_cond, timeout=timeout, message="'Batch List Of' modal never appeared")

    def row_has_batch_data(self, index):
        """Peek the row's hamburger 'Batch List' and close it with Cancel (nothing is changed)."""
        time.sleep(0.5)
        row = self._rows()[index]
        self.js_click(row.find_element(By.CSS_SELECTOR, "span.ShowBatchWiseVariant"))
        box = self._batch_modal()
        text = box.text
        cancel = box.find_elements(By.XPATH, ".//button[normalize-space(.)='Cancel']") or \
            box.find_elements(By.CSS_SELECTOR, ".jconfirm-closeIcon")
        if cancel:
            self.js_click(cancel[0])
        time.sleep(0.5)
        return "no data available" not in text.lower()

    def pick_rows(self, count, exclude_variants=()):
        """`count` rows (distinct products) that have batch data, skipping excluded ones."""
        picked, seen = [], set(exclude_variants)
        for i in range(self.row_count()):
            if len(picked) >= count:
                break
            info = self.row_info(i)
            if info["variant_id"] in seen:
                continue
            seen.add(info["variant_id"])
            try:
                if self.row_has_batch_data(i):
                    picked.append(info)
            except Exception:
                continue
        if len(picked) < count:
            raise AssertionError(f"Only found {len(picked)} usable product rows, needed {count}")
        return picked

    def set_saleable_qty(self, variant_id, qty):
        """Type qty into the item's Saleable box ('' or 0 = remove the item). Returns any alerts shown."""
        row = self._row_by_variant(variant_id)
        if row is None:
            raise AssertionError(f"Product {variant_id} not found in the grid")
        inp = row.find_element(By.CSS_SELECTOR, "input.C1")
        self.js_click(inp)
        inp.clear()
        if qty not in ("", None):
            inp.send_keys(str(qty))
        inp.send_keys(Keys.TAB)
        time.sleep(1)
        return self.dismiss_alerts(timeout=2)

    def saleable_qty(self, variant_id):
        row = self._row_by_variant(variant_id)
        if row is None:
            return None
        return (row.find_element(By.CSS_SELECTOR, "input.C1").get_attribute("value") or "").strip()

    # ------------------------------------------------------------------ Calc header + View Selected

    def calculate(self):
        """Click Calc and return the header: {'total_item', 'amount', 'final_amount'} (as text)."""
        self.dismiss_alerts(timeout=1)
        self.js_click(self.wait_until(EC.element_to_be_clickable(self.CALC_BUTTON), timeout=30))

        def _ready(d):
            self.dismiss_alerts(timeout=0.3)
            return any(ch.isdigit() for ch in d.find_element(*self.SUMMARY_FINAL_AMOUNT).text)

        try:
            self.wait_until(_ready, timeout=45)
        except TimeoutException:
            pass
        self.dismiss_alerts(timeout=2)
        return {
            "total_item": self.driver.find_element(*self.SUMMARY_TOTAL_ITEM).text.strip(),
            "amount": self.driver.find_element(*self.SUMMARY_AMOUNT).text.strip(),
            "final_amount": self.driver.find_element(*self.SUMMARY_FINAL_AMOUNT).text.strip(),
        }

    def view_selected_items(self):
        """Read 'View All Selected Items': {'rows': [{'text', 'value'}], 'footer_total': float|None}."""
        self.dismiss_alerts(timeout=1)
        self.js_click(self.wait_until(EC.element_to_be_clickable(self.VIEW_SELECTED_BUTTON), timeout=30))
        popover = self.wait_until(
            EC.visibility_of_element_located(self.SELECTED_POPOVER), timeout=30,
            message="View All Selected Items never opened",
        )
        time.sleep(1)
        rows = []
        for tr in popover.find_elements(By.CSS_SELECTOR, "table tbody tr"):
            cells = [td.text.strip() for td in tr.find_elements(By.TAG_NAME, "td")]
            if len(cells) < 3:
                continue
            numbers = [to_number(c) for c in cells if to_number(c) is not None]
            rows.append({"text": " | ".join(cells), "value": numbers[-1] if numbers else None})
        footer_total = None
        footer_cells = popover.find_elements(By.CSS_SELECTOR, "table tfoot tr td")
        footer_numbers = [to_number(td.text) for td in footer_cells if to_number(td.text) is not None]
        if footer_numbers:
            footer_total = footer_numbers[-1]
        try:
            closer = popover.find_elements(By.CSS_SELECTOR, ".vsi-close")
            if closer:
                self.js_click(closer[0])
            else:
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        except Exception:
            pass
        time.sleep(0.5)
        return {"rows": rows, "footer_total": footer_total}

    # ------------------------------------------------------------------ Save + close popup

    def save(self):
        """Click Save. Returns True if the save step (Receive Goods) appeared, plus any alerts."""
        self.dismiss_alerts(timeout=1)
        self.js_click(self.wait_until(EC.element_to_be_clickable(self.SAVE_BUTTON), timeout=30))
        alerts = []
        end = time.time() + 30
        while time.time() < end:
            if self._visible(self.RECEIVE_GOODS_BUTTON):
                return True, alerts
            alerts += self.dismiss_alerts(timeout=0.5)
        return False, alerts

    def _panel_close_button(self):
        """The round blue '×' at the top-left of the side panel that Save opens (the panel with
        Client Name / Total Qty / Payable / Goods Receive). Found by walking up from the Goods
        Receive button to the panel and looking for a small visible 'close'-type element in it or
        right next to it."""
        receive = self._visible(self.RECEIVE_GOODS_BUTTON)
        if receive is None:
            return None
        close_xpath = (
            ".//*[self::a or self::span or self::i or self::button or self::div or self::img]"
            "[contains(translate(@class,'CLOSE','close'),'close') or contains(translate(@id,'CLOSE','close'),'close')"
            " or normalize-space(.)='×' or normalize-space(.)='x' or normalize-space(.)='X'"
            " or normalize-space(.)='close' or normalize-space(.)='clear' or normalize-space(.)='cancel']"
        )
        node = receive
        for _ in range(8):  # climb from the button up to the panel (and its wrapper)
            try:
                node = node.find_element(By.XPATH, "./..")
            except Exception:
                break
            for el in node.find_elements(By.XPATH, close_xpath):
                try:
                    if el.is_displayed() and el.size.get("width", 99) <= 60 and el.size.get("height", 99) <= 60:
                        return el
                except StaleElementReferenceException:
                    continue
        return None

    def close_popup(self):
        """Close the side panel that Save opened, without receiving the goods, so items can be
        added again: first its round '×' button, then a generic close icon / Close-Cancel-Back
        button, then Escape."""
        btn = self._panel_close_button()
        if btn is not None:
            self.js_click(btn)
            time.sleep(1)
            if not self._visible(self.RECEIVE_GOODS_BUTTON):
                return "closed with the panel's round x button"
        candidates = [
            (By.CSS_SELECTOR, ".jconfirm-box .jconfirm-closeIcon"),
            (By.CSS_SELECTOR, ".modal.show .close, .modal.in .close, .modal-content .close"),
            (By.XPATH, "//*[self::button or self::a or self::span][normalize-space(.)='Close' or "
                       "normalize-space(.)='Cancel' or normalize-space(.)='Back' or normalize-space(.)='×']"),
        ]
        for locator in candidates:
            el = self._visible(locator)
            if el is not None:
                self.js_click(el)
                time.sleep(1)
                if not self._visible(self.RECEIVE_GOODS_BUTTON):
                    return "closed with " + locator[1][:40]
        try:
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(1)
        except Exception:
            pass
        return "closed with Escape" if not self._visible(self.RECEIVE_GOODS_BUTTON) else "popup still open"
