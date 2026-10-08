import re
import time

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from selenium.webdriver.support.ui import WebDriverWait


class PurchaseReturnBatchPage:
    """Page object for Purchase Return (DMSPages/ReturnProduct.html).

    The product grid uses the same component as Sale Return: each row has a Saleable Item qty
    box (input.C1), a Damage Item qty box (input.C2) and a hamburger icon (span.ShowBatchWiseVariant)
    that opens a per-batch modal with an Apply button."""

    URL = "https://admin.massistcrm.com/DMSPages/ReturnProduct.html"

    ALERT_TITLE = (
        By.XPATH,
        "//span[contains(@class,'jconfirm-title')][starts-with(normalize-space(text()),'Alert')]",
    )

    def __init__(self, driver):
        self.driver = driver
        # This project's driver fixture sets a 60s IMPLICIT wait. That makes every "is this element
        # absent?" check (find_elements returning nothing) hang for 60s, so this page turns it off
        # and uses explicit waits instead.
        self.driver.implicitly_wait(0)

    # ---- small helpers (the main DMS project has no shared BasePage)
    def get(self, url):
        self.driver.get(url)

    def find_all(self, locator):
        return self.driver.find_elements(*locator)

    def wait_until(self, condition, timeout=20, message=""):
        return WebDriverWait(self.driver, timeout).until(condition, message)

    def js_click(self, element):
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        self.driver.execute_script("arguments[0].click();", element)

    def dismiss_blocking_alert(self, timeout=1):
        try:
            title_el = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(self.ALERT_TITLE)
            )
        except TimeoutException:
            return None
        box = title_el.find_element(By.XPATH, "ancestor::div[contains(@class,'jconfirm-box')]")
        message = box.find_element(By.CSS_SELECTOR, ".jconfirm-content").text.strip()
        self.js_click(box.find_element(By.XPATH, ".//div[contains(@class,'jconfirm-buttons')]/button"))
        try:
            WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(self.ALERT_TITLE))
        except TimeoutException:
            pass
        return message

    CUSTOMER_SEARCH_INPUT = (By.XPATH, "//input[@type='search']")

    PRODUCT_ROWS = (By.CSS_SELECTOR, "#productlist tbody tr")
    QTY_INPUTS = (By.CSS_SELECTOR, "#productlist tbody tr input.C1, #productlist tbody tr input.C2")
    FIELD_SELECTORS = {"saleable": "input.C1", "damage": "input.C2"}

    VISIBLE_JCONFIRM_BOXES = (By.CSS_SELECTOR, ".jconfirm-box")
    INVENTORY_ALERT_OK = (By.CSS_SELECTOR, ".jconfirm-box .btn-godown-inv-ok")

    # ------------------------------------------------------------------ open / supplier selection

    def open(self):
        self.get(self.URL)
        self.wait_until(
            EC.presence_of_element_located(self.CUSTOMER_SEARCH_INPUT),
            timeout=60,
            message="Purchase Return supplier search box never appeared",
        )
        return self

    @staticmethod
    def _wait_table_settled(wrapper, timeout=10):
        """Wait until 'Showing X To Y Of Z Entries' stops changing (search/redraw finished)."""
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
        def _visible_search(d):
            for el in d.find_elements(*self.CUSTOMER_SEARCH_INPUT):
                if el.is_displayed():
                    return el
            return False

        search = self.wait_until(_visible_search, timeout=60, message="Supplier search box never became visible")
        wrapper = search.find_element(By.XPATH, "./ancestor::div[contains(@class,'dataTables_wrapper')]")
        return search, wrapper

    @staticmethod
    def _norm(text):
        return re.sub(r"\s+", " ", (text or "")).strip().lower()

    def select_supplier(self, name, sub_category=None):
        """Select the supplier row whose name is exactly `name` and, if given, whose Sub Category
        column is exactly `sub_category` -- the same supplier name can be listed more than once
        with different sub categories (e.g. 'Vadilal Industries Ltd.' / sub category 14)."""
        search, wrapper = self._customer_table()

        # Show every row on one page (scoped to this table) so the wanted row isn't on page 2.
        try:
            selects = wrapper.find_elements(By.CSS_SELECTOR, "select[name$='_length']") or \
                wrapper.find_elements(By.CSS_SELECTOR, ".dataTables_length select")
            if selects:
                Select(selects[0]).select_by_value("-1")
                self._wait_table_settled(wrapper)
        except Exception as exc:
            print(f"Could not switch supplier list to 'All' (will page through instead): {exc}")

        search.clear()
        search.send_keys(name)
        self._wait_table_settled(wrapper)

        # Which column is 'Sub Category'? (header text, case/space-insensitive)
        headers = [self._norm(th.text) for th in wrapper.find_elements(By.CSS_SELECTOR, "thead th")]
        sub_col = next((i for i, h in enumerate(headers) if "sub" in h and "categ" in h), None)

        wanted_name = self._norm(name)
        wanted_sub = self._norm(sub_category) if sub_category is not None else None
        seen = []

        for _ in range(20):  # pages
            for row in wrapper.find_elements(By.CSS_SELECTOR, "tbody tr"):
                try:
                    cells = [self._norm(td.text) for td in row.find_elements(By.TAG_NAME, "td")]
                except StaleElementReferenceException:
                    continue
                if wanted_name not in cells:
                    continue
                if wanted_sub is not None:
                    if sub_col is not None and sub_col < len(cells):
                        matches_sub = cells[sub_col] == wanted_sub
                    else:
                        matches_sub = wanted_sub in cells
                    if not matches_sub:
                        seen.append(cells)
                        continue
                select_btn = row.find_element(
                    By.XPATH,
                    ".//a[contains(normalize-space(.),'Select')] | .//button[contains(normalize-space(.),'Select')]",
                )
                self.js_click(select_btn)
                self.dismiss_blocking_alert(timeout=3)
                self.wait_for_grid_loaded()
                return self

            next_btn = wrapper.find_elements(By.CSS_SELECTOR, ".paginate_button.next")
            if not next_btn or "disabled" in (next_btn[0].get_attribute("class") or ""):
                break
            target = next_btn[0].find_elements(By.TAG_NAME, "a") or [next_btn[0]]
            self.js_click(target[0])
            self._wait_table_settled(wrapper)

        raise TimeoutException(
            f"No supplier row named '{name}'"
            + (f" with Sub Category '{sub_category}'" if sub_category is not None else "")
            + (f" -- same-name rows seen: {seen}" if seen else "")
        )

    def wait_for_grid_loaded(self, timeout=120):
        """The product grid loads by AJAX after selecting the supplier and can be slow under load."""
        def _ready(d):
            self.dismiss_blocking_alert(timeout=0.3)
            return len(d.find_elements(*self.QTY_INPUTS)) > 0

        self.wait_until(_ready, timeout=timeout, message="Purchase Return product grid never loaded")
        return self

    # ------------------------------------------------------------------ product rows / quantities

    def row_count(self):
        return len(self.find_all(self.PRODUCT_ROWS))

    def _row(self, index):
        return self.find_all(self.PRODUCT_ROWS)[index]

    def product_name(self, index):
        row = self._row(index)
        try:
            return row.find_element(By.CSS_SELECTOR, "span.Variant_Name").get_attribute("product_name").strip()
        except Exception:
            return row.text.split("\n")[0].strip()

    def _qty_input(self, index, field):
        return self._row(index).find_element(By.CSS_SELECTOR, self.FIELD_SELECTORS[field])

    def get_qty(self, index, field):
        """Current value of the Saleable ('saleable') or Damage ('damage') box on that row."""
        for _ in range(3):
            try:
                return (self._qty_input(index, field).get_attribute("value") or "").strip()
            except StaleElementReferenceException:
                time.sleep(0.5)
        return (self._qty_input(index, field).get_attribute("value") or "").strip()

    def enter_qty(self, index, field, qty):
        inp = self._qty_input(index, field)
        self.js_click(inp)
        inp.clear()
        inp.send_keys(str(qty))
        inp.send_keys(Keys.TAB)
        time.sleep(1)  # the blur triggers a row recalculation; let it settle
        return self

    # ------------------------------------------------------------------ batch (hamburger) modal

    def _visible_batch_modal(self, timeout=30):
        """The per-batch modal opened by the hamburger: a visible jconfirm box with an Apply button."""
        def _condition(d):
            for box in d.find_elements(*self.VISIBLE_JCONFIRM_BOXES):
                try:
                    if not box.is_displayed():
                        continue
                    if box.find_elements(By.XPATH, ".//button[normalize-space(.)='Apply']"):
                        return box
                except StaleElementReferenceException:
                    continue
            return False

        return self.wait_until(_condition, timeout=timeout, message="Batch modal (with Apply) never appeared")

    def open_batch_modal(self, index):
        time.sleep(1)  # let the row finish recalculating after the qty was entered
        hamburger = self._row(index).find_element(By.CSS_SELECTOR, "span.ShowBatchWiseVariant")
        self.js_click(hamburger)
        return self._visible_batch_modal()

    def batch_modal_text(self):
        return self._visible_batch_modal().text.strip()

    def batch_modal_inputs(self):
        """Values currently shown in the modal's own input boxes (for the report)."""
        values = []
        for inp in self._visible_batch_modal().find_elements(By.CSS_SELECTOR, "input"):
            try:
                if inp.get_attribute("type") in ("text", "number", None, ""):
                    values.append((inp.get_attribute("class") or "", (inp.get_attribute("value") or "").strip()))
            except StaleElementReferenceException:
                continue
        return values

    def apply_batch_modal(self):
        """Click Apply, wait for the modal to close, and dismiss any follow-up alerts.
        Returns the text of any alert that appeared (e.g. an inventory warning), or None."""
        box = self._visible_batch_modal()
        self.js_click(box.find_element(By.XPATH, ".//button[normalize-space(.)='Apply']"))

        def _closed(d):
            for b in d.find_elements(*self.VISIBLE_JCONFIRM_BOXES):
                try:
                    if b.is_displayed() and b.find_elements(By.XPATH, ".//button[normalize-space(.)='Apply']"):
                        return False
                except StaleElementReferenceException:
                    continue
            return True

        try:
            self.wait_until(_closed, timeout=15, message="")
        except Exception:
            pass

        alerts = []
        for _ in range(3):
            try:
                ok = self.wait_until(EC.visibility_of_element_located(self.INVENTORY_ALERT_OK), timeout=2)
                box_text = ok.find_element(By.XPATH, "ancestor::div[contains(@class,'jconfirm-box')]").text
                alerts.append(box_text.strip().replace("\n", " | "))
                self.js_click(ok)
                time.sleep(0.5)
            except Exception:
                break
        generic = self.dismiss_blocking_alert(timeout=1)
        if generic:
            alerts.append(generic)
        time.sleep(1)  # let the row re-render with the applied values
        return " || ".join(alerts) or None

    def close_batch_modal(self):
        """Close the modal WITHOUT applying (Cancel, else the X icon)."""
        box = self._visible_batch_modal()
        buttons = box.find_elements(By.XPATH, ".//button[normalize-space(.)='Cancel']") or \
            box.find_elements(By.CSS_SELECTOR, ".jconfirm-closeIcon")
        if buttons:
            self.js_click(buttons[0])
        time.sleep(0.5)
        return self

    @staticmethod
    def batch_total(batch_text):
        """Inventory total shown in the modal's 'Total ...' line, or None if not shown."""
        for line in batch_text.splitlines():
            if line.strip().lower().startswith("total"):
                numbers = re.findall(r"-?\d+(?:\.\d+)?", line.split(":", 1)[-1])
                if numbers:
                    return float(numbers[0])
        return None
