"""Shared customer selection for Bill/New Invoice and Sale Return.

The customer search matches each word separately ('Demo Dealer 3' also returns Demo Dealer 13, 23, 30 ...),
so the wanted customer can be on page 2 or later. This searches (first with the name in quotes, which
DataTables treats as an exact phrase), then looks for the EXACT name on each page, clicking Next and
waiting for the page to really change before looking again."""
import time

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

NEXT_BUTTON = (By.CSS_SELECTOR, ".paginate_button.next")
INFO = (By.CSS_SELECTOR, ".dataTables_info")


def _info_text(wrapper):
    try:
        return wrapper.find_element(*INFO).text.strip()
    except Exception:
        return ""


def _wait_for_row(wrapper, row_xpath, timeout):
    end = time.time() + timeout
    while time.time() < end:
        try:
            rows = wrapper.find_elements(By.XPATH, row_xpath)
            if rows:
                return rows[0]
        except StaleElementReferenceException:
            pass
        time.sleep(0.4)
    return None


def _click_next_and_wait(page, wrapper):
    """Click Next; True once the 'Showing X to Y' text has changed, False if there is no next page."""
    buttons = wrapper.find_elements(*NEXT_BUTTON)
    if not buttons or "disabled" in (buttons[0].get_attribute("class") or ""):
        return False
    before = _info_text(wrapper)
    target = buttons[0].find_elements(By.TAG_NAME, "a") or [buttons[0]]
    page.js_click(target[0])
    end = time.time() + 15
    while time.time() < end:
        if _info_text(wrapper) != before:
            time.sleep(0.5)
            return True
        time.sleep(0.3)
    return False


def pick_customer(page, name, max_pages=20):
    row_xpath = f".//tbody/tr[td[normalize-space(.)='{name}']]"
    seen_pages = []
    for term in (f'"{name}"', name):
        search, wrapper = page._customer_table()
        try:
            lengths = wrapper.find_elements(By.CSS_SELECTOR, "select[name$='_length']") or \
                wrapper.find_elements(By.CSS_SELECTOR, ".dataTables_length select")
            if lengths:
                values = [o.get_attribute("value") for o in lengths[0].find_elements(By.TAG_NAME, "option")]
                if "-1" in values:
                    Select(lengths[0]).select_by_value("-1")
                    page._wait_table_settled(wrapper)
        except Exception:
            pass

        search.clear()
        search.send_keys(term)
        page._wait_table_settled(wrapper)

        for page_no in range(1, max_pages + 1):
            row = _wait_for_row(wrapper, row_xpath, timeout=15 if page_no == 1 else 8)
            if row is not None:
                btn = row.find_element(
                    By.XPATH, ".//a[contains(normalize-space(.),'Select')] | .//button[contains(normalize-space(.),'Select')]"
                )
                page.js_click(btn)
                return
            seen_pages.append(f"search {term!r} page {page_no}: {_info_text(wrapper)}")
            if not _click_next_and_wait(page, wrapper):
                break

    raise TimeoutException(f"Customer row for '{name}' not found on any results page ({'; '.join(seen_pages)})")
