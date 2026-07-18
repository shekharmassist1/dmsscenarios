from utilities.excel_reader import get_login_data

def test_read_excel():
    data = get_login_data()
    print(data)

    assert len(data) > 0