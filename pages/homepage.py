
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config.config import EXPLICIT_WAIT
import time
from selenium.webdriver.support.ui import Select

from utilities.db_utils import DatabaseUtils


class HomePage:

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, EXPLICIT_WAIT)

    def get_menus(self):
        """
        Returns all sidebar menu links
        """

        return self.driver.find_elements(
            By.CSS_SELECTOR,
            "#menuVerticle a.nav-link"
        )

    def click_all_menus(self, screenshot_fn=None):

        menus = self.get_menus()

        menu_data = []

        # Store menu names and URLs first
        for menu in menus:
            menu_name = menu.text.strip()

            if not menu_name:
                continue

            menu_url = menu.get_attribute("href")

            menu_data.append({
                "name": menu_name,
                "url": menu_url
            })

        print(f"Total menus found: {len(menu_data)}")

        for menu in menu_data:

            try:
                menu_name = menu["name"]
                menu_url = menu["url"]

                safe_name = (
                    menu_name.replace("/", "_")
                    .replace("\\", "_")
                    .replace(":", "_")
                    .replace("*", "_")
                    .replace("?", "_")
                    .replace('"', "_")
                    .replace("<", "_")
                    .replace(">", "_")
                    .replace("|", "_")
                    .replace("\n", "_")
                )

                print(f"\nOpening menu: {menu_name}")
                print(f"URL: {menu_url}")

                if screenshot_fn:
                    screenshot_fn(f"Before_Click_{safe_name}")

                # Navigate directly
                self.driver.get(menu_url)

                self.wait.until(
                    lambda d: d.execute_script("return document.readyState")
                              == "complete"
                )

                time.sleep(2)

                if screenshot_fn:
                    screenshot_fn(f"After_Click_{safe_name}")

                print("Current URL:", self.driver.current_url)

                # Return to dashboard
                self.driver.get(
                    "https://admin.massistcrm.com/DMSPages/Dashboard.html"
                )

                self.wait.until(
                    EC.presence_of_element_located(
                        (By.ID, "menuVerticle")
                    )
                )

            except Exception as e:

                print(f"Failed menu '{menu_name}': {e}")

                if screenshot_fn:
                    screenshot_fn(f"FAILED_{safe_name}")

    def click_date_filter(self, option):

        option_element = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, f"//span[normalize-space()='{option}']")
            )
        )
        option_element.click()

        print(f"Selected Filter: {option}")

        time.sleep(2)

        self.wait.until(
            EC.invisibility_of_element_located(
                (By.ID, "feedLoading")
            )
        )

        calendar_icon = self.wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//i[contains(@class,'mIconCalendar')]"
                )
            )
        )

        calendar_icon.click()

    def get_pending_order_flag(self, company_id):

        query = f"""
        SELECT IsVisible
        FROM AdminSetting WITH(NOLOCK)
        WHERE Menu = 'DMSPendingOrder'
        AND Company_Id = {company_id}
        """

        db = DatabaseUtils()

        columns, rows = db.fetch_all(query)

        print("DB Result:", rows)

        if not rows:
            raise Exception(
                f"No AdminSetting found for Company_Id={company_id}"
            )

        result = dict(zip(columns, rows[0]))

        print("Pending Order Flag:", result["IsVisible"])

        return result["IsVisible"]

    def is_pending_order_menu_visible(self):

        try:
            element = self.driver.find_element(
                By.ID,
                "count_pending_order"
            )

            return element.is_displayed()

        except Exception as e:
            print(f"Pending Order menu not found: {e}")
            return False

    def click_pending_order(self):
        self.wait.until(
            EC.element_to_be_clickable(
                (By.ID, "count_pending_order")
            )
        ).click()


    def get_my_order_flag(self, company_id):

        query = f"""
        SELECT IsVisible
        FROM AdminSetting WITH(NOLOCK)
        WHERE Menu = 'DMSOrderDetails'
        AND Company_Id = {company_id}
        """

        db = DatabaseUtils()

        columns, rows = db.fetch_all(query)

        print("DB Result:", rows)

        if not rows:
            raise Exception(
                f"No AdminSetting found for Company_Id={company_id}"
            )

        result = dict(zip(columns, rows[0]))

        print("Order Details Flag:", result["IsVisible"])

        return result["IsVisible"]

    def is_my_order_menu_visible(self):

        try:
            element = self.driver.find_element(
                By.ID,
                "count_order"
            )

            return element.is_displayed()

        except Exception as e:
            print(f"My Order menu not found: {e}")
            return False

    def click_my_order(self):
        self.wait.until(
            EC.element_to_be_clickable(
                (By.ID, "count_order")
            )
        ).click()


    def get_return_details_flag(self, company_id):

        query = f"""
        SELECT IsVisible
        FROM AdminSetting WITH(NOLOCK)
        WHERE Menu = 'DMSReturnDetails'
        AND Company_Id = {company_id}
        """

        db = DatabaseUtils()

        columns, rows = db.fetch_all(query)

        print("DB Result:", rows)

        if not rows:
            raise Exception(
                f"No AdminSetting found for Company_Id={company_id}"
            )

        result = dict(zip(columns, rows[0]))

        print("Return Details Flag:", result["IsVisible"])

        return result["IsVisible"]

    def is_return_details_menu_visible(self):

        try:
            element = self.driver.find_element(
                By.ID,
                "count_return"
            )

            return element.is_displayed()

        except Exception as e:
            print(f"Return Details menu not found: {e}")
            return False

    def click_return_details(self):
        self.wait.until(
            EC.element_to_be_clickable(
                (By.ID, "count_return")
            )
        ).click()

    def get_purchase_report_flag(self, company_id):

        query = f"""
        SELECT IsVisible
        FROM AdminSetting WITH(NOLOCK)
        WHERE Menu = 'DMSPurchaseReport'
        AND Company_Id = {company_id}
        """

        db = DatabaseUtils()

        columns, rows = db.fetch_all(query)

        print("DB Result:", rows)

        if not rows:
            raise Exception(
                f"No AdminSetting found for Company_Id={company_id}"
            )

        result = dict(zip(columns, rows[0]))

        print("Purchase Report Flag:", result["IsVisible"])

        return result["IsVisible"]

    def is_purchase_menu_visible(self):

        try:
            element = self.driver.find_element(
                By.ID,
                "count_purchase"
            )

            return element.is_displayed()

        except Exception as e:
            print(f"Purchase menu not found: {e}")
            return False
    def click_purchase(self):
        self.wait.until(
            EC.element_to_be_clickable(
                  (By.ID, "count_purchase")
            )
        ).click()


    def get_total_sale_flag(self, company_id):

        query = f"""
        SELECT IsVisible
        FROM AdminSetting WITH(NOLOCK)
        WHERE Menu = 'DMSSaleDetails'
        AND Company_Id = {company_id}
        """

        db = DatabaseUtils()

        columns, rows = db.fetch_all(query)

        print("DB Result:", rows)

        if not rows:
            raise Exception(
                f"No AdminSetting found for Company_Id={company_id}"
            )

        result = dict(zip(columns, rows[0]))

        print("Total Sale Flag:", result["IsVisible"])

        return result["IsVisible"]

    def is_total_sale_visible(self):

        try:
            element = self.driver.find_element(
                By.ID,
                "count_sale"
            )

            return element.is_displayed()

        except Exception as e:
            print(f"Total Sale menu not found: {e}")
            return False

    def click_total_sale(self):
        self.wait.until(
            EC.element_to_be_clickable(
                (By.ID, "count_sale")
            )
        ).click()

    def click_client(self):
        client_name=self.wait.until(
            EC.element_to_be_clickable((By.ID,"clientid")
        ))

        name = client_name.text.strip()

        print("Client Name:", name)

        client_name.click()
        return name

    def click_autorenew(self):
        autorenew=self.wait.until(
            EC.element_to_be_clickable((By.XPATH,"//i[@class='material-icons allOpen']")
        ))
        autorenew.click()
        time.sleep(3)

    def click_Keyboard_arrow(self):
        keybrd_arrow=self.wait.until(
            EC.element_to_be_clickable((By.XPATH,"//i[normalize-space()='keyboard_arrow_right']")
        ))
        keybrd_arrow.click()
        time.sleep(3)

    def verify_show_dropdown(self):
        quarter = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[@name='Q']")))
        quarter.click()
        time.sleep(3)


        dropdown_element = self.wait.until(
            EC.presence_of_element_located((By.NAME, "tbl_order_grid_length"))
        )

        select = Select(dropdown_element)
        options = select.options
        print(f"Found {len(options)} options")

        for i in range(len(options)):
            dropdown_element = self.wait.until(
                EC.presence_of_element_located((By.NAME, "tbl_order_grid_length"))
            )
            select = Select(dropdown_element)

            option_value = select.options[i].get_attribute("value")
            option_text = select.options[i].text

            print(f"Selecting: {option_text} (value={option_value})")
            select.select_by_index(i)

            time.sleep(1.5)
            print(f"  → Selected successfully")

        print("All options clicked.")

    def verify_pagination(self):
        # Step 1: Click Quarter and verify it's active
        quarter = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[@name='Q']")))
        quarter.click()
        time.sleep(3)

        # Step 2: Confirm Quarter tab is selected before touching the dropdown
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[@name='Q' and contains(@class,'active')]")))
        print("Quarter filter is active")

        info = self.wait.until(
            EC.presence_of_element_located((By.ID, "tbl_order_grid_info"))
        )
        print(f"Table info: {info.text}")
        assert "entries" in info.text, "Entries info text not found"

        # Step 2: Verify Previous button is DISABLED on page 1
        prev_btn = self.driver.find_element(By.ID, "tbl_order_grid_previous")
        assert "disabled" in prev_btn.get_attribute("class"), "Previous should be disabled on page 1"
        print("Previous button is disabled on page 1 ✓")

        # Step 3: Verify page 1 is active (has 'current' class)
        current_page = self.driver.find_element(By.CSS_SELECTOR, "a.paginate_button.current")
        assert current_page.text == "1", f"Expected page 1 to be active, got {current_page.text}"
        print(f"Page 1 is active ✓")

        # Step 4: Click every page that actually exists (2..last) and verify each becomes active.
        # The page count depends on how many orders exist in the quarter (e.g. 71 entries / 25 per
        # page = 3 pages), so it must not be hardcoded -- clicking a non-existent page '4' timed out.
        page_links = self.driver.find_elements(
            By.CSS_SELECTOR, "#tbl_order_grid_paginate a.paginate_button:not(.previous):not(.next)"
        )
        page_numbers = sorted({int(a.text) for a in page_links if a.text.strip().isdigit()})
        last_page = max(page_numbers) if page_numbers else 1
        print(f"Total pages: {last_page}")

        for page_num in [str(n) for n in range(2, last_page + 1)]:
            page_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//div[@id='tbl_order_grid_paginate']//a[contains(@class,'paginate_button') and normalize-space()='{page_num}']")
                )
            )
            page_btn.click()
            time.sleep(1.5)

            # Verify clicked page becomes current
            current = self.driver.find_element(By.CSS_SELECTOR, "#tbl_order_grid_paginate a.paginate_button.current")
            assert current.text == page_num, f"Expected page {page_num} to be active, got {current.text}"
            print(f"Page {page_num} is active ✓")

            # Verify Previous is now ENABLED
            prev_btn = self.driver.find_element(By.ID, "tbl_order_grid_previous")
            assert "disabled" not in prev_btn.get_attribute("class"), f"Previous should be enabled on page {page_num}"
            print(f"Previous button is enabled on page {page_num} ✓")

            # Verify entries info updated
            info = self.driver.find_element(By.ID, "tbl_order_grid_info")
            print(f"  → {info.text}")

        # Step 5: On the last page, Next must be disabled; otherwise click it and check we moved on.
        next_btn = self.driver.find_element(By.ID, "tbl_order_grid_next")
        current = self.driver.find_element(By.CSS_SELECTOR, "#tbl_order_grid_paginate a.paginate_button.current")
        if current.text == str(last_page):
            assert "disabled" in next_btn.get_attribute("class"), "Next should be disabled on the last page"
            print(f"Next button is disabled on the last page ({last_page}) ✓")
        else:
            before = current.text
            next_btn.click()
            time.sleep(1.5)
            current = self.driver.find_element(By.CSS_SELECTOR, "#tbl_order_grid_paginate a.paginate_button.current")
            assert current.text != before, "Clicking Next did not change the page"
            print(f"After Next click → Page {current.text} is active ✓")

        # Step 6: Go back to page 1 via Previous button repeatedly (or direct click)
        page1_btn = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[@id='tbl_order_grid_paginate']//a[contains(@class,'paginate_button') and normalize-space()='1']")
            )
        )
        page1_btn.click()
        time.sleep(1.5)
        current = self.driver.find_element(By.CSS_SELECTOR, "#tbl_order_grid_paginate a.paginate_button.current")
        assert current.text == "1", "Should be back on page 1"
        print("Back to page 1 ✓")

        print("Pagination verification complete.")


