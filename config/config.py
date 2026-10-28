import os

# Site under test. Set DMS_BASE_URL (e.g. https://stage.massistcrm.com) to switch; default admin.
SITE_URL = os.environ.get("DMS_BASE_URL", "https://admin.massistcrm.com").rstrip("/")
BASE_URL = SITE_URL + "/"
USERNAME = "vadilaldms"
PASSWORD = "vadilal"
IMPLICIT_WAIT = 60
EXPLICIT_WAIT = 60
SCREENSHOT_FOLDER = "screenshots"

REPORT_URL = (
    SITE_URL + "/ExternalReport/DMSOrderSale.html"
    "?tokenkey=YOUR_TOKEN_HERE"
)

DB_SERVER = os.environ.get("DB_SERVER", "172.31.62.165")
DB_NAME = os.environ.get("DB_NAME", "MA_Live")
DB_USER = os.environ.get("DB_USER", "view")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "G7#vQ9!xL2@rT5$zC")
# Customer for the massist1 Bill tests (admin: Demo Dealer 4; set DMS_CUSTOMER_4 on stage).
CUSTOMER_4 = os.environ.get("DMS_CUSTOMER_4", "Demo Dealer 4")
