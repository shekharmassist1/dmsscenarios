from urllib.parse import urlparse

from selenium.webdriver.common.by import By
from pages.base_page import BasePage
from config import BASE_URL


def _on_login_page(url):
    """admin's login page is /Login.aspx, stage's is /login -- treat any path ending in 'login'
    (any case, with or without .aspx) as the login page."""
    path = urlparse(url).path.lower().rstrip("/")
    return path.endswith("/login") or path.endswith("/login.aspx")


class LoginPage(BasePage):
    # Open the site root: each site redirects it to its own login page (admin /Login.aspx, stage /login).
    URL = BASE_URL + "/"

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
        try:
            self.wait_until(lambda d: not _on_login_page(d.current_url), timeout=30, message="")
        except Exception:
            # Say what the login page is showing (wrong password, OTP prompt, ...) instead of a bare timeout.
            try:
                shown = self.driver.execute_script(
                    "return Array.from(document.querySelectorAll('.jconfirm-box, .alert, .error, .text-danger, span[style*=red]'))"
                    ".map(e => e.innerText.trim()).filter(t => t).join(' | ')") or ""
            except Exception:
                shown = ""
            raise AssertionError(
                f"Still on the login page after submitting credentials ({self.driver.current_url}); "
                f"page message: {shown[:300] or 'none'}")
        return self
