from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from config.config import EXPLICIT_WAIT
import time

class MySalePage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, EXPLICIT_WAIT)

    def navigate_to_mysale(self):
        menu = self.wait.until(EC.element_to_be_clickable((
            By.XPATH, "//span[contains(text(),'Bill/New Invoice')]"
        )))
        menu.click()
        time.sleep(3)
        mysale = self.wait.until(EC.element_to_be_clickable((By.ID, "mySale")))
        mysale.click()

    def click_edit(self, invoice_id):
        # Wait for any Action button
        action_btn = self.wait.until(EC.presence_of_element_located((
            By.XPATH,
            "//input[@type='button' and @value='Action' "
            "and contains(@class,'btn-primary')]"
        )))

        # Hover to reveal dropdown
        ActionChains(self.driver).move_to_element(action_btn).perform()

        # Click Edit for specific invoice
        edit_btn = self.wait.until(EC.presence_of_element_located((
            By.XPATH,
            f"//span[@id='{invoice_id}' and contains(@class,'editOrder')]"
        )))
        self.driver.execute_script("arguments[0].click();", edit_btn)
        print(f"✅ Edit clicked for invoice: {invoice_id}")

    def click_save(self):
        save = self.wait.until(EC.element_to_be_clickable((By.ID, "cartItemBtn")))
        save.click()

    def click_update_sale(self):
        update_sale = self.wait.until(EC.element_to_be_clickable((
            By.ID, "btnUpdateSale"
        )))
        update_sale.click()

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
            "//div[contains(@class,'printPreviewDialog')]"
            "//button[normalize-space()='Print']"
        )))

        original_window = self.driver.current_window_handle
        all_windows_before = set(self.driver.window_handles)

        self.driver.execute_script("arguments[0].click();", print_btn)

        # Wait for new tab
        WebDriverWait(self.driver, 20).until(
            lambda d: len(d.window_handles) > len(all_windows_before)
        )

        # Switch to new tab
        new_window = (set(self.driver.window_handles) - all_windows_before).pop()
        self.driver.switch_to.window(new_window)

        # Wait for invoice
        self.wait.until(EC.presence_of_element_located((
            By.XPATH, "//td[contains(text(),'Tax Invoice')]"
        )))

        print(f"✅ Invoice loaded: {self.driver.title}")
        print(f"✅ URL: {self.driver.current_url}")