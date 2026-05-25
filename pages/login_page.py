from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config.config import EXPLICIT_WAIT

class LoginPage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, EXPLICIT_WAIT)

    def login(self, username, password):
        self.driver.find_element(By.ID, "txtuser").send_keys(username)
        self.driver.find_element(By.ID, "txtpassword").send_keys(password)
        self.driver.find_element(By.ID, "btnSubmit").click()

    def verify_user(self):
        user_txt = self.wait.until(
            EC.presence_of_element_located((By.ID, "clientid"))
        ).text
        assert "Demo" in user_txt, f"User verification failed: {user_txt}"
        return user_txt

    def verify_logo(self):
        logo = self.driver.find_element(
            By.XPATH, "//img[@class='company_logo_img']"
        )
        assert logo.is_displayed(), "Logo not visible"
        return logo