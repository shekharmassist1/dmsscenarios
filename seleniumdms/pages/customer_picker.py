"""Shared customer selection for Bill/New Invoice and Sale Return.

The customer search matches each word separately ('Demo Dealer 3' also returns Demo Dealer 13, 23, 30 ...),
so the wanted customer can be on page 2 or later. This searches (first with the name in quotes, which
DataTables treats as an exact phrase), then looks for the EXACT name on each page, clicking Next and
waiting for the page to really change before looking again."""
import re
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


def _wait_for_match(wrapper, name, timeout):
    end = time.time() + timeout
    while time.time() < end:
        row = _matching_row(wrapper, name)
        if row is not None:
            return row
        if " 0 to 0 " in f" {_info_text(wrapper).lower()} ":
            time.sleep(1)  # empty result: give it one more second, then stop waiting
            return _matching_row(wrapper, name)
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


SEARCH_INPUTS = (By.XPATH, "//input[@type='search']")
SELECT_IN_ROW = ".//tbody/tr//*[self::a or self::button][contains(normalize-space(.),'Select')]"


def _customer_table(page, timeout=60):
    """(search box, table wrapper) of the CUSTOMER list -- the DataTable whose rows have 'Select'
    buttons. The page can show other small tables with their own search box (seen: a 1-row table),
    and typing into that one is why customer selection used to fail at random."""
    end = time.time() + timeout
    last = []
    while time.time() < end:
        last = []
        for box in page.driver.find_elements(*SEARCH_INPUTS):
            try:
                if not box.is_displayed():
                    continue
                wrapper = box.find_element(By.XPATH, "./ancestor::div[contains(@class,'dataTables_wrapper')]")
                if wrapper.find_elements(By.XPATH, SELECT_IN_ROW):
                    return box, wrapper
                last.append(_info_text(wrapper) or wrapper.get_attribute("id") or "?")
            except Exception:
                continue
        time.sleep(0.5)
    raise TimeoutException(f"No customer table (rows with a 'Select' button) found; visible tables: {last}")


def _matching_row(wrapper, name):
    """Row with a cell equal to name (case/space-insensitive), or starting with name followed by a
    non-digit (so 'Demo Dealer 3' never matches 'Demo Dealer 30')."""
    target = re.sub(r"\s+", " ", name).strip().lower()
    pattern = re.compile(re.escape(target) + r"(?!\d)")
    for tr in wrapper.find_elements(By.CSS_SELECTOR, "tbody tr"):
        try:
            for td in tr.find_elements(By.TAG_NAME, "td"):
                text = re.sub(r"\s+", " ", td.text).strip().lower()
                if text == target or pattern.match(text):
                    return tr
        except StaleElementReferenceException:
            continue
    return None


def _row_texts(wrapper, limit=3):
    out = []
    for tr in wrapper.find_elements(By.CSS_SELECTOR, "tbody tr")[:limit]:
        try:
            out.append(re.sub(r"\s+", " ", tr.text).strip()[:80])
        except StaleElementReferenceException:
            continue
    return out


BEAT_CONTAINERS = (By.CSS_SELECTOR, "span.select2-selection--single")


def _beat_select(page):
    """The <select> behind the first visible select2 dropdown on the customer screen (the Beat filter),
    or None. The customer list only shows the selected beat's customers."""
    for span in page.driver.find_elements(*BEAT_CONTAINERS):
        try:
            if not span.is_displayed():
                continue
            sel = span.find_element(By.XPATH, "./ancestor::span[contains(@class,'select2-container')]/preceding-sibling::select[1]")
            return sel
        except Exception:
            continue
    return None


def _beat_options(sel):
    return [((o.get_attribute("value") or ""), o.text.strip()) for o in sel.find_elements(By.TAG_NAME, "option")]


def _set_beat(page, sel, value):
    """Choose a beat (select2) and wait for the customer table to reload."""
    try:
        _, wrapper = _customer_table(page, timeout=20)
        before = _info_text(wrapper)
    except Exception:
        wrapper, before = None, None
    page.driver.execute_script(
        "var s = arguments[0];"
        "if (window.jQuery) { jQuery(s).val(arguments[1]).trigger('change'); }"
        "else { s.value = arguments[1]; s.dispatchEvent(new Event('change', {bubbles: true})); }",
        sel, value,
    )
    end = time.time() + 10
    while wrapper is not None and time.time() < end and _info_text(wrapper) == before:
        time.sleep(0.3)
    time.sleep(1.5)


def _total_entries(wrapper):
    """Total customers loaded in the table ('Filtered From N Total Entries' or 'Of N Entries')."""
    text = _info_text(wrapper)
    m = re.search(r"from\s+([\d,]+)\s+total", text, flags=re.I) or re.search(r"of\s+([\d,]+)\s+entries", text, flags=re.I)
    return int(m.group(1).replace(",", "")) if m else None


ALL_RE = re.compile(r"^\s*(all|--\s*all\s*--)\s*$", re.I)


def _beat_candidates(page):
    """Every <select> on the page that offers an 'ALL' option (the Beat filter), excluding the
    DataTables 'Show N entries' boxes. Works for plain selects and select2-enhanced ones."""
    out = []
    for sel in page.driver.find_elements(By.TAG_NAME, "select"):
        try:
            name = (sel.get_attribute("name") or "") + " " + (sel.get_attribute("id") or "")
            if name.strip().endswith("_length") or "_length" in name:
                continue
            options = sel.find_elements(By.TAG_NAME, "option")
            if len(options) >= 2 and any(ALL_RE.match(o.get_attribute("textContent") or "") for o in options):
                out.append(sel)
        except StaleElementReferenceException:
            continue
    # Prefer a dropdown that is clearly the Beat filter.
    out.sort(key=lambda e: 0 if "beat" in ((e.get_attribute("id") or "") + (e.get_attribute("name") or "")).lower() else 1)
    return out


def _select_info(page, sel):
    try:
        return page.driver.execute_script(
            "var s=arguments[0]; var o=s.options[s.selectedIndex];"
            "return (s.id||s.name||'?') + '=' + (o ? o.text.trim() : '') + ' (' + s.options.length + ' options'"
            " + (s.classList.contains('select2-hidden-accessible') ? ', select2' : '') + ')';", sel)
    except Exception:
        return "?"


def _all_selects_info(page):
    infos = []
    for sel in page.driver.find_elements(By.TAG_NAME, "select")[:12]:
        try:
            opts = [o.get_attribute("textContent").strip() for o in sel.find_elements(By.TAG_NAME, "option")][:6]
            infos.append(f"{sel.get_attribute('id') or sel.get_attribute('name') or '?'}:{opts}")
        except Exception:
            continue
    return infos


def _force_all_beat(page, min_customers=2, timeout=20):
    """Choose 'ALL' in the Beat filter and make the customer list reload. Always done (and the change
    event always fired, even if it already shows ALL): the beat is stored per login on the server and
    the parallel workers share one login, so the list can be loaded for a beat the dropdown does not
    show. Never picks a single beat. Returns a diagnostic string for error messages."""
    end = time.time() + 10
    candidates = []
    while time.time() < end and not candidates:
        candidates = _beat_candidates(page)
        if not candidates:
            time.sleep(0.5)
    if not candidates:
        return f"no dropdown with an 'ALL' option found; dropdowns on page: {_all_selects_info(page)}"

    sel = candidates[0]
    before = _select_info(page, sel)
    try:
        all_value = next(o.get_attribute("value") for o in sel.find_elements(By.TAG_NAME, "option")
                         if ALL_RE.match(o.get_attribute("textContent") or ""))
        page.driver.execute_script(
            "var s=arguments[0], v=arguments[1];"
            "if (window.jQuery) { jQuery(s).val(v).trigger('change'); jQuery(s).trigger({type:'select2:select'}); }"
            "else { s.value=v; s.dispatchEvent(new Event('change', {bubbles:true})); }",
            sel, all_value,
        )
        how = "set ALL + change event"
    except Exception as exc:
        how = f"error: {exc.__class__.__name__}"

    total = None
    end = time.time() + timeout
    while time.time() < end:
        try:
            _, wrapper = _customer_table(page, timeout=5)
            total = _total_entries(wrapper)
            if total is not None and total >= min_customers:
                break
        except Exception:
            pass
        time.sleep(0.5)
    diag = f"beat before={before}, {how}, after={_select_info(page, sel)}, customers loaded={total}"
    if total is None or total < min_customers:
        diag += f"; dropdowns on page: {_all_selects_info(page)}"
    return diag


def pick_customer(page, name, max_pages=20):
    diag = _force_all_beat(page)
    try:
        return _pick_customer_in_current_beat(page, name, max_pages)
    except TimeoutException:
        # The beat may have been switched by another worker in between: reload, force ALL again, retry once.
        try:
            page.driver.refresh()
            time.sleep(2)
        except Exception:
            pass
        diag2 = _force_all_beat(page)
        try:
            return _pick_customer_in_current_beat(page, name, max_pages)
        except TimeoutException as exc:
            raise TimeoutException(f"{exc.msg} | Beat 1st try: {diag} | 2nd try: {diag2}")


def _pick_customer_in_current_beat(page, name, max_pages=20, quick=False):
    seen_pages = []
    for term in ((name,) if quick else (name, f'"{name}"')):
        search, wrapper = _customer_table(page)
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
            row = _wait_for_match(wrapper, name, timeout=(5 if quick else 15) if page_no == 1 else 8)
            if row is not None:
                btn = row.find_element(
                    By.XPATH, ".//a[contains(normalize-space(.),'Select')] | .//button[contains(normalize-space(.),'Select')]"
                )
                page.js_click(btn)
                return
            seen_pages.append(f"search {term!r} page {page_no}: {_info_text(wrapper)} rows={_row_texts(wrapper)}")
            if not _click_next_and_wait(page, wrapper):
                break

    raise TimeoutException(f"Customer row for '{name}' not found on any results page ({'; '.join(seen_pages)})")
