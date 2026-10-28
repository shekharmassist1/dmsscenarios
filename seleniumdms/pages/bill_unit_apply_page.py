import re
import time

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from pages.product_page import ProductPage
from utilities.known_issues import is_known_problem


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
        row = self.product_row_el(index)
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
        """kind = 'carton' or 'piece'. Since the DMS UI update the row redraws as soon as the unit
        changes (Auto Calculate), so: select the option (Selenium fires the change itself), wait,
        re-find the row's dropdown and verify the unit stuck; retry up to 3 times."""
        prefixes = ("cart",) if kind == "carton" else ("pi", "pc")
        shown = None
        for attempt in range(3):
            sel = self._unit_select(index)
            if sel is None:
                raise AssertionError(f"Row {index} has no Carton/Piece unit dropdown")
            try:
                target = next((o.text for o in sel.find_elements(By.TAG_NAME, "option")
                               if o.text.strip().lower().startswith(prefixes)), None)
                if target is None:
                    raise AssertionError(f"Row {index}: no '{kind}' option in {self.unit_options(index)}")
                Select(sel).select_by_visible_text(target)
            except StaleElementReferenceException:
                pass
            time.sleep(1.5)
            self.dismiss_any_alert(timeout=1)
            try:
                sel = self._unit_select(index)
                shown = Select(sel).first_selected_option.text.strip() if sel is not None else None
            except StaleElementReferenceException:
                shown = None
            if shown and shown.lower().startswith(prefixes):
                return shown
        raise AssertionError(f"Row {index}: unit would not stay on {kind!r} (shows {shown!r} after 3 tries)")

    def find_row_with_multi_piece_carton(self, max_rows=60):
        """First row (index, info) whose pack has more than 1 piece per carton, that has a
        Carton/Piece dropdown and at least 1 in stock. Shows all rows if the first page has none."""
        def _scan():
            for i in range(min(len(self.find_all(self.PRODUCT_ROWS)), max_rows)):
                try:
                    info = self.product_row(i)
                except Exception:
                    continue
                if is_known_problem(info.get("display_name")):
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
        row = self.product_row_el(index)
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
        """{'found', 'visible', 'enabled', 'details'} for the popup's Apply button.

        The app disables Apply by styling its CONTAINER (div.jconfirm-buttons gets
        'cursor: not-allowed; opacity: 0.5'), not the button itself -- so the button and every parent
        up to the popup are checked. 'enabled' is False if any of them has the disabled attribute, a
        'disabled' class, aria-disabled=true, pointer-events:none, cursor:not-allowed or opacity < 1,
        or if the button is missing/hidden."""
        buttons = box.find_elements(By.XPATH, ".//button[normalize-space(.)='Apply'] | .//*[@value='Apply']")
        if not buttons:
            return {"found": False, "visible": False, "enabled": False, "details": "no Apply button in the popup"}
        btn = buttons[0]
        end = time.time() + 3
        while time.time() < end:
            try:
                if float(self.driver.execute_script("return getComputedStyle(arguments[0]).opacity", box)) >= 0.99:
                    break
            except Exception:
                break
            time.sleep(0.2)
        visible = btn.is_displayed()
        chain = self.driver.execute_script(
            """
            var el = arguments[0], stop = arguments[1], out = [];
            while (el && el.nodeType === 1) {
                var cs = getComputedStyle(el);
                out.push({
                    tag: el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).trim().split(/\\s+/).join('.') : ''),
                    disabled: el.hasAttribute('disabled'),
                    cls: String(el.className || ''),
                    aria: (el.getAttribute('aria-disabled') || '').toLowerCase(),
                    pointer: cs.pointerEvents, cursor: cs.cursor, opacity: parseFloat(cs.opacity)
                });
                if (el === stop) break;
                el = el.parentElement;
            }
            return out;
            """,
            btn, box,
        ) or []
        reasons = []
        for node in chain:
            if node["disabled"]:
                reasons.append(f"{node['tag']} has disabled attribute")
            if "disabled" in node["cls"].lower().split():
                reasons.append(f"{node['tag']} has class 'disabled'")
            if node["aria"] == "true":
                reasons.append(f"{node['tag']} aria-disabled=true")
            if node["pointer"] == "none":
                reasons.append(f"{node['tag']} pointer-events:none")
            if node["cursor"] == "not-allowed":
                reasons.append(f"{node['tag']} cursor:not-allowed")
            # The popup box itself fades in (opacity 0 -> 1) when it opens: that is animation, not a
            # disabled state, so its own opacity is ignored (the buttons container's 0.5 still counts).
            if node["opacity"] is not None and node["opacity"] < 0.99 and "jconfirm-box" not in node["cls"]:
                reasons.append(f"{node['tag']} opacity {node['opacity']}")
        enabled = visible and btn.is_enabled() and not reasons
        details = (f"visible={visible} is_enabled={btn.is_enabled()} "
                   + ("disabled because: " + "; ".join(reasons) if reasons else "no disabling style on the button or its containers"))
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
