from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from pages.base_page import BasePage
from utilities.performance import attach_page_performance


class DraftPage(BasePage):
    URL = "https://admin.massistcrm.com/DMSPages/NewDmsdrafts.html"

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

    @staticmethod
    def _row_to_dict(row):
        return {
            "draft_transfer_id": row.find_element(By.CSS_SELECTOR, "td.OrderId").text.split("\n")[0].strip(),
            "client": row.find_element(By.CSS_SELECTOR, "td.GetClientDetails").text.strip(),
            "no_of_items": row.find_element(By.CSS_SELECTOR, "td:nth-child(7)").text.strip(),
            "draft_amount": row.find_element(By.CSS_SELECTOR, "td.OrderAmt").text.strip(),
            "draft_qty": row.find_element(By.CSS_SELECTOR, "td.OrderQty").text.strip(),
        }

    def get_latest_draft_for_client(self, client_name):
        self.search(client_name)
        rows = self.find_all(self.ROWS)
        if not rows:
            return None
        return self._row_to_dict(rows[0])

    def order_again_for_client(self, client_name):
        self.search(client_name)
        rows = self.find_all(self.ROWS)
        if not rows:
            return None
        row = rows[0]
        draft_info = self._row_to_dict(row)
        order_btn = row.find_element(By.XPATH, ".//span[normalize-space(text())='Order']")
        self.js_click(order_btn)
        self.wait_until(
            lambda d: "SaleProduct.html" in d.current_url and "order_id" in d.current_url,
            timeout=20,
            message=f"Did not navigate back to SaleProduct.html with order_id after clicking Order for '{client_name}'",
        )
        return draft_info
