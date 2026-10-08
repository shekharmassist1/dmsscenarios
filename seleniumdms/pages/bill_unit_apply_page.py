import re
import time

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from pages.product_page import ProductPage


class BillUnitApplyPage(ProductPage):
    """Bill/New Invoice checks around the row's unit type (Carton / Piece) and the hamburger
    (batch) popup's Apply button."""

    HAMBURGER = (By.CSS_SELECTOR, "span.ShowBatchWiseVariant")
    JCONFIRM_BOXES = (By.CSS_SELECTOR, ".jconfirm-box")

    # ------------------------------------------------------------------ pack size and unit type

    @staticmethod
    def pieces_per_carton(product_name):
        """Pieces in one carton from the pack size in the name, e.g. '[1*10]' -> 10,
        '[100 Gms*100]' -> 100, '[5KGS*5]' -> 5, '[1 * 30]' -> 30. None if no pack size shown."""
        match = re.search(r"\[[^\]]*\*\s*(\d+)\s*\]", product_name or "")
        return int(match.group(1)) if match else None

    def _unit_select(self, index):
        """The row's unit dropdown: the <select> whose options include Carton and Piece."""
        row = self.find_all(self.PRODUCT_ROWS)[index]
        for sel in row.find_elements(By.TAG_NAME, "select"):
            texts = [o.text.strip().lower() for o in sel.find_elements(By.TAG_NAME, "option")]
            if any(t.startswith("cart") for t in texts) and any(t.startswith("pi") or t.startswith("pc") for t in texts):
                return sel
        return None

    def unit_options(self, index):
        sel = self._unit_select(index)
        return [o.text.strip() for o in sel.find_elements(By.TAG_NAME, "option")] if sel else []

    def current_unit(self, index):
        sel = self._unit_select(index)
        return Select(sel).first_selected_option.text.strip() if sel else None

    def set_unit(self, index, kind):
        """kind = 'carton' or 'piece'. Selects the matching option and fires the change event."""
        sel = self._unit_select(index)
        if sel is None:
            raise AssertionError(f"Row {index} has no Carton/Piece unit dropdown")
        prefixes = ("cart",) if kind == "carton" else ("pi", "pc")
        for opt in sel.find_elements(By.TAG_NAME, "option"):
            if opt.text.strip().lower().startswith(prefixes):
                Select(sel).select_by_visible_text(opt.text)
                self.driver.execute_script(
                    "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", sel
                )
                time.sleep(1)
                self.dismiss_any_alert(timeout=1)
                return opt.text.strip()
        raise AssertionError(f"Row {index}: no '{kind}' option in {self.unit_options(index)}")

    def find_row_with_multi_piece_carton(self, max_rows=60):
        """First row (index, info) whose pack has more than 1 piece per carton, that has a
        Carton/Piece dropdown and at least 1 in stock. Shows all rows if the first page has none."""
        def _scan():
            for i in range(min(len(self.find_all(self.PRODUCT_ROWS)), max_rows)):
                try:
                    info = self.product_row(i)
                except Exception:
                    continue
                per_carton = self.pieces_per_carton(info["display_name"])
                if per_carton and per_carton > 1 and info["available_stock"] >= 1 and self._unit_select(i) is not None:
                    info["pieces_per_carton"] = per_carton
                    return i, info
            return None

        found = _scan()
        if found is None:
            self.show_all_products()
            found = _scan()
        if found is None:
            raise AssertionError("No in-stock product with more than 1 piece per carton and a Carton/Piece dropdown found")
        return found

    # ------------------------------------------------------------------ hamburger popup + Apply

    def open_hamburger(self, index, timeout=30):
        """Click the row's hamburger and return the popup that opens (a visible jconfirm box)."""
        time.sleep(1)
        row = self.find_all(self.PRODUCT_ROWS)[index]
        self.js_click(row.find_element(*self.HAMBURGER))

        def _popup(d):
            for box in d.find_elements(*self.JCONFIRM_BOXES):
                try:
                    if box.is_displayed() and box.text.strip():
                        return box
                except StaleElementReferenceException:
                    continue
            return False

        return self.wait_until(_popup, timeout=timeout, message="Hamburger popup never opened")

    def apply_button_state(self, box):
        """{'found', 'visible', 'enabled', 'details'} for the popup's Apply button. 'enabled' is False
        if the button is missing/hidden, has the disabled attribute, a 'disabled' class,
        aria-disabled=true, or pointer-events:none."""
        buttons = box.find_elements(By.XPATH, ".//button[normalize-space(.)='Apply'] | .//*[@value='Apply']")
        if not buttons:
            return {"found": False, "visible": False, "enabled": False, "details": "no Apply button in the popup"}
        btn = buttons[0]
        visible = btn.is_displayed()
        disabled_attr = btn.get_attribute("disabled")
        cls = btn.get_attribute("class") or ""
        aria = (btn.get_attribute("aria-disabled") or "").lower()
        pointer = self.driver.execute_script("return getComputedStyle(arguments[0]).pointerEvents;", btn)
        opacity = self.driver.execute_script("return getComputedStyle(arguments[0]).opacity;", btn)
        enabled = (
            visible
            and btn.is_enabled()
            and disabled_attr is None
            and "disabled" not in cls.lower()
            and aria != "true"
            and pointer != "none"
        )
        details = (f"visible={visible} is_enabled={btn.is_enabled()} disabled_attr={disabled_attr!r} "
                   f"class={cls!r} aria-disabled={aria!r} pointer-events={pointer!r} opacity={opacity!r}")
        return {"found": True, "visible": visible, "enabled": enabled, "details": details}

    def close_popup_without_applying(self, box):
        for locator in ((By.XPATH, ".//button[normalize-space(.)='Cancel']"),
                        (By.CSS_SELECTOR, ".jconfirm-closeIcon"),
                        (By.XPATH, ".//button[normalize-space(.)='Close']")):
            els = [e for e in box.find_elements(*locator) if e.is_displayed()]
            if els:
                self.js_click(els[0])
                break
        try:
            self.wait_until(lambda d: not box.is_displayed(), timeout=10)
        except (TimeoutException, StaleElementReferenceException):
            pass
        time.sleep(0.5)
