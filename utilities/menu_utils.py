import pytest
from selenium.webdriver.common.by import By


def verify_menu_or_skip(driver, menu_name):

    menus = driver.find_elements(
        By.XPATH,
        f"//span[contains(text(),'{menu_name}')]"
    )

    if not menus:
        pytest.skip(
            f"{menu_name} menu not available"
        )