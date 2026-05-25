from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config.config import EXPLICIT_WAIT
import time

class HomePage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, EXPLICIT_WAIT)

    def get_menus(self):
        return self.driver.find_elements(By.XPATH, "//div[@class='nav']")

    def click_all_menus(self, screenshot_fn):
        menus = self.get_menus()
        total = len(menus)
        print(f"Total menus: {total}")

        for i in range(total):
            # Re-fetch to avoid stale element
            menus = self.get_menus()
            try:
                menu_name = menus[i].text.strip()
                print(f"Opening menu: {menu_name}")
                screenshot_fn(f"Before_Click_{menu_name}")
                menus[i].click()
                time.sleep(3)
                screenshot_fn(f"After_Click_{menu_name}")
                print(f"Current Page: {self.driver.title}")
            except Exception as e:
                print(f"Error on menu {i}: {e}")
                screenshot_fn(f"FAILED_menu_{i}")