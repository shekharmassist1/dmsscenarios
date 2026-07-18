import pytest
import allure

from pages.login_page import LoginPage
from utilities.excel_reader import get_login_data


@allure.feature("Login")
@allure.story("Login Validation using Excel Data")
@pytest.mark.parametrize(
    "username,password,expected",
    get_login_data()
)
def test_login(driver, username, password, expected):

    login_page = LoginPage(driver)

    with allure.step(f"Login with Username={username}, Expected={expected}"):

        login_page.login(username, password)

        try:
            login_page.verify_user()
            actual_result = "Pass"

        except Exception:
            actual_result = "Fail"

        assert actual_result == expected, (
            f"Expected={expected}, Actual={actual_result}"
        )