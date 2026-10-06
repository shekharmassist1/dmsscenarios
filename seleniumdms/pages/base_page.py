from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class BasePage:
    ALERT_TITLE = (
        By.XPATH,
        "//span[contains(@class,'jconfirm-title')][starts-with(normalize-space(text()),'Alert')]",
    )

    def __init__(self, driver, timeout=20):
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)

    def get(self, url, retries=2):
        last_exc = None
        for attempt in range(retries + 1):
            try:
                self.driver.get(url)
                return
            except TimeoutException as exc:
                # This shared environment intermittently fails to load a page within the page-load
                # timeout (a raw "Timed out receiving message from renderer" from Chrome itself, not
                # one of our own waits) -- retrying the navigation resolves it almost every time.
                last_exc = exc
        raise last_exc

    def find(self, locator):
        return self.wait.until(
            EC.presence_of_element_located(locator), f"{locator} never became present"
        )

    def find_all(self, locator):
        return self.driver.find_elements(*locator)

    def dismiss_blocking_alert(self, timeout=1):
        try:
            title_el = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(self.ALERT_TITLE)
            )
        except TimeoutException:
            return None
        box = title_el.find_element(By.XPATH, "ancestor::div[contains(@class,'jconfirm-box')]")
        message = box.find_element(By.CSS_SELECTOR, ".jconfirm-content").text.strip()
        okay_btn = box.find_element(By.XPATH, ".//div[contains(@class,'jconfirm-buttons')]/button")
        self.js_click(okay_btn)
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(self.ALERT_TITLE))
        return message

    def click(self, locator, message="", max_alert_retries=5):
        for _ in range(max_alert_retries):
            try:
                el = self.wait.until(
                    EC.element_to_be_clickable(locator), message or f"{locator} never became clickable"
                )
                break
            except TimeoutException:
                if self.dismiss_blocking_alert() is None:
                    raise
        else:
            el = self.wait.until(
                EC.element_to_be_clickable(locator), message or f"{locator} never became clickable"
            )
        self.js_click(el)
        return el

    def js_click(self, element, retries=1):
        for attempt in range(retries + 1):
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
                self.driver.execute_script("arguments[0].click();", element)
                return
            except TimeoutException:
                # Same class of raw Chrome renderer-timeout flake as get()'s retry above (a genuine
                # "Timed out receiving message from renderer: 30.000" from Chrome itself, not one of
                # our own waits) -- confirmed live during a Print click, not just page navigation.
                # Retrying the same click resolves it almost every time.
                if attempt == retries:
                    raise

    def wait_until(self, condition, timeout=None, message=""):
        w = self.wait if timeout is None else WebDriverWait(self.driver, timeout)
        return w.until(condition, message)

    def text_of(self, locator):
        return self.find(locator).text.strip()
