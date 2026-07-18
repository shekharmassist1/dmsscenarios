import pytest
import time
import allure

from pages.login_page import LoginPage
from pages.homepage import HomePage
from utilities.helpers import take_screenshot, navigate_dashboard
from config.config import USERNAME, PASSWORD


@allure.epic("DMS Application")
@allure.feature("Homepage")
@allure.story("Homepage")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Homepage Testing")
@allure.tag("smoke", "homepage")
@allure.link("https://admin.massistcrm.com", name="DMS Application")
def test_homepage(driver):

    login = LoginPage(driver)
    home = HomePage(driver)

    with allure.step("Login to DMS"):
        login.login(USERNAME, PASSWORD)
        time.sleep(5)
        take_screenshot(driver, "Login")

    with allure.step("Get Menus"):
        home.get_menus()
        take_screenshot(driver, "Get_Menu")

    with allure.step("Click All Menus"):
        home.click_all_menus(
            lambda name: take_screenshot(driver, name)
        )
        take_screenshot(driver, "Click_All_Menus")
        driver.get(
            "https://admin.massistcrm.com/DMSPages/Dashboard.html"
        )

        time.sleep(3)

    with allure.step("Verify Date Filters"):
        filters = [
            "Today",
            "Weekly",
            "Monthly",
            "Quarterly"
        ]

        for filter_name in filters:

            with allure.step(f"Select Filter: {filter_name}"):

                home.click_date_filter(filter_name)

                take_screenshot(
                    driver,
                    f"DateFilter_{filter_name.replace(' ', '_')}"
                )

                time.sleep(2)

    with allure.step("Validate Pending Order configuration"):
        company_id = 536

        db_flag = home.get_pending_order_flag(company_id)

        allure.attach(
            f"""
    Company ID : {company_id}
    Menu       : DMSPendingOrder
    IsVisible  : {db_flag}
    Status     : {'Enabled' if db_flag == 1 else 'Disabled'}
    """,
            name="Pending Order DB Validation",
            attachment_type=allure.attachment_type.TEXT
        )

        assert db_flag == 1, \
            f"Pending Order disabled in DB. IsVisible={db_flag}"

    with allure.step("Pending order menu visible"):
        assert home.is_pending_order_menu_visible(), \
            f"Pending Order menu not visible though DB flag is enabled"
        take_screenshot(driver, "Pending_Order")

    with allure.step("Pending order clicked"):
        home.click_pending_order()
        take_screenshot(driver, "Pending_Order")
        navigate_dashboard(driver)

    with allure.step("Validate My Order configuration"):
        company_id = 536

        db_flag = home.get_my_order_flag(company_id)

        allure.attach(
            f"""
    Company ID : {company_id}
    Menu       : DMSOrderDetails
    IsVisible  : {db_flag}
    Status     : {'Enabled' if db_flag == 1 else 'Disabled'}
    """,
            name="My Order DB Validation",
            attachment_type=allure.attachment_type.TEXT
        )

        assert db_flag == 1, \
            f"My Order disabled in DB. IsVisible={db_flag}"

    with allure.step("My order menu visible"):

        assert home.is_my_order_menu_visible(), \
            f"My Order menu not visible though DB flag is enabled"
        take_screenshot(driver, "My_Order")

    with allure.step("My Order clicked"):
        home.click_my_order()
        take_screenshot(driver, "My_Order")
        navigate_dashboard(driver)

        with allure.step("Validate Return Details configuration"):
            company_id = 536

            db_flag = home.get_return_details_flag(company_id)

            allure.attach(
                f"""
        Company ID : {company_id}
        Menu       : DMSReturnDetails
        IsVisible  : {db_flag}
        Status     : {'Enabled' if db_flag == 1 else 'Disabled'}
        """,
                name="Return Details DB Validation",
                attachment_type=allure.attachment_type.TEXT
            )

            assert db_flag == 1, \
                f"Return Details disabled in DB. IsVisible={db_flag}"

    with allure.step("Return Details menu visible"):

            assert home.is_return_details_menu_visible(), \
                f"Return Details menu not visible though DB flag is enabled"
            take_screenshot(driver, "Return Details")

    with allure.step("Return details click"):
            home.click_return_details()
            take_screenshot(driver, "Return Details")
            navigate_dashboard(driver)


    with allure.step("Validate Purchase configuration"):
            company_id = 536

            db_flag = home.get_purchase_report_flag(company_id)

            allure.attach(
                f"""
        Company ID : {company_id}
        Menu       : DMSPurchaseReport
        IsVisible  : {db_flag}
        Status     : {'Enabled' if db_flag == 1 else 'Disabled'}
        """,
                name="Purchase DB Validation",
                attachment_type=allure.attachment_type.TEXT
            )

            assert db_flag == 1, \
                f"Purchase disabled in DB. IsVisible={db_flag}"

    with allure.step("Purchase menu visible"):

            assert home.is_purchase_menu_visible(), \
                f"Purchase menu not visible though DB flag is enabled"
            take_screenshot(driver, "Purchase Details")

    with allure.step("Validate Purchase menu clicked"):
            home.click_purchase()
            take_screenshot(driver, "Purchase clicked")
            navigate_dashboard(driver)

    with allure.step("Total Sale configuration"):
            company_id = 536

            db_flag = home.get_total_sale_flag(company_id)

            allure.attach(
                f"""
        Company ID : {company_id}
        Menu       : DMSSaleDetails
        IsVisible  : {db_flag}
        Status     : {'Enabled' if db_flag == 1 else 'Disabled'}
        """,
                name="Total Sale DB Validation",
                attachment_type=allure.attachment_type.TEXT
            )

            assert db_flag == 1, \
                f"Total Sale disabled in DB. IsVisible={db_flag}"

    with allure.step("Sale Details"):

            assert home.is_purchase_menu_visible(), \
                f"Total Sale menu not visible though DB flag is enabled"
            take_screenshot(driver, "Total Sale Details")

    with allure.step("Total Sale clicked"):
        home.click_total_sale()
        take_screenshot(driver, "Total Sale details clicked")
        navigate_dashboard(driver)

    with allure.step("click client"):
        client_name = home.click_client()
        allure.attach(
            client_name or "Client name not found",  # fallback if None
            name="Client Name",
            attachment_type=allure.attachment_type.TEXT
        )
        take_screenshot(driver, "Client name clicked")

    with allure.step("Auto Renew"):
        home.click_autorenew()
        take_screenshot(driver, "Auto Renew")
        time.sleep(2)

    with allure.step("keyboard Arrow"):
        home.click_Keyboard_arrow()
        take_screenshot(driver, "Keyboard Arrow")

    with allure.step("show Dropdown"):
        home.verify_show_dropdown()
        take_screenshot(driver, "Show Dropdown")

    with allure.step("Verify Pagination"):
        home.verify_pagination()
        take_screenshot(driver, "Verify Pagination")













