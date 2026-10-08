import allure

from pages.bill_unit_apply_page import BillUnitApplyPage
from utilities.allure_utils import step

CUSTOMER_NAME = "Demo Dealer 4"
QTY = 1


@allure.epic("Bill / New Invoice")
@allure.feature("Unit type and batch popup")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Bill/New Invoice: hamburger Apply is DISABLED for unit Carton and ENABLED for unit Piece (item with >1 piece per carton)")
def test_bill_hamburger_apply_disabled_for_carton_enabled_for_piece(logged_in_driver, soft_assert):
    page = BillUnitApplyPage(logged_in_driver)

    with step(page, f"Open Bill/New Invoice and select '{CUSTOMER_NAME}'"):
        page.open()
        page.select_customer(CUSTOMER_NAME)

    with step(page, "Find an in-stock item with more than 1 piece in a carton"):
        row, info = page.find_row_with_multi_piece_carton()
        allure.attach(
            f"row={row}\nproduct={info['display_name']}\nitem code={info['item_code']}\n"
            f"pieces per carton={info['pieces_per_carton']}\nstock={info['available_stock']}\n"
            f"unit options={page.unit_options(row)}",
            name="item_used", attachment_type=allure.attachment_type.TEXT,
        )

    # ---- Carton: Apply must be disabled
    with step(page, "Set unit type to Carton and enter qty 1"):
        carton_label = page.set_unit(row, "carton")
        page.enter_quantity(row, QTY)
        soft_assert.check_true(
            (page.current_unit(row) or "").lower().startswith("cart"),
            f"Unit should be Carton, shows {page.current_unit(row)!r}",
        )

    with step(page, "Click the hamburger: Apply should be DISABLED for Carton"):
        box = page.open_hamburger(row)
        state = page.apply_button_state(box)
        allure.attach(f"unit={carton_label}\n{state['details']}\n\nPopup:\n{box.text}",
                      name="apply_state_carton", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_true(
            not state["enabled"],
            f"ISSUE: with unit type '{carton_label}' the hamburger Apply button is ENABLED -- it should be "
            f"disabled ({info['display_name']}; {state['details']})",
        )
        page.close_popup_without_applying(box)

    # ---- Piece: Apply must be enabled
    with step(page, "Set unit type to Piece and enter qty 1"):
        piece_label = page.set_unit(row, "piece")
        page.enter_quantity(row, QTY)
        soft_assert.check_true(
            not (page.current_unit(row) or "").lower().startswith("cart"),
            f"Unit should be Piece, shows {page.current_unit(row)!r}",
        )

    with step(page, "Click the hamburger: Apply should be ENABLED for Piece"):
        box = page.open_hamburger(row)
        state = page.apply_button_state(box)
        allure.attach(f"unit={piece_label}\n{state['details']}\n\nPopup:\n{box.text}",
                      name="apply_state_piece", attachment_type=allure.attachment_type.TEXT)
        soft_assert.check_true(
            state["enabled"],
            f"ISSUE: with unit type '{piece_label}' the hamburger Apply button is "
            f"{'missing' if not state['found'] else 'DISABLED'} -- it should be enabled "
            f"({info['display_name']}; {state['details']})",
        )
        page.close_popup_without_applying(box)
