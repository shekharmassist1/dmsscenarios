"""Products with a CONFIRMED app bug that would make unrelated tests fail.

Tests that pick items for a sale, draft, edit or return skip these, so each test checks its own flow.
The batch-presence test (tests/test_bill_batch_presence.py) does NOT skip them: it keeps reporting
the bug until it is fixed. When the developers fix a product, delete it from this list.
"""
import re

KNOWN_PROBLEM_PRODUCTS = {
    # Pcs. Inv. 39,939 but NO batch: counted in Total Item but left out of Qty/Amount, and dropped
    # when the sale is saved (confirmed manually: Demo Dealer 3, qty 1 + Classic Malai qty 1 ->
    # Total Item 2 but Amount 184.71 / Final 193.95 = Classic Malai only).
    "Strawberry Sundae Spin Cup [1*8] 120Ml": "No batch for in-stock product; dropped from totals and from the saved sale",
}


def _norm(name):
    return re.sub(r"\s+", " ", (name or "")).strip().lower()


_KNOWN = {_norm(n) for n in KNOWN_PROBLEM_PRODUCTS}


def is_known_problem(product_name):
    """True if this product is on the known-problem list (case/space-insensitive; a grid name that
    carries extra text after the product name also matches)."""
    n = _norm(product_name)
    return any(n == k or n.startswith(k) for k in _KNOWN)
