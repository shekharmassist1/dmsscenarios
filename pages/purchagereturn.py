from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from config.config import EXPLICIT_WAIT
import time

class purchageReturnPage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, EXPLICIT_WAIT)

    def navigate_to_purchage_return(self):
        menu = self.wait.until(EC.element_to_be_clickable((
            By.XPATH, "//span[@class='hide_txt'][normalize-space()='Purchase Return']"
        )))
        menu.click()

    def search_customer(self):
        search_input = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='search']")))
        search_input.send_keys("vel")

    def select_customer(self, customer_name):
        select_btn = self.wait.until(EC.visibility_of_element_located((
            By.XPATH,
            "(//a[contains(@class,'btn-primary') and normalize-space()='Select'])[1]"
        )))
        select_btn.click()
        time.sleep(10)

    def hamburger(self):
        hamburger_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(@class,'ShowBatchWiseVariant')]")))
        hamburger_btn.click()

        inventory_value = WebDriverWait(self.driver, 25).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//table//td[contains(@class,'Inventory') or "
                "contains(@class,'inventory')]//span | "
                "//table//td[preceding-sibling::td[contains(text(),'Inventory')]]"
            ))
        )
        print(f"Inventory: {inventory_value.text}")
        close_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@class='jconfirm-closeIcon']")))
        close_btn.click()
        return inventory_value.text

    def select_first_product(self):
        # Wait for slow API to load table
        WebDriverWait(self.driver, 60).until(
            EC.presence_of_element_located((By.ID, "productlist"))
        )
        time.sleep(3)

        first_row = self.driver.find_element(
            By.CSS_SELECTOR, "#productlist tbody tr"
        )
        first_row.click()
        print("✅ First product row clicked")

    def enter_qty(self, qty="1"):
        qty_input = WebDriverWait(self.driver, 60).until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR, "input.clsNumberOnly.C2"
            ))
        )
        qty_input.clear()
        qty_input.send_keys(qty)
        print(f"✅ Qty entered: {qty}")
        time.sleep(3)

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

    def click_place_return(self):
        place_return = self.wait.until(EC.element_to_be_clickable((
            By.ID, "btnPlaceReturn"
        )))
        place_return.click()

    def confirm_return(self):
        confirm_btn = self.wait.until(EC.element_to_be_clickable((
            By.XPATH, "//button[contains(text(),'Yes! Proceed.')]"
        )))
        confirm_btn.click()

    def click_ok(self):
        alert = self.wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//div[contains(@class,'jconfirm-buttons')]//button"
            "[translate(normalize-space(),'ok','OK')='OK']"
            " | //button[translate(normalize-space(),'ok','OK')='OK']"
        )))
        alert.click()
        time.sleep(5)

