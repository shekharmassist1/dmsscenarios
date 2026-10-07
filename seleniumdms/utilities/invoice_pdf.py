import io
import re

import pdfplumber
import requests

# A money value as it appears on the invoice: optional currency mark, digits with optional
# thousands commas, optional decimals (e.g. "Rs. 1,23,456.78", "₹ 14,746.21", "24794.00").
_MONEY = r"(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d+)?)"


def fetch_invoice_text(driver, url):
    """Download the invoice using the browser's session cookies and return its text.

    Normally the URL returns a PDF. If the server returns an HTML page instead (e.g. a report
    viewer or an error page), fall back to the page's visible text rather than crashing in
    pdfplumber -- the caller then sees what the server actually sent."""
    cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
    resp = requests.get(url, cookies=cookies, verify=False, timeout=30)
    content = resp.content or b""
    if content.lstrip().startswith(b"%PDF"):
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    html = content.decode(resp.encoding or "utf-8", errors="replace")
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", "\n", html)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def extract_payable_amount(text):
    """Return the invoice's payable total as a plain number string (no commas), or None.

    pdfplumber flattens the PDF's columns, so the label and the value can come out in different
    orders depending on the invoice layout. The old single pattern ('Payable <amount> Amount')
    missed the common 'Payable Amount : <amount>' layout, so several shapes are tried, most
    specific first."""
    if not text:
        return None
    patterns = [
        r"Payable\s+" + _MONEY + r"\s+Amount",                         # column-split: Payable 123 Amount
        r"(?:Total\s+|Net\s+)?Payable\s+Amount\s*[:\-]?\s*" + _MONEY,   # Payable Amount : 123
        r"Amount\s+Payable\s*[:\-]?\s*" + _MONEY,                        # Amount Payable : 123
        r"(?:Net|Total)\s+Payable\s*[:\-]?\s*" + _MONEY,                 # Net Payable 123
        r"Grand\s+Total\s*[:\-]?\s*" + _MONEY,                           # Grand Total 123
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(1).replace(",", "")
            if re.search(r"\d", value):
                return value
    return None


def extract_line_item_count(text):
    """Highest row number at the start of an item line ('1 FGDPD5B01 ...', '2 Aam Chaska ...').
    Item codes can be mixed letters and digits, so accept any code starting with a letter."""
    row_numbers = re.findall(r"(?m)^\s*(\d{1,3})\s+[A-Za-z][A-Za-z0-9]", text or "")
    return max((int(n) for n in row_numbers), default=0)


def extract_items_and_pricing_table(text):
    """The item/pricing section of the invoice (for the report attachment). If the expected
    markers aren't found, the whole text is returned so the attachment still shows what was read."""
    text = text or ""
    start_match = re.search(r"S\s+Item Code", text) or re.search(r"Item\s+Code", text, flags=re.IGNORECASE)
    start = start_match.start() if start_match else 0
    end_match = (
        re.search(r"Payable\s+[\d,.]+\s+Amount", text)
        or re.search(r"Payable\s+Amount\s*[:\-]?\s*" + _MONEY, text, flags=re.IGNORECASE)
    )
    end = end_match.end() if end_match else len(text)
    return text[start:end].strip()
