import re
import time

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from pages.product_page import ProductPage


def _num(text):
    match = re.search(r"-?\d+(?:\.\d+)?", str(text or "").replace(",", ""))
    return float(match.group()) if match else None


class BillFilterPage(ProductPage):
    """Bill/New Invoice: the Clear button and the Group1 (main product category) filter."""

    CLEAR_BUTTON = (By.XPATH, "//span[normalize-space()='Clear'] | //button[normalize-space()='Clear']")
    GROUP1_SELECT = (By.ID, "ddlProductMaincategory")
    JCONFIRM_BOXES = (By.CSS_SELECTOR, ".jconfirm-box")

    # ------------------------------------------------------------------ Clear

    def click_clear_and_ok(self):
        """Click Clear and confirm with OK/Yes. Returns the confirmation text (or None)."""
        btn = next((b for b in self.driver.find_elements(*self.CLEAR_BUTTON) if b.is_displayed()), None)
        if btn is None:
            raise AssertionError("Clear button not found")
        self.js_click(btn)
        end, text = time.time() + 10, None
        while time.time() < end:
            for box in self.driver.find_elements(*self.JCONFIRM_BOXES):
                try:
                    if not box.is_displayed():
                        continue
                    buttons = box.find_elements(By.CSS_SELECTOR, ".jconfirm-buttons button")
                    ok = next((b for b in buttons if b.text.strip().lower().rstrip("!.") in ("ok", "yes", "yes, clear", "clear")), None)
                    ok = ok or (buttons[0] if buttons else None)
                    if ok is not None:
                        text = box.text.strip()
                        self.js_click(ok)
                        time.sleep(1.5)
                        return text
                except StaleElementReferenceException:
                    continue
            time.sleep(0.3)
        return text

    def calculate_allowing_empty(self):
        """Click Calc and return the header, also when the cart is empty (an alert may appear and
        Final Amount may stay blank)."""
        try:
            self.click_calc()
        except Exception:
            self.dismiss_any_alert(timeout=2)
        return self.get_summary()

    # ------------------------------------------------------------------ Group1 filter

    def group1_options(self):
        sel = self.driver.find_element(*self.GROUP1_SELECT)
        opts = []
        for o in sel.find_elements(By.TAG_NAME, "option"):
            value, text = (o.get_attribute("value") or "").strip(), o.text.strip()
            if value and value not in ("0", "-1") and "all" not in text.lower():
                opts.append((value, text))
        return opts

    def select_group1(self, value):
        """Choose a Group1 option (select2 dropdown) and wait for the product grid to reload."""
        before = self._grid_signature()
        self.driver.execute_script(
            "var s = document.getElementById('ddlProductMaincategory');"
            "if (window.jQuery) { jQuery(s).val(arguments[0]).trigger('change'); }"
            "else { s.value = arguments[0]; s.dispatchEvent(new Event('change', {bubbles: true})); }",
            value,
        )
        end = time.time() + 30
        while time.time() < end and self._grid_signature() == before:
            time.sleep(0.5)
        time.sleep(2)
        self.dismiss_any_alert(timeout=1)
        return Select(self.driver.find_element(*self.GROUP1_SELECT)).first_selected_option.text.strip()

    def _grid_signature(self):
        try:
            rows = self.find_all(self.PRODUCT_ROWS)
            return (len(rows), rows[0].text[:80] if rows else "")
        except Exception:
            return None

    # ------------------------------------------------------------------ rows

    def row_codes(self, limit=None):
        """[(index, item_code, qty in the box)] for the rows currently shown, in order."""
        out = []
        rows = self.find_all(self.PRODUCT_ROWS)
        for i in range(len(rows) if limit is None else min(limit, len(rows))):
            try:
                info = self.product_row(i)
                out.append((i, info["item_code"], (info["qty_input"].get_attribute("value") or "").strip()))
            except Exception:
                continue
        return out

    def first_in_stock_row_excluding(self, codes, min_qty=1):
        for i, code, _ in self.row_codes():
            if code in codes:
                continue
            try:
                if self.product_row(i)["available_stock"] >= min_qty:
                    return i
            except Exception:
                continue
        return None
