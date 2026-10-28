import os

# Site under test. Set DMS_BASE_URL (e.g. https://stage.massistcrm.com) to switch; default admin.
BASE_URL = os.environ.get("DMS_BASE_URL", "https://admin.massistcrm.com").rstrip("/")
USERNAME = "vadilaldms"
PASSWORD = "vadilal"
