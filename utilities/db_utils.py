import pyodbc
from config.config import DB_SERVER, DB_NAME, DB_USER, DB_PASSWORD


class DatabaseUtils:

    def __init__(self):
        self.conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={DB_SERVER};"
            f"DATABASE={DB_NAME};"
            f"UID={DB_USER};"
            f"PWD={DB_PASSWORD};"
            f"TrustServerCertificate=yes;"
            f"Encrypt=yes;"
        )
        self.connection = None

    def connect(self):
        self.connection = pyodbc.connect(self.conn_str)
        return self.connection.cursor()

    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def fetch_all(self, query: str):
        cursor = self.connect()
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        rows    = cursor.fetchall()
        self.disconnect()
        return columns, rows

    def fetch_one(self, query):

        columns, rows = self.fetch_all(query)

        if not rows:
            return None

        return dict(zip(columns, rows[0]))