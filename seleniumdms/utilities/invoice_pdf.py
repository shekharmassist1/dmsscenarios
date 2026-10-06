import io
import re

import pdfplumber
import requests


def fetch_invoice_text(driver, url):
    cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
    resp = requests.get(url, cookies=cookies, verify=False, timeout=30)
    with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def extract_payable_amount(text):
    match = re.search(r"Payable\s+([\d,.]+)\s+Amount", text)
    return match.group(1).replace(",", "") if match else None


def extract_line_item_count(text):
    row_numbers = re.findall(r"(?m)^(\d+)\s+[A-Z]{2,}", text)
    return max((int(n) for n in row_numbers), default=0)


def extract_items_and_pricing_table(text):
    start_match = re.search(r"S\s+Item Code", text)
    start = start_match.start() if start_match else 0
    end_match = re.search(r"Payable\s+[\d,.]+\s+Amount", text)
    end = end_match.end() if end_match else len(text)
    return text[start:end].strip()
