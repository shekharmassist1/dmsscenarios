from selenium.webdriver.common.by import By
from pages.base_page import BasePage


class LoginPage(BasePage):
    URL = "https://admin.massistcrm.com/Login.aspx"

    USERNAME_INPUT = (By.ID, "txtuser")
    PASSWORD_INPUT = (By.ID, "txtpassword")
    SUBMIT_BUTTON = (By.ID, "btnSubmit")

    def open(self):
        self.get(self.URL)
        self.find(self.USERNAME_INPUT)
        return self

    def login(self, username, password):
        self.find(self.USERNAME_INPUT).send_keys(username)
        self.find(self.PASSWORD_INPUT).send_keys(password)
        self.click(self.SUBMIT_BUTTON)
        self.wait_until(
            lambda d: "Login.aspx" not in d.current_url,
            timeout=30,
            message="Still on Login.aspx after submitting credentials",
        )
        return self
