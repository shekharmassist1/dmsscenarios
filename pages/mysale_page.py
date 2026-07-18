from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from config.config import BASE_URL

class MySalePage:

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)
        self.TABLE_ROWS = (By.CSS_SELECTOR, "table.table tbody tr")  # ← yeh
        self.TABLE_COLS = (By.TAG_NAME, "td")  # ← yeh
        self.LOADING_VEIL = (By.ID, "veil")

    def navigate_to_mysale(self):
        menu = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//span[contains(text(),'Bill/New Invoice')]")
            )
        )
        menu.click()

        mysale = self.wait.until(
            EC.element_to_be_clickable((By.ID, "mySale"))
        )
        mysale.click()

        # better than sleep, but keeping safe wait
        self.wait.until(
            EC.presence_of_element_located((By.XPATH, "//table//tbody//tr"))
        )

    def get_orders_from_ui(self) -> list[dict]:
        self.wait.until(EC.presence_of_element_located(self.TABLE_ROWS))
        time.sleep(1)

        rows = self.driver.find_elements(*self.TABLE_ROWS)
        print(f"📋 Total rows: {len(rows)}")

        # ── Debug: pehli row ke saare columns print karo ──
        if rows:
            all_cols = rows[0].find_elements(By.TAG_NAME, "td")
            for idx, col in enumerate(all_cols):
                print(f"  col[{idx}] = '{col.text.strip()}'")

        orders = []
        for i, row in enumerate(rows):
            try:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) < 8:
                    continue

                invoice_full = cols[3].text.strip()
                order_id = invoice_full.split("/")[0].strip()

                # ── Sahi index — debug output dekh ke confirm karo ──
                order_data = {
                    "order_id": order_id,
                    "invoice_id": invoice_full,
                    "party_name": cols[4].text.strip(),  # Demo Dealer 4
                    "order_by": cols[6].text.strip(),  # Dummy_Distributor ← 6
                    "no_of_items": cols[7].text.strip(),  # 2                 ← 7
                    "amount": cols[8].text.strip(),  # 18263             ← 8
                    "order_qty": cols[11].text.strip(),  # 0
                    "sale_qty": cols[12].text.strip(),  # 360
                    "status": cols[13].text.strip(),  # Waiting for receive
                }

                if order_id:
                    orders.append(order_data)
                    print(f"  Row {i + 1}: {order_data}")

            except Exception as e:
                print(f"  Row {i + 1} skip: {e}")

        return orders

    def get_order_from_db(self, db, order_id: str) -> dict:
        query = f"""
            SELECT TOP 10
            Order_Id,
            Order_Amt       AS total_amount,
            NoOfProducts    AS no_of_items
        FROM order_dtls WITH(NOLOCK)
            WHERE Order_Id = '{order_id}'
            GROUP BY order_id,Order_Amt,
    NoOfProducts
        """
        columns, rows = db.fetch_all(query)

        if not rows:
            print(f"  Order {order_id} DB order not Found!")
            return {}

        db_data = dict(zip(columns, rows[0]))
        print(f"  🗄️  DB → {db_data}")
        return db_data

    def click_first_row_edit(self):
        rows = WebDriverWait(self.driver, 20).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//table//tbody//tr")
            )
        )

        first_row = rows[0]

        action_btn = first_row.find_element(
            By.XPATH,
            "//input[@value='Action']"
        )

        self.wait.until(EC.element_to_be_clickable(action_btn))
        action_btn.click()

        # Step 3: wait for dropdown/menu to appear
        edit_btn = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH,
                 "//table//tbody//tr[1]//td[contains(@class,'Action')]//span[contains(@class,'editOrder')]")
            )
        )
        self.driver.execute_script("arguments[0].click();", edit_btn)
        time.sleep(5)

    def click_calculate(self):
        calculate=self.wait.until(EC.element_to_be_clickable((By.XPATH,"//span[normalize-space()='calculate']")))
        calculate.click()

    def click_save(self):
        save=self.wait.until(EC.element_to_be_clickable((By.XPATH,"//button[@id='cartItemBtn']")))
        save.click()

    def click_update_sale(self):
        update=self.wait.until(EC.element_to_be_clickable((By.XPATH,"//button[@id='btnUpdateSale']")))
        update.click()
        time.sleep(5)
    def confirm_order(self):
        order=self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Yes! Proceed.']")))
        order.click()

    def click_print(self):
        print=self.wait.until(EC.element_to_be_clickable((By.XPATH,"//button[normalize-space()='Print']")))

        print.click()
        time.sleep(5)

    def verify_amount_and_screenshot(self):
        self.driver.switch_to.window(self.driver.window_handles[-1])
        time.sleep(3)

        # Print the URL for reference
        print(f"[INFO] Invoice URL: {self.driver.current_url}")

        # Take screenshot — payable amount visible in the PDF render
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"screenshots/invoice_{timestamp}.png"
        self.driver.save_screenshot(screenshot_path)
        print(f"[INFO] Screenshot saved: {screenshot_path}")

        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])









