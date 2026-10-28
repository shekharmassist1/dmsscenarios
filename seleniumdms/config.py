import os

# Site under test. Set DMS_BASE_URL (e.g. https://stage.massistcrm.com) to switch; default admin.
BASE_URL = os.environ.get("DMS_BASE_URL", "https://admin.massistcrm.com").rstrip("/")
USERNAME = "vadilaldms"
PASSWORD = "vadilal"

# Customers used by the test groups (each parallel worker uses its own customer). Override per site:
# admin uses Demo Dealer 2/3/4; on stage set DMS_CUSTOMER_2/3/4 to customers that exist there.
CUSTOMER_2 = os.environ.get("DMS_CUSTOMER_2", "Demo Dealer 2")   # Sale Return scenarios
CUSTOMER_3 = os.environ.get("DMS_CUSTOMER_3", "Demo Dealer 3")   # Bill / batch / lifecycle / unit tests
CUSTOMER_4 = os.environ.get("DMS_CUSTOMER_4", "Demo Dealer 4")   # Inventory scenarios
COMPANY_NAME = os.environ.get("DMS_COMPANY_NAME", "Demo Distributor 1")  # name on the invoice header
