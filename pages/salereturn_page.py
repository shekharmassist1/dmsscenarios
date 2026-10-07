from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from config.config import EXPLICIT_WAIT
import time

class SaleReturnPage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, EXPLICIT_WAIT)

    def navigate_to_sale_return(self):
        menu = self.wait.until(EC.element_to_be_clickable((
            By.XPATH, "//span[contains(text(),'Sale Return')]"
        )))
        menu.click()

    def search_customer(self, customer_name):
        search_input = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='search']")))
        search_input.send_keys("Demo 4")

    def select_customer(self, customer_name):
        select_btn = self.wait.until(EC.visibility_of_element_located((
            By.XPATH,
            "(//a[contains(@class,'btn-primary') and normalize-space()='Select'])[1]"
        )))
        select_btn.click()
        time.sleep(10)

    def select_return_type(self, return_type="Without Reference"):
        dropdown = self.wait.until(EC.presence_of_element_located((
            By.ID, "ddlBillFor"
        )))
        Select(dropdown).select_by_visible_text(return_type)



        go_btn = self.wait.until(EC.element_to_be_clickable((
            By.XPATH, "//button[normalize-space()='Go!']"
        )))
        go_btn.click()
        print(f"✅ Return type '{return_type}' selected and Go! clicked")

    def select_first_product(self):
        # Wait for slow API to load table
        # The table shell (#productlist) appears before its rows are filled by a slow API call,
        # so wait for an actual row rather than just the table.
        rows = WebDriverWait(self.driver, 90).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, "#productlist tbody tr"),
            message="Sale Return product grid loaded no rows within 90s after Go!",
        )
        first_row = rows[0]
        first_row.click()
        print("✅ First product row clicked")

    def enter_qty(self, qty="1"):
        qty_input = WebDriverWait(self.driver, 60).until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR, "input.clsNumberOnly.C1"
            ))
        )
        qty_input.clear()
        qty_input.send_keys(qty)
        print(f"✅ Qty entered: {qty}")

    def click_calculate(self):
        calculate = self.wait.until(EC.element_to_be_clickable((
            By.ID, "lblCalculate"
        )))
        calculate.click()

    def click_save(self):
        save_btn = self.wait.until(EC.element_to_be_clickable((
            By.ID, "cartItemBtn"
        )))
        save_btn.click()

    def click_product_receive(self):
        product_rcv = self.wait.until(EC.element_to_be_clickable((
            By.ID, "btnProductsRecieve"
        )))
        product_rcv.click()

    def confirm_order(self):
        confirm_btn = self.wait.until(EC.element_to_be_clickable((
            By.XPATH, "//button[contains(text(),'Yes! Proceed.')]"
        )))
        confirm_btn.click()

    def click_ok(self):
        ok_btn = self.wait.until(EC.element_to_be_clickable((
            By.XPATH, "//button[translate(normalize-space(),'ok','OK')='OK']"
        )))
        ok_btn.click()
        print("✅ Received successfully!")