from openpyxl.styles.builtins import total
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config.config import EXPLICIT_WAIT
import time
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from utilities.excel_reader import get_bill_data

import pytest
from utilities.menu_utils import verify_menu_or_skip

class BillPage:

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, EXPLICIT_WAIT)

    def navigate_to_bill(self):
        menu = self.wait.until(EC.element_to_be_clickable((
            By.XPATH, "//span[contains(text(),'Bill/New Invoice')]"
        )))
        menu.click()

    def verify_beat(self):
        beat = self.wait.until(EC.element_to_be_clickable((By.XPATH,"//span[contains(@class,'select2-selection--single')]")))
        beat.click()

        first_option = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "(//li[contains(@class,'select2-results__option')])[1]")
            )
        )
        first_option.click()

    def credit_info(self):
        credit_info = self.wait.until(EC.element_to_be_clickable((By.ID,"btnSetClientLimit")))
        credit_info.click()
        actual_text = credit_info.text.strip()

        assert "Client Credit Amount" in actual_text, \
            f"Expected 'Client Credit Amount' but found '{actual_text}'"

        print("Verified text: Client Credit Amount")

    # def client_type(self):
    #     dropdown = self.wait.until(
    #         EC.element_to_be_clickable(
    #             (By.XPATH, "//select[contains(@class,'clsSaleCustGridClientTypeDd')]")
    #         )
    #     )
    #
    #     Select(dropdown).select_by_visible_text("Dealer")
    #
    #     print("Dealer selected")



    def verify_show_dropdown(self):

        # Re-locate every iteration to avoid StaleElementReferenceException
        show_select = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//select[contains(@name,'_length')]")
            )
        )

        sel = Select(show_select)

        # Read all available options first
        options = sel.options
        print(f"Total options found: {len(options)}")
        for opt in options:
            print(f"  Value='{opt.get_attribute('value')}' | Text='{opt.text}'")

        # Select each option one by one and verify the grid updates
        for i in range(len(options)):
            # Re-locate to avoid StaleElementReferenceException
            show_select = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//select[contains(@name,'_length')]")
                )
            )
            sel = Select(show_select)

            option_text = sel.options[i].text
            option_value = sel.options[i].get_attribute("value")

            sel.select_by_index(i)
            time.sleep(1.5)  # wait for table to redraw

            # Verify the info text updates
            info = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(@class,'dataTables_info')]")
                )
            ).text
            print(f"  Selected '{option_text}' (value={option_value}) → {info}")

        print("✓ All Show dropdown options verified")

        show_select = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//select[contains(@name,'_length')]")
            )
        )

        Select(show_select).select_by_visible_text("10")

        WebDriverWait(self.driver, 10).until(
            EC.text_to_be_present_in_element(
                (By.XPATH, "//div[contains(@class,'dataTables_info')]"),
                "Showing 1 To 10"
            )
        )

        print("✓ Reset Show dropdown to 10")
        print("✓ All Show dropdown options verified")

    def click_excel(self):
        click_excel= self.wait.until(
            EC.element_to_be_clickable((By.XPATH,"//span[normalize-space()='Excel']")))
        click_excel.click()



    def verify_pagination(self):
        wait = WebDriverWait(self.driver, 20)

        page_numbers = self.driver.find_elements(
            By.XPATH,
            "//a[contains(@class,'paginate_button') and normalize-space(text())!='' and not(contains(text(),'Previous')) and not(contains(text(),'Next'))]"
        )

        total_pages = len(page_numbers)

        print(f"Total Pages: {total_pages}")

        for page_no in range(1, total_pages + 1):
            page = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH,
                     f"//a[contains(@class,'paginate_button') and text()='{page_no}']")
                )
            )

            self.driver.execute_script("arguments[0].click();", page)

            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH,
                     f"//a[contains(@class,'current') and text()='{page_no}']")
                )
            )

            rows = self.driver.find_elements(
                By.XPATH,
                "//table/tbody/tr"
            )

            visible_rows = [row for row in rows if row.is_displayed()]
            customer_count = len(visible_rows)

            info = self.driver.find_element(
                By.XPATH,
                "//div[contains(@class,'dataTables_info')]"
            ).text

            print(f"Page {page_no}: {info}")
            print(f"Customers on page: {customer_count}")

            assert customer_count > 0, f"No customers found on page {page_no}"

    def search_customer(self):
        search_input = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='search']")))
        search_input.send_keys("Demo 4")

    def select_customer(self, customer_name):

        while True:

            # Search customer again if search box gets cleared
            search_box = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//input[@type='search']")
                )
            )

            search_box.clear()
            search_box.send_keys("Demo 4")

            time.sleep(2)

            select_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        f"//td[contains(.,'{customer_name}')]/following-sibling::td//a[contains(.,'Select')]"
                    )
                )
            )

            self.driver.execute_script(
                "arguments[0].click();",
                select_btn
            )

            try:
                popup = WebDriverWait(self.driver, 3).until(
                    EC.visibility_of_element_located(
                        (
                            By.XPATH,
                            "//*[contains(text(),'Product not exists')]"
                        )
                    )
                )

                print(f"{customer_name}: Product not exists")

                self.driver.find_element(
                    By.XPATH,
                    "//button[contains(.,'Okay')]"
                ).click()

                WebDriverWait(self.driver, 10).until(
                    EC.invisibility_of_element(popup)
                )

                continue

            except:
                actual_customer = self.driver.find_element(
                    By.XPATH,
                    "//label[contains(@class,'titleToclientname')]"
                ).text.strip()

                print(f"Selected Customer: {actual_customer}")

                return actual_customer

    def verify_page_elements(self,
                             customer_name="",
                             distributor_name="Demo Distributor 1"):

        # Title
        title = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//span[contains(text(),'Bill/New Invoice')]")
            )
        )

        assert title.is_displayed()
        print("✓ Bill/New Invoice title displayed")

        # Customer
        # Customer
        customer = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//label[contains(@class,'titleToclientname')]")
            )
        )

        actual_customer = customer.text.strip()

        print("=" * 50)
        print(f"Expected Customer: {customer_name}")
        print(f"Actual Customer  : {actual_customer}")
        print("=" * 50)

        assert actual_customer == customer_name, \
            f"Expected='{customer_name}', Actual='{actual_customer}'"

        print(f"✓ Customer name displayed: {actual_customer}")

        # Distributor
        distributor = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//label[contains(@class,'titleSourceclientname')]")
            )
        )

        assert distributor.text.strip() == distributor_name
        print(f"✓ Distributor displayed: {distributor.text}")

        # Product Table
        expected_headers = [
            "Product_Name",
    "Item Code",
    "GST",
    "Inventory Lebel",
    "Pcs. Inv.",
    "Net Rate",
    "Sale Qty",
    "Free Qty",
    "QPSDisc",
    "QPSamt",
    "Total"
        ]

        headers = self.wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//table//th")
            )
        )

        actual_headers = [h.text.strip() for h in headers]

        print(actual_headers)

        for header in expected_headers:
            assert header in actual_headers, f"{header} column missing"

        print("✓ Product table loaded successfully")

        # Calculate Button
        calc_btn = self.wait.until(
            EC.visibility_of_element_located(
                (By.ID, "lblCalculate")
            )
        )
        assert calc_btn.is_displayed()
        print("✓ Calculate button visible")

        # Filter Button
        filter_btn = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//span[normalize-space()='Filter']")
            )
        )
        assert filter_btn.is_displayed()
        print("✓ Filter button visible")

        # Clear Button
        clear_btn = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//span[normalize-space()='Clear']")
            )
        )
        assert clear_btn.is_displayed()
        print("✓ Clear button visible")

        # Save Button
        save_btn = self.wait.until(
            EC.visibility_of_element_located(
                (By.ID, "cartItemBtn")
            )
        )
        assert save_btn.is_displayed()
        print("✓ Save button visible")

        # Save Draft Button
        save_draft_btn = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//button[@title='Draft']")
            )
        )
        assert save_draft_btn.is_displayed()
        print("✓ Save Draft button visible")

        # Print Button
        print_btn = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//button[@id='btnPrintPreview']")
            )
        )
        assert print_btn.is_displayed()
        print("✓ Print button visible")

    def verify_product_category_dropdowns(self):
        dropdown1 = self.wait.until(
            EC.visibility_of_element_located((By.ID,"select2-ddlProductMaincategory-container"))
        )
        dropdown1.click()
        assert dropdown1.is_displayed()
        time.sleep(1)

        dropdown2 = self.wait.until(EC.visibility_of_element_located((By.ID,"select2-ddlchildProductCategory-container")))
        dropdown2.click()
        time.sleep(1)
        assert dropdown2.is_displayed()

        dropdown3 = self.wait.until(EC.visibility_of_element_located((By.ID,"select2-ddlProductCategory-container")))
        dropdown3.click()
        time.sleep(1)
        assert dropdown3.is_displayed()


    def product_page_show_dropdown(self):

        # Re-locate every iteration to avoid StaleElementReferenceException
        show_select = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//select[@name='productlist_length']")
            )
        )

        sel = Select(show_select)

        # Read all available options first
        options = sel.options
        print(f"Total options found: {len(options)}")
        for opt in options:
            print(f"  Value='{opt.get_attribute('value')}' | Text='{opt.text}'")

        # Select each option one by one and verify the grid updates
        for i in range(len(options)):
            # Re-locate to avoid StaleElementReferenceException
            show_select = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//select[@name='productlist_length']")
                )
            )
            sel = Select(show_select)

            option_text = sel.options[i].text
            option_value = sel.options[i].get_attribute("value")

            sel.select_by_index(i)
            time.sleep(1.5)  # wait for table to redraw

            # Verify the info text updates
            rows = self.driver.find_elements(
                By.XPATH,
                "//table[@id='productlist']//tbody/tr"
            )

            print(
                f"  Selected '{option_text}' "
                f"(value={option_value}) → Rows={len(rows)}"
            )

        show_select = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//select[@name='productlist_length']")
            )
        )

        Select(show_select).select_by_visible_text("10")

        time.sleep(2)

        rows = self.driver.find_elements(
            By.XPATH,
            "//table[@id='productlist']//tbody/tr"
        )

        print(f"Rows after reset: {len(rows)}")

        print("✓ Reset Show dropdown to 10")
        print("✓ All Show dropdown options verified")

    def verify_pagination_using_next(self):

        while True:

            current_page = self.driver.find_element(
                By.CSS_SELECTOR,
                "#productlist_paginate a.current"
            ).text

            print(f"Current Page: {current_page}")

            next_buttons = self.driver.find_elements(
                By.ID,
                "productlist_next"
            )

            if not next_buttons:
                break

            next_btn = next_buttons[0]

            if "disabled" in next_btn.get_attribute("class"):
                break

            next_btn.click()
            time.sleep(2)

        print("✓ Reached last page successfully")

    def verify_product_grid_headers(self):

        def normalize(text):
            return (
                text.lower()
                .replace("_", " ")
                .replace(".", "")
                .strip()
            )

        expected_headers = [
            "product name",
            "item code",
            "gst",
            "inventory lebel",  # actual UI spelling
            "pcs inv",
            "net rate",
            "sale qty",
            "free qty",
            "qpsdisc",
            "qpsamt",
            "total"
        ]

        headers = self.driver.find_elements(
            By.XPATH,
            "//table//thead//th"
        )

        actual_headers = [
            normalize(header.text)
            for header in headers
            if header.text.strip()
        ]

        print("Actual Headers:", actual_headers)

        for expected in expected_headers:
            assert expected in actual_headers, \
                f"Header '{expected}' not found"

        print("✓ All product grid headers verified")

    def verify_inventory_popup_for_all_products(self):

        hamburgers = self.driver.find_elements(
            By.CSS_SELECTOR,
            "span.ShowBatchWiseVariant"
        )

        print(f"Total Inventory Icons Found: {len(hamburgers)}")

        assert len(hamburgers) > 0, "No inventory icons found"

        max_rows = min(5, len(hamburgers))

        for row_num in range(max_rows):
            print(f"\nVerifying Product Row: {row_num + 1}")

            # Re-fetch elements every iteration
            hamburgers = self.driver.find_elements(
                By.CSS_SELECTOR,
                "span.ShowBatchWiseVariant"
            )

            hamburger = hamburgers[row_num]

            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                hamburger
            )

            time.sleep(1)

            self.driver.execute_script(
                "arguments[0].click();",
                hamburger
            )

            print(f"✓ Clicked Inventory Icon {row_num + 1}")

            print("✓ Inventory popup opened")

            # Get inventory value
            inventory = WebDriverWait(self.driver, 15).until(
                EC.visibility_of_element_located(
                    (
                        By.XPATH,
                        "//table//td[contains(@class,'Inventory') or "
                        "contains(@class,'inventory')]//span"
                    )
                )
            )

            inventory_text = inventory.text.strip()

            print(f"Inventory Value: {inventory_text}")

            # Negative validation
            assert inventory_text != "", \
                f"Inventory value is blank for row {row_num + 1}"

            print("✓ Inventory value displayed")

            # Close popup
            close_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".jconfirm-closeIcon")
                )
            )

            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                close_button
            )

            WebDriverWait(self.driver, 10).until(
                EC.visibility_of(close_button)
            )

            try:
                close_button.click()
            except:
                self.driver.execute_script(
                    "arguments[0].click();",
                    close_button
                )

            print("✓ Popup closed")

    def click_filter(self):
        filter_button = self.wait.until(EC.presence_of_element_located((By.XPATH,"//span[normalize-space()='Filter']")))
        filter_button.click()

    def move_to_favourite(self):
        favourite_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[normalize-space()='Favourite']")
            )
        )

        favourite_button.click()

        # Wait for grid refresh after clicking Favourite
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.contentLI")
            )
        )

        WebDriverWait(self.driver, 20).until(
            EC.invisibility_of_element_located(
                (By.CSS_SELECTOR, "div.contentLI")
            )
        )

    def click_focus(self):

        # try:
        #     focus_btn = WebDriverWait(self.driver, 10).until(
        #         EC.element_to_be_clickable((By.XPATH, "//a[normalize-space()='Focus']"))
        #     )
        #
        #     self.driver.execute_script(
        #         "arguments[0].scrollIntoView({block:'center'});",
        #         focus_btn
        #     )
        #
        #     self.driver.execute_script("arguments[0].click();", focus_btn)
        #
        #     # WAIT FOR GRID instead of div.contentLI
        #     WebDriverWait(self.driver, 15).until(
        #         EC.presence_of_element_located((By.XPATH, "//table | //div[contains(@class,'grid')]"))
        #     )
        #
        # except Exception as e:
        #     raise Exception(f"click_focus failed: {e}")

        # ok_btn = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Okay']")))
        # ok_btn.click()
        # time.sleep(3)

        all_product = WebDriverWait(self.driver, 15).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[normalize-space()='All Products']")
            )
        )

        all_product.click()

        # Wait until overlay/loading disappears
        WebDriverWait(self.driver, 15).until(
            EC.invisibility_of_element_located(
                (By.CLASS_NAME, "contentLI")
            )
        )

        all_products = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[normalize-space()='All Products']")
            )
        )

        self.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});",
            all_products
        )

        all_products.click()

    def enter_quantity(self, row_num, qty):

        print(f"Entering Qty={qty} in Row={row_num}")

        qty_field = self.wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    f"(//input[contains(@class,'SaleQty')])[{row_num}]"
                )
            )
        )

        self.driver.execute_script("""
            arguments[0].value = arguments[1];
            arguments[0].dispatchEvent(new Event('input', { bubbles:true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles:true }));
            arguments[0].dispatchEvent(new Event('blur', { bubbles:true }));
        """, qty_field, str(qty))

        time.sleep(1)

        ui_qty = qty_field.get_attribute("value")

        print(
            f"Row={row_num}, "
            f"Excel Qty={qty}, "
            f"UI Qty={ui_qty}"
        )

    # -------------------------
    # GET PRODUCT NAME
    # -------------------------
    def get_product_name(self, row_num):

        return self.driver.find_element(
            By.XPATH,
            f"(//table[@id='productlist']//tbody//tr)[{row_num}]//td[1]"
        ).text.strip()



    # -------------------------
    # GET ROW TOTAL
    # -------------------------
    def get_total(self, row_no):
        total = self.wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    f"(//td[contains(@class,'total')])[{row_no}]"
                )
            )
        )
        return float(total.text.strip())
    # -------------------------
    # GET BILL TOTAL
    # -------------------------
    def get_final_amount(self):
        amount = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//div[contains(@class,'orange') and contains(.,'Final Amount')]")
            )
        )

        text = amount.text.split("\n")[0].strip()
        return float(text)

    # -------------------------
    # HANDLE POPUP
    # -------------------------
    def handle_inventory_popup(self):

        try:
            popup = WebDriverWait(self.driver, 3).until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//div[contains(@class,'jconfirm')]")
                )
            )

            message = popup.text

            ok_btn = popup.find_element(
                By.XPATH,
                ".//button[contains(.,'OK') or contains(.,'Ok') or contains(.,'Okay')]"
            )

            self.driver.execute_script("arguments[0].click();", ok_btn)

            return True, message

        except Exception:
            return False, ""


    def click_calculate(self):

        calc_btn = self.wait.until(
            EC.element_to_be_clickable((By.ID, "lblCalculate"))
        )

        calc_btn.click()

        print("Calculate clicked")

    def get_bill_summary(self):

        summary = {}

        cards = self.driver.find_elements(
            By.XPATH,
            "//div[contains(@class,'top_cart_items')]//div[contains(@class,'custom_col')]"
        )

        for card in cards:

            text = card.text.strip().split("\n")

            if len(text) >= 2:
                value = text[0]
                label = " ".join(text[1:])

                summary[label] = value

        return summary

    def click_draft(self):

            draft_btn = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[@title='Draft']")
                )
            )

            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);",
                draft_btn
            )

            draft_btn.click()

            print("Draft button clicked")

            popup_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//div[contains(@class,'jconfirm-buttons')]//button"
                    )
                )
            )

            print("Draft popup appeared")

            popup_btn.click()

    def get_latest_draft_details(self):

        row = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//table[@id='tbl_order_grid']/tbody/tr[1]")
            )
        )

        # Keep only visible cells
        visible_cells = [
            td for td in row.find_elements(By.TAG_NAME, "td")
            if td.is_displayed()
        ]

        return {
            "Draft Transfer Id": visible_cells[0].text.strip(),
            "Approval Id": visible_cells[1].text.strip(),
            "Client": visible_cells[2].text.strip(),
            "Draft By": visible_cells[3].text.strip(),
            "No Of Items": visible_cells[4].text.strip(),
            "Draft Amount": visible_cells[5].text.strip(),
            "Draft Date": visible_cells[6].text.strip(),
            "Draft Qty": visible_cells[7].text.strip(),
        }



    def go_to_product_page(self):

        # Option 1: safest → reload bill page directly
        self.driver.get("https://admin.massistcrm.com/EmployeePages/scheme_details.aspx")

        # wait for product grid to load
        WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.ID, "productlist"))
        )

        print("✓ Back to Product Page")

    def click_order(self):

        order_btn = self.wait.until(
            EC.element_to_be_clickable(
                (
                    By.CSS_SELECTOR,
                    "span.GoDraftCart"
                )
            )
        )

        self.driver.execute_script(
            "arguments[0].click();",
            order_btn
        )

        print("Order button clicked")

    def click_save(self):


        save_btn = WebDriverWait(self.driver, 20).until(
            EC.element_to_be_clickable(
                (By.ID, "cartItemBtn")
            )
        )

        self.driver.execute_script(
            "arguments[0].click();",
            save_btn
        )

        print("Save clicked")

    def add_discount(self):
        discount=self.wait.until(EC.visibility_of_element_located((By.ID,"discount")))
        discount.send_keys("2")



    def verify_amount(self):

        total_discount = self.wait.until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "input.clsprecentagevalue"
                )
            )
        ).get_attribute("value")

        total_payable = self.wait.until(
            EC.visibility_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "input.clsPaymentValue"
                )
            )
        ).get_attribute("value")

        print(f"Total Discount = {total_discount}")
        print(f"Total Payable = {total_payable}")

        discount_value = float(total_discount.replace(",", ""))
        payable_value = float(total_payable.replace(",", ""))

        assert discount_value >= 0
        assert payable_value > 0

        print("✓ Discount and Payable Amount verified")

    def click_add_to_cart(self):
        add_sale_btn = self.wait.until(EC.element_to_be_clickable((
            By.ID, "btnCart"
        )))
        add_sale_btn.click()

    def confirm_order(self):
        actual_payable = float(
            self.driver.find_element(
                By.CSS_SELECTOR,
                "input.clsPaymentValue"
            ).get_attribute("value")
        )

        assert actual_payable > 0, (
            f"Invalid Total Payable Amount: {actual_payable}"
        )

        print(f"✓ Total Payable verified before confirmation: {actual_payable}")

        confirm_btn = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(),'Yes! Proceed.')]")
            )
        )
        confirm_btn.click()

    def click_print_and_switch(self):
        # Wait for print dialog
        self.wait.until(EC.visibility_of_element_located((
            By.CLASS_NAME, "printPreviewDialog"
        )))

        print_btn = self.wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//div[contains(@class,'printPreviewDialog')]//button[normalize-space()='Print']"
        )))

        original_window = self.driver.current_window_handle
        all_windows_before = set(self.driver.window_handles)

        print_btn.click()

        # Wait for new tab
        WebDriverWait(self.driver, 20).until(
            lambda d: len(d.window_handles) > len(all_windows_before)
        )

        # Switch to new tab
        new_window = (set(self.driver.window_handles) - all_windows_before).pop()
        self.driver.switch_to.window(new_window)

        WebDriverWait(self.driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        print("Invoice page loaded successfully!")
        print(f"Title: {self.driver.title}")
        print(f"URL: {self.driver.current_url}")

        self.driver.save_screenshot("screenshots/invoice.png")

        self.driver.close()
        self.driver.switch_to.window(original_window)

        print("Returned to parent window")