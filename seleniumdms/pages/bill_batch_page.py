import re
import time

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from pages.bill_unit_apply_page import BillUnitApplyPage


def _num(text):
    match = re.search(r"-?\d+(?:\.\d+)?", str(text or "").replace(",", ""))
    return float(match.group()) if match else None


class BillBatchPage(BillUnitApplyPage):
    """Bill/New Invoice (and Edit Sale) -- the row hamburger's batch popup: one line per batch with a
    qty box; Apply commits the split back to the row."""

    @staticmethod
    def _norm(text):
        return re.sub(r"\s+", " ", (text or "")).strip().lower()

    def popup_unit(self, box):
        """Unit shown in the popup title, e.g. 'Batch List Of ... With Unit Type : Carton' -> 'carton'."""
        m = re.search(r"unit\s*type\s*:\s*([A-Za-z]+)", box.text, flags=re.IGNORECASE)
        return m.group(1).lower() if m else None

    def _columns(self, box):
        """Header positions in the batch table (SrNo, Batch No, MRP, GST, Expiry Date, Mfg Date,
        RemainingDays, Price, Inventory, Carton Qty, Quantity, Free Qty)."""
        headers = [self._norm(th.text) for th in box.find_elements(By.CSS_SELECTOR, "thead th")]
        def find(pred):
            return next((i for i, h in enumerate(headers) if pred(h)), None)
        return {
            "batch": find(lambda h: "batch" in h),
            "stock": find(lambda h: "inventory" in h or "stock" in h),
            "carton": find(lambda h: "carton" in h),
            "piece": find(lambda h: h in ("quantity", "qty") or (h.startswith("quantity") and "free" not in h)),
        }

    def batch_rows(self, box, unit="piece"):
        """[{'batch', 'stock', 'qty', 'input'}] for each real batch line (the 'Total :' line is skipped).
        The qty box is the 'Quantity' column for unit piece, 'Carton Qty' for unit carton."""
        cols = self._columns(box)
        qty_col = cols["piece"] if unit == "piece" else cols["carton"]
        rows = []
        for tr in box.find_elements(By.CSS_SELECTOR, "tbody tr"):
            try:
                if not tr.is_displayed():
                    continue
                tds = tr.find_elements(By.TAG_NAME, "td")
                texts = [td.text.strip() for td in tds]
                if any(t.lower().startswith("total") for t in texts) or len(tds) < 3:
                    continue
                batch = texts[cols["batch"]] if cols["batch"] is not None and cols["batch"] < len(texts) else None
                if not batch:
                    continue
                inp = None
                if qty_col is not None and qty_col < len(tds):
                    found = tds[qty_col].find_elements(By.TAG_NAME, "input")
                    inp = found[0] if found else None
                if inp is None:
                    continue
                stock = None
                if cols["stock"] is not None and cols["stock"] < len(texts):
                    m = re.search(r"-?\d+(?:\.\d+)?", texts[cols["stock"]].replace(",", ""))
                    stock = float(m.group()) if m else None
                rows.append({"batch": batch, "stock": stock,
                             "qty": (inp.get_attribute("value") or "").strip(), "input": inp})
            except StaleElementReferenceException:
                continue
        return rows

    def read_allocation(self, row_index, unit="piece"):
        """{batch: qty} for batches with a non-zero qty, read from the row's hamburger popup
        (the popup is closed without applying)."""
        box = self.open_hamburger(row_index)
        time.sleep(1)
        alloc = {}
        text = box.text
        for r in self.batch_rows(box, unit):
            q = _num(r["qty"])
            if q:
                alloc[r["batch"]] = q
        self.close_popup_without_applying(box)
        return alloc, text

    def find_row_with_two_batches(self, min_stock=1, max_rows=40, product_search=None):
        """First in-stock row (with a Carton/Piece dropdown) whose batch popup lists at least two
        batches with stock >= min_stock. Returns (row_index, product_info, [batch labels]).
        If product_search is given, the grid is filtered to that product first (much faster)."""
        if product_search:
            self.search_product(product_search)

        def _scan(limit):
            for i in range(min(len(self.find_all(self.PRODUCT_ROWS)), limit)):
                try:
                    info = self.product_row(i)
                except Exception:
                    continue
                if info["available_stock"] < min_stock or self._unit_select(i) is None:
                    continue
                try:
                    box = self.open_hamburger(i, timeout=20)
                    time.sleep(1)
                    batches = [r for r in self.batch_rows(box, "carton") + self.batch_rows(box, "piece")
                               if r["batch"] and (r["stock"] is None or r["stock"] >= min_stock)]
                    labels = []
                    for r in batches:
                        if r["batch"] not in labels:
                            labels.append(r["batch"])
                    self.close_popup_without_applying(box)
                except Exception:
                    self.dismiss_any_alert(timeout=1)
                    continue
                if len(labels) >= 2:
                    return i, info, labels[:2]
            return None

        found = _scan(max_rows)
        if found is None and not product_search:
            self.show_all_products()
            found = _scan(max_rows * 3)
        if found is None:
            raise AssertionError(
                "No in-stock product with at least two batches found"
                + (f" for search {product_search!r}" if product_search else " in the rows checked")
                + " -- set BATCH_PRODUCT_SEARCH in the test to a product that has 2+ batches"
            )
        return found

    def split_across_batches(self, row_index, allocation, unit="piece"):
        """Open the row's hamburger, put allocation[batch] in each listed batch's qty box for the
        unit (Quantity for piece, Carton Qty for carton; others cleared), and click Apply.
        Returns (popup unit shown in the title, any alert text shown after Apply)."""
        box = self.open_hamburger(row_index)
        time.sleep(1)
        shown_unit = self.popup_unit(box)
        for r in self.batch_rows(box, unit):
            inp = r["input"]
            self.js_click(inp)
            inp.clear()
            if r["batch"] in allocation:
                inp.send_keys(str(allocation[r["batch"]]))
            inp.send_keys(Keys.TAB)
            time.sleep(0.3)
        apply_btn = box.find_element(By.XPATH, ".//button[normalize-space(.)='Apply'] | .//*[@value='Apply']")
        self.js_click(apply_btn)
        time.sleep(1.5)
        return shown_unit, self.dismiss_any_alert(timeout=2)

    # ------------------------------------------------------------------ batch presence / totals

    def row_pcs_inventory(self, row_index):
        """The product grid's 'Pcs. Inv.' value for a row (pieces in stock), or None."""
        headers = [self._norm(th.text) for th in self.driver.find_elements(By.CSS_SELECTOR, "#productlist thead th")]
        col = next((i for i, h in enumerate(headers) if "pcs" in h and "inv" in h), None)
        if col is None:
            return None
        tds = self.find_all(self.PRODUCT_ROWS)[row_index].find_elements(By.TAG_NAME, "td")
        return _num(tds[col].text) if col < len(tds) else None

    def batch_summary(self, row_index):
        """Open the row's batch popup and return {'batches': [(batch, inventory)], 'total': popup Total
        inventory or None, 'no_data': bool, 'text': popup text}; the popup is closed without applying."""
        box = self.open_hamburger(row_index, timeout=30)
        time.sleep(1)
        text = box.text
        rows = self.batch_rows(box, "carton") or self.batch_rows(box, "piece")
        batches = [(r["batch"], r["stock"]) for r in rows]
        total = None
        cols = self._columns(box)
        for tr in box.find_elements(By.CSS_SELECTOR, "tbody tr, tfoot tr"):
            try:
                tds = tr.find_elements(By.TAG_NAME, "td")
                texts = [td.text.strip() for td in tds]
                if any(t.lower().startswith("total") for t in texts):
                    if cols["stock"] is not None and cols["stock"] < len(texts):
                        total = _num(texts[cols["stock"]])
                    if total is None:
                        nums = [_num(t) for t in texts if _num(t) is not None]
                        total = nums[0] if nums else None
                    break
            except StaleElementReferenceException:
                continue
        self.close_popup_without_applying(box)
        return {"batches": batches, "total": total,
                "no_data": "no data available" in text.lower() or not batches, "text": text}
