import re
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

    _ROW_KEYS_JS = """
        return arguments[0].map(function (tr) {
            var b = tr.querySelector('label.barcode');
            if (b && b.getAttribute('barcode')) return 'code:' + b.getAttribute('barcode').trim();
            var p = tr.querySelector('[data-productid]');
            if (p && p.getAttribute('data-productid')) return 'pid:' + p.getAttribute('data-productid');
            var t = tr.querySelector('td');
            return 'text:' + (t ? t.innerText.trim().slice(0, 80) : '');
        });
    """

    def product_row_el(self, index):
        """The product-grid row the test means by `index`. Since the DMS UI update the grid moves a
        row (e.g. to the top) as soon as it is changed, so plain rows[index] can point at a different
        product. Positions are therefore pinned to a snapshot of which product sat where when the
        grid was loaded: if the grid only reorders (same products), `index` still means that product;
        if the set of products changes (search, filter, paging, reload), the snapshot is refreshed."""
        rows = self.find_all(self.PRODUCT_ROWS)
        try:
            keys = self.driver.execute_script(self._ROW_KEYS_JS, rows) or []
        except Exception:
            return rows[index]
        snap = getattr(self, "_row_snapshot", None)
        if snap is None or sorted(snap) != sorted(keys):
            self._row_snapshot = list(keys)
            return rows[index]
        if index >= len(snap):
            return rows[index]
        key = snap[index]
        occurrence = snap[:index].count(key)
        seen = -1
        for j, k in enumerate(keys):
            if k == key:
                seen += 1
                if seen == occurrence:
                    return rows[j]
        return rows[index]

    _NUMBER_RE = re.compile(r"-?[\d,]*\.?\d+")

    def summary_value(self, locator, label):
        """Text of a header summary box (Total Item, Final Amount, ...). Tries the old locator first;
        if it is missing or empty (the DMS UI update changed the header), finds the box by its
        on-screen label (exact, case-insensitive) and returns the number shown in that box."""
        # The locator can match both the number and its label span, and since the UI update the
        # number span may not count as 'displayed' (sticky header), so read textContent of every
        # match and take the first one that contains a number.
        try:
            for el in self.driver.find_elements(*locator):
                text = (el.get_attribute("textContent") or el.text or "").strip()
                m = self._NUMBER_RE.search(text.replace(",", ""))
                if m:
                    return m.group(0)
        except Exception:
            pass
        lower = "translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')"
        xpath = f"//*[not(*) and {lower}='{label.lower()}']"
        for lab in self.driver.find_elements("xpath", xpath):
            try:
                if not lab.is_displayed():
                    continue
                box_text = lab.find_element("xpath", "./..").text
                rest = box_text.replace(lab.text, " ")
                m = self._NUMBER_RE.search(rest)
                if m:
                    return m.group(0)
            except Exception:
                continue
        return ""

    def text_of(self, locator):
        return self.find(locator).text.strip()
