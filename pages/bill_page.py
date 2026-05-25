from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config.config import EXPLICIT_WAIT
import time

class BillPage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, EXPLICIT_WAIT)

    def navigate_to_bill(self):
        menu = self.wait.until(EC.element_to_be_clickable((
            By.XPATH, "//span[contains(text(),'Bill/New Invoice')]"
        )))
        menu.click()

    def select_customer(self, customer_name):
        select_btn = self.wait.until(EC.element_to_be_clickable((
            By.XPATH,
            f"//td[text()='{customer_name}']/following-sibling::td/a[contains(text(),'Select')]"
        )))
        select_btn.click()

    def enter_sale_qty(self, qty="10"):
        sale_qty = self.wait.until(EC.presence_of_element_located((
            By.XPATH, "(//input[contains(@class,'SaleQty')])[1]"
        )))
        sale_qty.clear()
        sale_qty.send_keys(qty)

    def click_calculate(self):
        calculate_btn = self.wait.until(EC.element_to_be_clickable((
            By.ID, "lblCalculate"
        )))
        print(f"Calculate button text: {calculate_btn.text}")
        calculate_btn.click()

    def click_save(self):
        save_btn = self.wait.until(EC.element_to_be_clickable((
            By.ID, "cartItemBtn"
        )))
        save_btn.click()

    def click_add_to_cart(self):
        add_sale_btn = self.wait.until(EC.element_to_be_clickable((
            By.ID, "btnCart"
        )))
        add_sale_btn.click()

    def confirm_order(self):
        confirm_btn = self.wait.until(EC.element_to_be_clickable((
            By.XPATH, "//button[contains(text(),'Yes! Proceed.')]"
        )))
        confirm_btn.click()

    def click_print_and_switch(self):
        # Wait for print dialog
        self.wait.until(EC.visibility_of_element_located((
            By.CLASS_NAME, "printPreviewDialog"
        )))

        print_btn = self.wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//div[contains(@class,'printPreviewDialog')]//button[normalize-space()='Print']"
        )))

        original_window = self.driver.current_window_handle
        all_windows_before = set(self.driver.window_handles)

        print_btn.click()

        # Wait for new tab
        WebDriverWait(self.driver, 20).until(
            lambda d: len(d.window_handles) > len(all_windows_before)
        )

        # Switch to new tab
        new_window = (set(self.driver.window_handles) - all_windows_before).pop()
        self.driver.switch_to.window(new_window)

        # Wait for invoice to load
        self.wait.until(EC.presence_of_element_located((
            By.XPATH, "//td[contains(text(),'Tax Invoice')]"
        )))

        print("Invoice page loaded successfully!")
        print(f"Title: {self.driver.title}")
        print(f"URL: {self.driver.current_url}")