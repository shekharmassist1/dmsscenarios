from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config.config import EXPLICIT_WAIT
import time
import os


class ReportsPage:

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, EXPLICIT_WAIT)

        os.makedirs("screenshots", exist_ok=True)

    def navigate_to_reports(self):

        main_window = self.driver.current_window_handle
        windows_before = self.driver.window_handles.copy()

        reports = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//span[normalize-space()='Reports']")
            )
        )

        reports.click()

        try:
            WebDriverWait(self.driver, 10).until(
                lambda d: len(d.window_handles) > len(windows_before)
            )

            new_window = [
                w for w in self.driver.window_handles
                if w not in windows_before
            ][0]

            self.driver.switch_to.window(new_window)

            print("✅ Switched to Reports Window")

        except:
            print("✅ Reports opened in same window")

        time.sleep(3)

    def click_date_filter(self, option):

        calendar = self.wait.until(
            EC.element_to_be_clickable(
                (By.ID, "divdaterange")
            )
        )

        calendar.click()

        option_element = self.wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    f"//li[normalize-space()='{option}'] | //*[@class='ranges']//span[normalize-space()='{option}']"
                )
            )
        )

        option_element.click()

        print(f"✅ Selected Date Filter: {option}")

        time.sleep(2)

    def click_report_and_capture(self, report_name, xpath):

        main_window = self.driver.current_window_handle
        windows_before = self.driver.window_handles.copy()

        report = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )

        self.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});",
            report
        )

        self.driver.execute_script(
            "arguments[0].click();",
            report
        )

        time.sleep(3)

        try:

            WebDriverWait(self.driver, 10).until(
                lambda d: len(d.window_handles) > len(windows_before)
            )

            new_window = [
                w for w in self.driver.window_handles
                if w not in windows_before
            ][0]

            self.driver.switch_to.window(new_window)

            print(f"✅ Opened Report: {report_name}")
            print("URL:", self.driver.current_url)

            time.sleep(2)

            self.driver.save_screenshot(
                f"screenshots/{report_name.replace(' ', '_')}.png"
            )

            self.driver.close()

            self.driver.switch_to.window(main_window)

            print(f"✅ Closed Report: {report_name}")

        except:

            print(f"✅ Opened in same tab: {report_name}")

            self.driver.save_screenshot(
                f"screenshots/{report_name.replace(' ', '_')}.png"
            )

            self.driver.back()

            time.sleep(2)