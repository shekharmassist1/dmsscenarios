import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from pages.base_page import BasePage
from utilities.performance import attach_page_performance
from config import BASE_URL


class DraftPage(BasePage):
    URL = BASE_URL + "/DMSPages/NewDmsdrafts.html"

    SEARCH_INPUT = (By.ID, "productSearch")
    ROWS = (By.CSS_SELECTOR, "#tbl_order_grid tbody tr")

    def open(self):
        self.get(self.URL)
        self.find(self.SEARCH_INPUT)
        attach_page_performance(self.driver, "Drafts page")
        return self

    def search(self, text):
        box = self.find(self.SEARCH_INPUT)
        box.clear()
        box.send_keys(text)
        self.wait_until(
            lambda d: len(d.find_elements(*self.ROWS)) > 0,
            timeout=15,
            message=f"No draft rows appeared after searching for '{text}'",
        )
        return self

    def _items_col(self):
        """1-based index of the 'No. Of Items' column, found by its heading (falls back to 7)."""
        try:
            heads = self.driver.find_elements(By.CSS_SELECTOR, "#tbl_order_grid thead th")
            for i, th in enumerate(heads, start=1):
                t = re.sub(r"[^a-z]", "", (th.get_attribute("textContent") or "").lower())
                if t in ("noofitems", "noofitem", "items"):
                    return i
        except Exception:
            pass
        return 7

    def _row_to_dict(self, row):
        return {
            "draft_transfer_id": row.find_element(By.CSS_SELECTOR, "td.OrderId").text.split("\n")[0].strip(),
            "client": row.find_element(By.CSS_SELECTOR, "td.GetClientDetails").text.strip(),
            "no_of_items": row.find_element(By.CSS_SELECTOR, f"td:nth-child({self._items_col()})").text.strip(),
            "draft_amount": row.find_element(By.CSS_SELECTOR, "td.OrderAmt").text.strip(),
            "draft_qty": row.find_element(By.CSS_SELECTOR, "td.OrderQty").text.strip(),
        }

    def _newest_row_for_client(self, client_name):
        """The customer's NEWEST draft. The search matches words anywhere (so 'Demo Dealer 4' also
        returns Demo Dealer 14 ...) and the list is not guaranteed to be newest-first, so: keep only
        rows whose client name matches exactly, then take the highest Draft ID."""
        self.search(client_name)
        target = re.sub(r"\s+", " ", client_name).strip().lower()
        best, best_id = None, None
        for row in self.find_all(self.ROWS):
            try:
                client = re.sub(r"\s+", " ", row.find_element(By.CSS_SELECTOR, "td.GetClientDetails").text).strip().lower()
                if not (client == target or client.startswith(target + " ") or client.startswith(target + "\n")
                        or client.split("\n")[0].strip() == target):
                    continue
                raw = row.find_element(By.CSS_SELECTOR, "td.OrderId").text.split("\n")[0].strip()
                num = int(re.sub(r"\D", "", raw) or -1)
            except Exception:
                continue
            if best_id is None or num > best_id:
                best, best_id = row, num
        return best

    def get_latest_draft_for_client(self, client_name):
        row = self._newest_row_for_client(client_name)
        return self._row_to_dict(row) if row is not None else None

    def order_again_for_client(self, client_name):
        row = self._newest_row_for_client(client_name)
        if row is None:
            return None
        draft_info = self._row_to_dict(row)
        order_btn = row.find_element(By.XPATH, ".//span[normalize-space(text())='Order']")
        self.js_click(order_btn)
        self.wait_until(
            lambda d: "SaleProduct.html" in d.current_url and "order_id" in d.current_url,
            timeout=20,
            message=f"Did not navigate back to SaleProduct.html with order_id after clicking Order for '{client_name}'",
        )
        return draft_info
