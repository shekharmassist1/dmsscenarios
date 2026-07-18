class BillValidations:

    errors = []

    @staticmethod
    def validate_selected_items(bill, test_data):

        expected_count = 0

        for row in test_data:
            ui_qty = bill.get_quantity(row["Row"])

            print(
                f"Row={row['Row']} "
                f"Excel={row['Qty']} "
                f"UI={ui_qty}"
            )

            if ui_qty > 0:
                expected_count += 1

        actual_count = bill.get_total_item()

        if actual_count != expected_count:
            BillValidations.errors.append(
                f"Selected Items Failed: Expected={expected_count}, Actual={actual_count}"
            )
        else:
            print(f"✓ Selected Items={actual_count}")



