import os
from contextlib import contextmanager

import pyodbc
from dotenv import load_dotenv

load_dotenv()


def _connection_string():
    return (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={os.environ['DB_SERVER']};"
        f"DATABASE={os.environ['DB_NAME']};"
        f"UID={os.environ['DB_USER']};"
        f"PWD={os.environ['DB_PASSWORD']};"
        f"TrustServerCertificate=yes;"
        f"Encrypt=yes;"
    )


@contextmanager
def get_connection(timeout=10):
    conn = pyodbc.connect(_connection_string(), timeout=timeout)
    try:
        yield conn
    finally:
        conn.close()


def _rows_to_dicts(cursor, rows):
    columns = [c[0] for c in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


def get_order_header(order_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM order_dtls WHERE Order_Id = ?", order_id)
        row = cursor.fetchone()
        if row is None:
            return None
        return _rows_to_dicts(cursor, [row])[0]


def get_order_products(order_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM order_products WHERE Order_Id = ?", order_id)
        return _rows_to_dicts(cursor, cursor.fetchall())


def get_latest_order_for_client(client_name, order_type="sale"):
    """Newest order of the given OrderType for a customer. order_dtls also holds 'Draft' and
    'PrintPreview' records (created by Save Draft / Print), so without the type filter the
    'latest order' was often a draft or a print preview rather than the sale just made."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT TOP 1 * FROM order_dtls WHERE Client_Name = ? AND IsDeleted = 0 "
            "AND LOWER(OrderType) = LOWER(?) ORDER BY Order_Id DESC",
            client_name, order_type,
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return _rows_to_dicts(cursor, [row])[0]


def get_latest_return_for_client(client_name):
    """A completed Sale Return (after Goods Receive + confirm) lands in the same order_dtls/
    order_products tables as sale orders, with OrderType = 'CreditNote' -- confirmed by matching
    a live test return's Order_Amt/Client_Name against the UI's 'Return Confirm!' dialog total.
    ('return' is a different, earlier OrderType seen on other distributors' data -- likely a
    pending/not-yet-received state -- and does not match records created by this flow.)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT TOP 1 * FROM order_dtls WHERE Client_Name = ? AND OrderType = 'CreditNote' "
            "AND IsDeleted = 0 ORDER BY Order_Id DESC",
            client_name,
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return _rows_to_dicts(cursor, [row])[0]


def get_return_products(order_id):
    return get_order_products(order_id)
