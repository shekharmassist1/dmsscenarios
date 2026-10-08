import re
import time

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


class ReturnDetailsPage:
    """Return Details page (opens after a Sale Return is saved; also in the top menu).

    Rows have an 'Action' dropdown in the Status column whose menu items are pill buttons labelled
    Action / Print / Create IRN / Remark. 'Print' opens the credit note in a new tab."""

    JCONFIRM_BOXES = (By.CSS_SELECTOR, ".jconfirm-box")
    NAV_LINK = (By.XPATH, "//a[normalize-space(.)='Return Details'] | //*[self::span or self::li][normalize-space(.)='Return Details']")
    _ACTION_TOGGLE_XPATH = (
        ".//*[contains(@class,'dmsActionMenu')]"
        " | .//*[self::button or self::a or self::span or self::div]"
        "[normalize-space(.)='Action' and not(ancestor::*[contains(@class,'actionButtonsWrapper')])]"
    )

    def __init__(self, driver):
        self.driver = driver

    def wait_until(self, condition, timeout=20, message=""):
        return WebDriverWait(self.driver, timeout).until(condition, message)

    def js_click(self, element):
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        self.driver.execute_script("arguments[0].click();", element)

    def _rows(self):
        rows = []
        for r in self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr"):
            try:
                if r.is_displayed() and r.find_elements(By.XPATH, self._ACTION_TOGGLE_XPATH):
                    rows.append(r)
            except StaleElementReferenceException:
                continue
        return rows

    def wait_for_page(self, timeout=60):
        """The app normally opens Return Details by itself after the return is saved. If it hasn't
        within `timeout`, open it from the top menu. Returns the page URL."""
        def _ready(d):
            return "ProductReceived" not in d.current_url and bool(self._rows())

        try:
            self.wait_until(_ready, timeout=timeout)
        except TimeoutException:
            links = [l for l in self.driver.find_elements(*self.NAV_LINK) if l.is_displayed()]
            if not links:
                raise AssertionError("Return Details page did not open and its menu link was not found")
            self.js_click(links[0])
            self.wait_until(_ready, timeout=60, message="Return Details page (rows with Action) never loaded")
        time.sleep(1)
        return self.driver.current_url

    def newest_row(self):
        """First (newest) row as {column header: cell text} plus '_text' (the whole row)."""
        rows = self._rows()
        if not rows:
            return {}
        row = rows[0]
        table = row.find_element(By.XPATH, "./ancestor::table[1]")
        headers = [th.text.strip() for th in table.find_elements(By.CSS_SELECTOR, "thead th")]
        cells = [td.text.strip() for td in row.find_elements(By.TAG_NAME, "td")]
        data = {"_text": row.text.strip()}
        for i, h in enumerate(headers):
            if h and i < len(cells):
                data[h] = cells[i]
        return data

    @staticmethod
    def column(data, *names):
        def norm(x):
            return re.sub(r"[^a-z0-9]", "", x.lower())
        wanted = [norm(n) for n in names]
        for key, value in data.items():
            if key != "_text" and norm(key) in wanted:
                return value
        return None

    def _visible_print_item(self, row):
        xpath = (
            ".//*[self::a or self::button or self::li or self::span or self::div]"
            "[normalize-space(.)='Print' or contains(@class,'GetInvoiceDetails')]"
        )
        for scope, xp in ((row, xpath), (self.driver, "/" + xpath)):
            for el in scope.find_elements(By.XPATH, xp):
                try:
                    if el.is_displayed():
                        return el
                except StaleElementReferenceException:
                    continue
        return None

    def open_newest_credit_note(self):
        """Hover (else click) Action on the newest row, click 'Print' (and Print in a print dialog if
        one appears), switch to the new tab and return {'url', 'title', 'screenshot', 'main_handle'}.
        The caller reads the note and then calls close_credit_note(info)."""
        rows = self._rows()
        if not rows:
            raise AssertionError("No rows with an Action button on the Return Details page")
        row = rows[0]
        toggle = row.find_elements(By.XPATH, self._ACTION_TOGGLE_XPATH)[0]
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", toggle)
        self.driver.execute_script(
            "arguments[0].dispatchEvent(new MouseEvent('mouseover', {bubbles: true, cancelable: true}));", toggle
        )
        time.sleep(1)
        item = self._visible_print_item(row)
        if item is None:
            self.js_click(toggle)
            try:
                item = self.wait_until(lambda d: self._visible_print_item(row), timeout=10)
            except TimeoutException:
                item = None
        if item is None:
            raise AssertionError("'Print' never appeared in the Action menu of the newest return row")

        handles_before = set(self.driver.window_handles)
        main_handle = self.driver.current_window_handle
        self.js_click(item)
        end = time.time() + 30
        while time.time() < end and len(self.driver.window_handles) <= len(handles_before):
            for box in self.driver.find_elements(*self.JCONFIRM_BOXES):
                try:
                    if box.is_displayed():
                        btns = box.find_elements(By.XPATH, ".//button[normalize-space(.)='Print']")
                        if btns:
                            self.js_click(btns[0])
                            time.sleep(1)
                except StaleElementReferenceException:
                    continue
            time.sleep(0.5)
        new_handles = set(self.driver.window_handles) - handles_before
        if not new_handles:
            raise AssertionError("The credit note did not open in a new tab after clicking Print")
        self.driver.switch_to.window(new_handles.pop())
        try:
            self.wait_until(lambda d: d.current_url not in ("", "about:blank"), timeout=30)
        except TimeoutException:
            pass
        time.sleep(2)
        return {
            "url": self.driver.current_url,
            "title": self.driver.title,
            "screenshot": self.driver.get_screenshot_as_png(),
            "main_handle": main_handle,
        }

    def close_credit_note(self, info):
        try:
            self.driver.close()
        finally:
            self.driver.switch_to.window(info["main_handle"])
