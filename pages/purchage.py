from selenium.webdriver.common import alert
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config.config import EXPLICIT_WAIT
import time

class purchaseOrder:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, EXPLICIT_WAIT)

    def navigate_to_purchase(self):
        menu = self.wait.until(EC.element_to_be_clickable((
            By.XPATH, "//span[contains(text(),'Purchase Order')]"
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

    def enter_sale_qty(self, qty="10"):
        sale_qty = self.wait.until(EC.presence_of_element_located((
            By.XPATH, "(//input[contains(@class,'SaleQty')])[1]"
        )))
        sale_qty.clear()
        sale_qty.send_keys("1")

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

    def place_order(self):
        place_order = self.wait.until(EC.element_to_be_clickable((
            By.ID, "btnPlaceOrder"
        )))
        self.driver.execute_script("arguments[0].click();", place_order)

    def confirm_order(self):
        confirm_btn = self.wait.until(EC.element_to_be_clickable((
            By.XPATH, "//button[contains(text(),'Yes! Proceed.')]"
        )))
        confirm_btn.click()

    def click_ok_print_message(self):
        alert =self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='OK']")))
        alert.click()
        time.sleep(5)

    def verify_my_order_page(self):
        # Wait until My Order grid is loaded
        WebDriverWait(self.driver, 20).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//table")
            )
        )

        WebDriverWait(self.driver, 20).until(
        EC.visibility_of_element_located(
        (By.XPATH, "//button[contains(text(),'Load Slip Bill Wise')]")
    )
)

    print("My Order page loaded successfully")


    def click_first_row_print(self):
        rows = WebDriverWait(self.driver, 20).until(
        EC.presence_of_all_elements_located((By.XPATH, "//table//tbody//tr")))


        first_row = rows[0]

        # './/' keeps the search inside the first row ('//' searched the whole page), and the
        # Action control may be an input, button or link depending on the screen version.
        action_btn = first_row.find_element(
        By.XPATH,
        ".//*[self::input[@value='Action'] or self::button[normalize-space()='Action']"
        " or self::a[normalize-space()='Action']]"
         )

        self.wait.until(EC.element_to_be_clickable(action_btn))
        action_btn.click()

    # Step 3: wait for dropdown/menu to appear
        print_btn = self.wait.until(
          EC.visibility_of_element_located(
            (By.XPATH,
             "(//span[@title='Print Preview'])[1]")
          )
        )
        self.driver.execute_script("arguments[0].click();", print_btn)
        time.sleep(5)

    def click_print(self):
        print_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH,"//button[normalize-space()='Print']")))
        print_btn.click()

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





