import pytest
import time
from pages.login_page import LoginPage
from pages.homepage import HomePage
from utilities.helpers import take_screenshot
from config.config import USERNAME, PASSWORD

def test_login_and_verify(driver):
    login = LoginPage(driver)
    login.login(USERNAME, PASSWORD)
    time.sleep(5)

    user_txt = login.verify_user()
    print(f"User verified: {user_txt}")
    take_screenshot(driver, "User_Verified")

    login.verify_logo()
    print("Logo verified")
    take_screenshot(driver, "Logo_Verified")

def test_menu_navigation(driver):
    home = HomePage(driver)
    home.click_all_menus(
        lambda step: take_screenshot(driver, step)
    )