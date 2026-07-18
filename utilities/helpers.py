import os
import allure
from datetime import datetime
import time

def take_screenshot(driver, step_name, folder="screenshots"):
    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{folder}/{step_name}_{timestamp}.png"
    driver.save_screenshot(file_name)

    # Attach to Allure report
    with open(file_name, "rb") as f:
        allure.attach(
            f.read(),
            name=step_name,
            attachment_type=allure.attachment_type.PNG
        )
    print(f"Screenshot saved: {file_name}")
    return file_name
def navigate_dashboard(driver):
    driver.get(
        "https://admin.massistcrm.com/DMSPages/Dashboard.html"
    )
    time.sleep(3)



