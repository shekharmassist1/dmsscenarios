import re
import time

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from pages.base_page import BasePage
from utilities.performance import attach_page_performance


def _parse_float(text):
    match = re.search(r"[\d.]+", text)
    return float(match.group()) if match else 0.0


class ProductPage(BasePage):
    URL = "https://admin.massistcrm.com/DMSPages/SaleProduct.html"
    last_calc_alert = None

    CUSTOMER_SEARCH_INPUT = (By.XPATH, "//input[@type='search']")
    PRODUCT_ROWS = (By.CSS_SELECTOR, "#productlist tbody tr")
    SALE_QTY_INPUTS = (By.CSS_SELECTOR, "#productlist tbody tr input.SaleQty")
    PRODUCT_SEARCH_INPUT = (By.ID, "searchProduct")

    CALC_BUTTON = (By.ID, "lblCalculate")
    SUMMARY_TOTAL_ITEM = (By.CSS_SELECTOR, "#divitem span")
    SUMMARY_AMOUNT = (By.CSS_SELECTOR, "#divAmount span")
    SUMMARY_QTY_PCS = (By.CSS_SELECTOR, "#divQtyPcs span")
    SUMMARY_ALL_QTY_PCS = (By.CSS_SELECTOR, "#divAllQtyPcs span")
    SUMMARY_TOTAL_GST = (By.CSS_SELECTOR, "#divGST span")
    SUMMARY_FINAL_AMOUNT = (By.CSS_SELECTOR, "#totalPayAmt span")
    SUMMARY_FREE_ITEM = (By.CSS_SELECTOR, "#divfreeItem span")
    SUMMARY_TOTAL_SCHEME = (By.CSS_SELECTOR, "#divschemeapplicable span")

    ANY_ALERT_TITLE = (
        By.XPATH,
        "//span[contains(@class,'jconfirm-title')][starts-with(normalize-space(text()),'Alert')]",
    )

    VIEW_SELECTED_BUTTON = (By.ID, "btnViewAllSelectedItems")
    SELECTED_POPOVER = (By.ID, "viewSelectedItemsPopover")
    SELECTED_POPOVER_CLOSE = (By.CSS_SELECTOR, "#viewSelectedItemsPopover .vsi-close")

    ADD_MORE_BUTTON = (By.CSS_SELECTOR, "button.AddMoreProduct")

    PRINT_BUTTON = (By.ID, "btnPrintPreview")
    PRINT_PREVIEW_BOX = (By.CSS_SELECTOR, ".jconfirm-box.printpriview")
    PRINT_PREVIEW_TITLE = (By.XPATH, "//*[normalize-space(text())='Print Preview']")
    PRINT_PREVIEW_NOTE = (By.XPATH, "//*[contains(text(),'Invoice Preview Only')]")
    PRINT_PREVIEW_IFRAME = (By.ID, "frmPrintPreview")
    PRINT_PREVIEW_CLOSE = (
        By.XPATH,
        "//div[contains(@class,'jconfirm-box') and contains(@class,'printpriview')]"
        "//div[contains(@class,'jconfirm-buttons')]/button[normalize-space(text())='Close']",
    )

    SAVE_DRAFT_BUTTON = (By.CLASS_NAME, "AddDraftProduct")
    DRAFT_ALERT_CONTENT = (By.XPATH, "//div[contains(@class,'jconfirm-content') and contains(.,'Draft')]")
    DRAFT_ALERT_OKAY = (
        By.XPATH,
        "//div[contains(@class,'jconfirm-content') and contains(.,'Draft')]"
        "/ancestor::div[contains(@class,'jconfirm-box')]//div[contains(@class,'jconfirm-buttons')]/button",
    )

    SAVE_BUTTON = (By.ID, "cartItemBtn")
    SAVE_PANEL_CLIENT_NAME_LABEL = (By.XPATH, "//td/b[normalize-space(text())='Client Name']")
    SAVE_PANEL_CLIENT_NAME_INPUT = (By.ID, "contactperson")
    SAVE_PANEL_PAYABLE_AMOUNT = (By.CSS_SELECTOR, "input.clsPaymentValue")
    ADD_SALE_BUTTON = (By.ID, "btnCart")

    CONFIRM_SALE_TITLE = (By.XPATH, "//span[contains(@class,'jconfirm-title')][contains(.,'Confirm Sale')]")
    CONFIRM_SALE_TABLE = (By.CSS_SELECTOR, "table.tblConfirmSummary")
    CONFIRM_SALE_PROCEED_BUTTON = (
        By.XPATH,
        "//span[contains(@class,'jconfirm-title')][contains(.,'Confirm Sale')]"
        "/ancestor::div[contains(@class,'jconfirm-box')]//div[contains(@class,'jconfirm-buttons')]"
        "/button[contains(normalize-space(.),'Proceed')]",
    )

    UPDATE_SALE_BUTTON = (
        By.XPATH, "//button[@id='btnUpdateSale' and not(contains(@style,'display:none'))]"
    )
    CONFIRM_UPDATE_TITLE = (By.XPATH, "//span[contains(@class,'jconfirm-title')][contains(.,'Update Sale')]")
    CONFIRM_UPDATE_TABLE = (By.CSS_SELECTOR, "table.tblConfirmSummary")
    CONFIRM_UPDATE_PROCEED_BUTTON = (
        By.XPATH,
        "//span[contains(@class,'jconfirm-title')][contains(.,'Update Sale')]"
        "/ancestor::div[contains(@class,'jconfirm-box')]//div[contains(@class,'jconfirm-buttons')]"
        "/button[contains(normalize-space(.),'Proceed')]",
    )

    DISCOUNT_PERCENT_INPUT = (By.ID, "discount")

    POST_SALE_PRINT_PREVIEW_TITLE = (
        By.XPATH, "//span[contains(@class,'jconfirm-title')][contains(.,'Print Preview!')]"
    )
    POST_SALE_PRINT_BUTTON = (
        By.XPATH,
        "//span[contains(@class,'jconfirm-title')][contains(.,'Print Preview!')]"
        "/ancestor::div[contains(@class,'jconfirm-box')]//div[contains(@class,'jconfirm-buttons')]"
        "/button[normalize-space(text())='Print']",
    )

    SELECT_ALL_BUTTON = (By.CSS_SELECTOR, "input.btnSelectAllProduct")
    SELECT_ALL_MASTER_CHECKBOX = (By.ID, "selectallproducts")
    SELECT_ALL_SEARCH_INPUT = (By.ID, "txtprouctselectionsearch")
    SELECT_ALL_ENTER_BUTTON = (
        By.XPATH, "//div[contains(@class,'jconfirm-buttons')]/button[normalize-space(text())='Enter']"
    )
    SELECT_ALL_CANCEL_BUTTON = (
        By.XPATH,
        "//div[contains(@class,'jconfirm-buttons')]/button[translate(normalize-space(text()),"
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='cancel']",
    )

    def open(self):
        self.get(self.URL)
        self.find(self.CUSTOMER_SEARCH_INPUT)
        attach_page_performance(self.driver, "Bill/New Invoice - product page")
        return self

    def wait_for_grid_loaded(self, timeout=30):
        self.wait_until(
            lambda d: len(d.find_elements(*self.SALE_QTY_INPUTS)) > 0,
            timeout=timeout,
            message="Product grid rows never appeared",
        )
        return self

    def get_visible_product_row_count(self):
        return len(self.find_all(self.PRODUCT_ROWS))

    @staticmethod
    def _customer_row_locator(name):
        return (By.XPATH, f"//td[normalize-space(text())='{name}']/parent::tr")

    # Fallback customer to try if the primary one has no products assigned (the app shows a
    # blocking "Product not exists!" alert in that case rather than loading the grid).
    FALLBACK_CUSTOMER = "Demo Dealer 4"

    def _select_customer_once(self, name):
        search = self.find(self.CUSTOMER_SEARCH_INPUT)
        search.clear()
        search.send_keys(name)
        row = self.wait_until(
            EC.presence_of_element_located(self._customer_row_locator(name)),
            message=f"Customer row for '{name}' never appeared in the search results",
        )
        select_btn = row.find_element(
            By.XPATH, ".//button[contains(text(),'Select')] | .//a[contains(text(),'Select')]"
        )
        self.js_click(select_btn)

    def select_customer(self, name):
        self._select_customer_once(name)

        alert_message = self.dismiss_blocking_alert()
        if alert_message and "product not exist" in alert_message.lower():
            if name == self.FALLBACK_CUSTOMER:
                raise AssertionError(
                    f"Customer '{name}' has no products available, and it is "
                    f"already the fallback customer -- no further fallback to try"
                )
            self._select_customer_once(self.FALLBACK_CUSTOMER)

        self.wait_until(
            lambda d: len(d.find_elements(*self.SALE_QTY_INPUTS)) > 0,
            timeout=30,
            message=f"Product grid never loaded after selecting customer '{name}'",
        )
        return self

    def product_row(self, index):
        # The product grid can re-render mid-read (e.g. a live stock/price refresh) -- this makes
        # several sequential find_element calls against the same row, so a single attempt can go
        # stale partway through; re-fetch the row fresh and retry rather than trusting one reference
        # across all of them.
        last_exc = None
        for _ in range(3):
            try:
                rows = self.find_all(self.PRODUCT_ROWS)
                row = rows[index]
                name_cell = row.find_element(By.CSS_SELECTOR, "td.Variant_Name")
                item_code = name_cell.find_element(By.CSS_SELECTOR, "label.barcode").get_attribute("barcode").strip()
                display_name = name_cell.find_element(By.CSS_SELECTOR, "span.Variant_Name").get_attribute(
                    "product_name"
                ).strip()
                qty_input = row.find_element(By.CSS_SELECTOR, "input.SaleQty")
                product_id = qty_input.get_attribute("data-productid")
                stock_text = row.find_element(By.CSS_SELECTOR, "td.InventoryLabel").text
                price_text = row.find_element(By.CSS_SELECTOR, "td.Price span").text
                try:
                    scheme_id = row.find_element(By.CSS_SELECTOR, "div.scheme_code").get_attribute("schemeid")
                except StaleElementReferenceException:
                    raise
                except Exception:
                    scheme_id = None
                return {
                    "item_code": item_code,
                    "display_name": display_name,
                    "product_id": product_id,
                    "qty_input": qty_input,
                    "available_stock": _parse_float(stock_text),
                    "price": _parse_float(price_text),
                    "scheme_id": scheme_id,
                }
            except StaleElementReferenceException as exc:
                last_exc = exc
                time.sleep(0.5)
        raise last_exc

    def get_scheme_tiers(self, row_index):
        """Opens the row's 'Scheme Details' popup (via its gift icon -- confirmed live this needs a
        native click, a JS-synthesized click does not trigger it) and returns the tier table as
        [{"min": float, "max": float, "free_qty": str, "product_name": str}, ...], sorted lowest
        tier first. Reads the real, current tiers rather than assuming they match any previously
        recorded values -- schemes on this app can be reassigned/rotated over time (confirmed live:
        a product's scheme id and tier ranges changed between test sessions)."""
        def _visible_modal():
            boxes = [b for b in self.driver.find_elements(By.CSS_SELECTOR, ".modal-content") if b.is_displayed()]
            return boxes[0] if boxes else None

        def _click_gift_icon():
            time.sleep(1)
            # The product grid can re-render (e.g. a live stock/price refresh) between fetching the
            # row and clicking it, going stale mid-click -- re-fetch fresh and retry rather than
            # trusting a single row/gift_icon reference.
            last_exc = None
            for _ in range(3):
                try:
                    rows = self.find_all(self.PRODUCT_ROWS)
                    row = rows[row_index]
                    gift_icon = row.find_element(By.CSS_SELECTOR, "span.offer.available_scheme")
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", gift_icon)
                    gift_icon.click()
                    return
                except StaleElementReferenceException as exc:
                    last_exc = exc
                    time.sleep(0.5)
            raise last_exc

        # Confirmed live: this click intermittently doesn't register at all (same low-frequency
        # class of click flake seen throughout this app) -- retry the click once, but only if the
        # modal genuinely never appeared (re-clicking a modal that IS already open just hits its
        # own backdrop and throws ElementClickInterceptedException).
        _click_gift_icon()
        modal = None
        for _ in range(16):
            modal = _visible_modal()
            if modal:
                break
            time.sleep(0.5)
        if modal is None:
            _click_gift_icon()
            modal = self.wait_until(
                lambda d: _visible_modal(),
                timeout=20,
                message="Scheme Details modal never appeared after clicking the scheme icon (retried)",
            )
        # The modal itself is a pre-rendered node just toggled visible (confirmed live, not
        # recreated), but reading its text/Cancel button can still hit a stale reference if the
        # visible modal swaps (e.g. the earlier "modal is None" retry path re-opens it) between
        # locating it above and reading it here -- re-resolve and retry rather than trusting the
        # single reference.
        lines = None
        cancel_btn = None
        last_exc = None
        for _ in range(6):
            try:
                modal = _visible_modal() or modal
                lines = [l.strip() for l in modal.text.splitlines() if l.strip()]
                cancel_btn = modal.find_element(By.XPATH, ".//button[normalize-space(text())='Cancel']")
                break
            except StaleElementReferenceException as exc:
                last_exc = exc
                time.sleep(0.5)
        else:
            raise last_exc
        tiers = []
        try:
            i = lines.index("Variant Id") + 1
        except ValueError:
            i = len(lines)
        while i + 5 < len(lines) and not lines[i].lower().startswith("remarks"):
            try:
                min_amt = float(lines[i])
                max_amt = float(lines[i + 1])
            except ValueError:
                break
            tiers.append({
                "min": min_amt, "max": max_amt,
                "discount": lines[i + 2], "free_qty": lines[i + 3], "product_name": lines[i + 4],
            })
            i += 6
        self.js_click(cancel_btn)
        self.wait_until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal-content")),
            message="Scheme Details modal did not close after clicking Cancel",
        )
        return sorted(tiers, key=lambda t: t["min"])

    def enter_quantity(self, row_index, qty):
        info = self.product_row(row_index)
        inp = info["qty_input"]
        self.js_click(inp)
        inp.clear()
        inp.send_keys(str(qty))
        inp.send_keys(Keys.TAB)
        return info["item_code"]

    def get_available_stock(self, row_index):
        return self.product_row(row_index)["available_stock"]

    def click_add_more(self):
        """On the Edit Sale page, the product grid is initially scoped to only the order's existing
        items. Clicking 'Add More' expands it to the full catalog (existing items keep their saved
        quantities pre-filled), but first shows two sequential jconfirm alerts -- 'Calculation in
        process!' then 'Product loaded' -- each requiring its own dismissal before the expanded grid
        is usable."""
        self.click(self.ADD_MORE_BUTTON)
        for _ in range(2):
            self.dismiss_one_alert(timeout=5)
        self.wait_until(
            lambda d: len(d.find_elements(*self.PRODUCT_ROWS)) > 5,
            timeout=15,
            message="Product grid never expanded to the full catalog after clicking Add More",
        )
        return self

    def enter_insufficient_quantity(self, row_index, buffer=25):
        info = self.product_row(row_index)
        qty = int(info["available_stock"]) + buffer
        return self.enter_quantity(row_index, qty), qty

    def dismiss_one_alert(self, timeout=3):
        try:
            title_el = self.wait_until(EC.visibility_of_element_located(self.ANY_ALERT_TITLE), timeout=timeout)
        except Exception:
            return None
        box = title_el.find_element(By.XPATH, "ancestor::div[contains(@class,'jconfirm-box')]")
        message = box.find_element(By.CSS_SELECTOR, ".jconfirm-content").text.strip()
        okay_btn = box.find_element(By.XPATH, ".//div[contains(@class,'jconfirm-buttons')]/button")
        self.js_click(okay_btn)
        self.wait_until(
            EC.invisibility_of_element_located(self.ANY_ALERT_TITLE),
            timeout=10,
            message="Alert dialog did not close after clicking its OK button",
        )
        return message

    def dismiss_any_alert(self, timeout=3, max_alerts=10):
        messages = []
        for _ in range(max_alerts):
            message = self.dismiss_one_alert(timeout=timeout)
            if message is None:
                break
            messages.append(message)
            timeout = 1
        if not messages:
            return None
        return " | ".join(messages)

    def click_calc(self):
        self.click(self.CALC_BUTTON)
        seen_alerts = []

        def _final_amount_ready(d):
            # An insufficient-inventory alert can block the Final Amount from updating until dismissed,
            # so dismiss opportunistically while polling instead of waiting for it to clear on its own.
            msg = self.dismiss_one_alert(timeout=0.3)
            if msg:
                seen_alerts.append(msg)
            return any(ch.isdigit() for ch in d.find_element(*self.SUMMARY_FINAL_AMOUNT).text)

        self.wait_until(_final_amount_ready, timeout=30, message="Final Amount never populated after clicking Calc")
        trailing = self.dismiss_any_alert(timeout=8)
        if trailing:
            seen_alerts.append(trailing)
        self.last_calc_alert = " | ".join(seen_alerts) if seen_alerts else None
        return self

    def get_summary(self):
        return {
            "total_item": self.text_of(self.SUMMARY_TOTAL_ITEM),
            "amount": self.text_of(self.SUMMARY_AMOUNT),
            "qty_pcs": self.text_of(self.SUMMARY_QTY_PCS),
            "all_qty_pcs": self.text_of(self.SUMMARY_ALL_QTY_PCS),
            "total_gst": self.text_of(self.SUMMARY_TOTAL_GST),
            "final_amount": self.text_of(self.SUMMARY_FINAL_AMOUNT),
            "free_item": self.text_of(self.SUMMARY_FREE_ITEM),
            "total_scheme": self.text_of(self.SUMMARY_TOTAL_SCHEME),
        }

    def search_product(self, text):
        box = self.find(self.PRODUCT_SEARCH_INPUT)
        box.clear()
        box.send_keys(text)
        self.wait_until(
            lambda d: len(d.find_elements(*self.PRODUCT_ROWS)) > 0,
            timeout=15,
            message=f"No product rows appeared after searching for '{text}'",
        )
        return self

    def open_view_selected_items(self):
        self.click(self.VIEW_SELECTED_BUTTON)
        self.wait_until(
            EC.visibility_of_element_located(self.SELECTED_POPOVER),
            message="View Selected Items popover never appeared",
        )
        return self

    def get_selected_items(self):
        popover = self.find(self.SELECTED_POPOVER)
        rows = popover.find_elements(By.CSS_SELECTOR, "table tbody tr")
        items = []
        for r in rows:
            cells = r.find_elements(By.TAG_NAME, "td")
            if len(cells) < 6:
                continue
            items.append({
                "vsku": cells[1].text.strip(),
                "item_name": cells[2].text.strip(),
                "unit_qty": cells[3].text.strip(),
                "qty": cells[4].text.strip(),
                "value": cells[5].text.strip(),
            })
        total = None
        footer_cells = popover.find_elements(By.CSS_SELECTOR, "table tfoot tr td")
        if len(footer_cells) >= 3:
            total = {
                "unit_qty": footer_cells[-3].text.strip(),
                "qty_pcs": footer_cells[-2].text.strip(),
                "value": footer_cells[-1].text.strip(),
            }
        return items, total

    def close_selected_items(self):
        try:
            self.click(self.SELECTED_POPOVER_CLOSE)
        except Exception:
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        return self

    def click_print(self):
        self.click(self.PRINT_BUTTON)
        self.wait_until(
            EC.presence_of_element_located(self.PRINT_PREVIEW_TITLE),
            message="Print Preview modal (title 'Print Preview') never appeared after clicking Print",
        )
        return self

    def click_print_or_detect_error(self, timeout=15):
        """Click Print; return (True, None) if Print Preview opens, or (False, error_text) if an
        unrelated jconfirm error dialog appears instead (e.g. a permissions/authorization error)."""
        self.click(self.PRINT_BUTTON)

        def _outcome(d):
            if d.find_elements(*self.PRINT_PREVIEW_TITLE):
                return "preview"
            error_boxes = [
                b for b in d.find_elements(By.CSS_SELECTOR, ".jconfirm-box")
                if b.is_displayed() and "something went wrong" in b.text.lower()
            ]
            if error_boxes:
                return error_boxes[0].text
            return False

        result = self.wait_until(
            _outcome,
            timeout=timeout,
            message="Neither the Print Preview modal nor an error dialog appeared after clicking Print",
        )
        if result == "preview":
            return True, None
        return False, result

    def get_print_preview_note(self):
        return self.text_of(self.PRINT_PREVIEW_NOTE)

    def get_print_preview_iframe_src(self):
        return self.find(self.PRINT_PREVIEW_IFRAME).get_attribute("src")

    def close_print_preview(self):
        self.click(self.PRINT_PREVIEW_CLOSE)
        self.wait_until(
            EC.invisibility_of_element_located(self.PRINT_PREVIEW_BOX),
            message="Print Preview modal did not close after clicking its Close button",
        )
        return self

    def click_save_draft(self):
        self.dismiss_any_alert(timeout=2)
        self.click(self.SAVE_DRAFT_BUTTON)
        self.wait_until(
            EC.visibility_of_element_located(self.DRAFT_ALERT_CONTENT),
            message="Draft-saved confirmation alert (jconfirm-content containing 'Draft') never appeared "
                    "after clicking Save Drafts",
        )
        return self

    def get_draft_alert_text(self):
        return self.text_of(self.DRAFT_ALERT_CONTENT)

    def confirm_draft_alert(self):
        self.click(self.DRAFT_ALERT_OKAY)
        self.wait_until(
            EC.invisibility_of_element_located(self.DRAFT_ALERT_CONTENT),
            message="Draft-saved confirmation alert did not close after clicking its OKAY button",
        )
        return self

    def click_save(self):
        self.click(self.SAVE_BUTTON)
        self.wait_until(
            EC.visibility_of_element_located(self.SAVE_PANEL_CLIENT_NAME_LABEL),
            message="Save/payment panel (label 'Client Name') never appeared after clicking Save",
        )
        return self

    def get_save_panel_client_name(self):
        return self.find(self.SAVE_PANEL_CLIENT_NAME_INPUT).get_attribute("value")

    def get_payable_amount(self):
        return self.find(self.SAVE_PANEL_PAYABLE_AMOUNT).get_attribute("value")

    def apply_discount_percent(self, percent):
        inp = self.find(self.DISCOUNT_PERCENT_INPUT)
        self.js_click(inp)
        inp.clear()
        inp.send_keys(str(percent))
        inp.send_keys(Keys.TAB)
        self.wait_until(
            lambda d: d.find_element(*self.SAVE_PANEL_PAYABLE_AMOUNT).get_attribute("value") != "",
            message="Payable Amount did not update after applying the discount",
        )
        return self

    def close_save_panel(self):
        self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        return self

    def click_add_sale(self):
        self.click(self.ADD_SALE_BUTTON)
        self.wait_until(
            EC.visibility_of_element_located(self.CONFIRM_SALE_TITLE),
            message="'Confirm Sale?' dialog never appeared after clicking Add Sale",
        )
        return self

    def get_confirm_sale_details(self):
        table = self.find(self.CONFIRM_SALE_TABLE)
        rows = table.find_elements(By.TAG_NAME, "tr")
        details = {}
        for r in rows:
            cells = r.find_elements(By.TAG_NAME, "td")
            if len(cells) == 2:
                key = cells[0].text.strip().rstrip(":").strip()
                details[key] = cells[1].text.strip()
        return details

    def confirm_sale_proceed(self):
        self.click(self.CONFIRM_SALE_PROCEED_BUTTON)
        self.wait_until(
            EC.invisibility_of_element_located(self.CONFIRM_SALE_TITLE),
            message="'Confirm Sale?' dialog did not close after clicking Yes! Proceed.",
        )
        return self

    def click_update_sale(self):
        self.click(self.UPDATE_SALE_BUTTON)
        self.wait_until(
            EC.visibility_of_element_located(self.CONFIRM_UPDATE_TITLE),
            message="Confirmation dialog never appeared after clicking Update Sale",
        )
        return self

    def get_confirm_update_details(self):
        table = self.find(self.CONFIRM_UPDATE_TABLE)
        rows = table.find_elements(By.TAG_NAME, "tr")
        details = {}
        for r in rows:
            cells = r.find_elements(By.TAG_NAME, "td")
            if len(cells) == 2:
                key = cells[0].text.strip().rstrip(":").strip()
                details[key] = cells[1].text.strip()
        return details

    def confirm_update_proceed(self):
        self.click(self.CONFIRM_UPDATE_PROCEED_BUTTON)
        self.wait_until(
            EC.invisibility_of_element_located(self.CONFIRM_UPDATE_TITLE),
            message="Confirmation dialog did not close after clicking Proceed",
        )
        return self

    def wait_for_sale_completed(self):
        self.wait_until(
            EC.presence_of_element_located(self.CUSTOMER_SEARCH_INPUT),
            message="Did not return to the Select Customer screen after confirming the sale",
        )
        return self

    def dismiss_post_sale_print_preview(self):
        try:
            cancel_btn = self.wait_until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//*[contains(text(),'Print Preview')]"
                                "/ancestor::div[contains(@class,'jconfirm-box') or contains(@class,'modal-content')][1]"
                                "//button[normalize-space(text())='Cancel']")
                ),
                timeout=5,
            )
            self.js_click(cancel_btn)
        except Exception:
            pass
        return self

    def generate_invoice_and_get_url(self):
        main_handle = self.driver.current_window_handle
        self.wait_until(
            EC.visibility_of_element_located(self.POST_SALE_PRINT_PREVIEW_TITLE),
            message="Post-sale 'Print Preview!' dialog never appeared",
        )
        self.click(self.POST_SALE_PRINT_BUTTON)
        self.wait_until(
            lambda d: len(d.window_handles) > 1,
            timeout=15,
            message="Invoice tab did not open after clicking Print",
        )
        new_handle = next(h for h in self.driver.window_handles if h != main_handle)
        self.driver.switch_to.window(new_handle)
        self.wait_until(lambda d: "OrderId" in d.current_url, timeout=15, message="Invoice tab never loaded a report URL")
        url = self.driver.current_url
        time.sleep(1.5)
        screenshot = self.driver.get_screenshot_as_png()
        self.driver.close()
        self.driver.switch_to.window(main_handle)
        return url, screenshot

    def open_select_all_modal(self):
        self.click(self.SELECT_ALL_BUTTON)
        self.wait_until(
            EC.visibility_of_element_located(self.SELECT_ALL_SEARCH_INPUT),
            message="Select All modal never appeared",
        )
        return self

    def uncheck_all_in_select_all_modal(self):
        checkbox = self.find(self.SELECT_ALL_MASTER_CHECKBOX)
        if checkbox.is_selected():
            self.js_click(checkbox)
        return self

    def set_select_all_modal_quantity(self, product_id, qty):
        checkbox = self.find((By.CSS_SELECTOR, f"input.childproduct[id='{product_id}']"))
        if not checkbox.is_selected():
            self.js_click(checkbox)
        qty_input = self.find((By.CSS_SELECTOR, f"input.qty[product_id='{product_id}']"))
        self.js_click(qty_input)
        qty_input.clear()
        qty_input.send_keys(str(qty))
        return self

    def confirm_select_all_modal(self):
        self.click(self.SELECT_ALL_ENTER_BUTTON)
        self.wait_until(
            EC.invisibility_of_element_located(self.SELECT_ALL_SEARCH_INPUT),
            message="Select All modal did not close after clicking Enter",
        )
        return self
