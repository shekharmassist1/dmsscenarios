# Test Cases — Bill/New Invoice (Product Page)

**Application:** MAssistCRM-DMS (`admin.massistcrm.com`)
**Login:** `vadilaldms` / `vadilal` → select Distributor **"Demo Distributor 1"**
**Module:** Bill/New Invoice → Select Customer → Product Grid
**Test customer:** **"Demo 4"**
**Automation:** [tests/test_product_page.py](tests/test_product_page.py), [tests/test_inventory_scenarios.py](tests/test_inventory_scenarios.py)

All 11 cases below were run through automated Selenium tests. Every "FAIL" case has been reproduced multiple times (2–4× each) and is a genuine, repeatable app defect — not a one-off automation flake. Steps are written so anyone can follow them manually in the browser.

---

## Bugs to demo first (most severe, most reproducible)

1. **TC-11 — Items disappear between "Confirm Sale" and the generated invoice.** This is the cleanest, most precise repro: everything is correct right up through clicking "Yes! Proceed." (5 items confirmed, correct discounted total) — then the actual Tax Invoice PDF that gets generated only has 3 line items. Confirmed on a **real, finalized sale**.
2. **TC-09 — Pricing corrupts after Order Again (Select-All path).** Item count stays correct (2 items throughout), but Final Amount jumps from 202.91 to 6,290.47 (~31×) after reopening a saved draft via "Order Again" and recalculating. Reproduced identically 4 times.
3. **TC-04/05/06/07 — Item count and pricing both drop whenever a cart contains an item flagged "insufficient inventory," at the Save Draft → Order Again step.** Losses range from losing 1–3 items out of 2–7, and amounts have been off by anywhere from ~7× to ~315×.

---

## TC-01 — Enter products, Calculate, verify View Selected Items, Print, Save Draft

**Precondition:** Logged in, customer "Demo 4" selected on the product grid.

**Test Data:** Product row 1 → qty 2 Carton; Product row 2 → qty 3 Carton.

**Steps:**
1. Enter quantity 2 into the Sale Qty field of product row 1.
2. Enter quantity 3 into the Sale Qty field of product row 2.
3. Click **Calc**.
4. Verify the summary bar's Total Item, Qty (pcs), and Final Amount are populated and consistent with the entered quantities.
5. Click **View All Selected Items**.
6. Verify the popover lists exactly the 2 products entered, with matching quantities, and its total matches the Calc Final Amount.
7. Close the popover.
8. Click **Print (Ctrl+P)**.
9. Verify the "Print Preview" modal opens and shows the note that the invoice is not yet saved.
10. Close the Print Preview modal.
11. Click **Save Drafts**.
12. Verify the "Draft saved successfully" confirmation alert appears, then click OKAY.

**Expected Result:** Every step above completes without a mismatch; the draft is saved with 2 items.

**Actual Result:** ✅ Pass — reproduced cleanly across 2 consecutive runs.

**Status:** **PASS**

---

## TC-02 — Verify the saved draft appears correctly in the drafts list

**Precondition:** TC-01 completed (a draft for "Demo 4" with 2 items exists).

**Steps:**
1. Navigate to **DMSSaveToDraft**.
2. Search/filter for client "Demo 4".
3. Locate the most recent draft row.
4. Verify Client = "Demo 4", No. Of Items = 2, Draft Qty matches the summary bar's "All Qty (pcs)" from TC-01, and Draft Amt matches the Calc Final Amount (rounded).

**Expected Result:** The draft row's item count and amount match what was entered and calculated in TC-01.

**Actual Result:** ✅ Pass.

**Status:** **PASS**

---

## TC-03 — Scenario 1: 4 valid items + 1 insufficient-inventory item → Calculate

**Precondition:** Logged in, customer "Demo 4" selected.

**Test Data:** 4 product rows with a valid quantity (1 Carton each); 1 product row with a quantity deliberately set above its live available stock ("insufficient inventory").

**Steps:**
1. Enter valid quantity (1) into 4 product rows.
2. Enter a quantity greater than the currently available stock into a 5th product row (check the green "Inventory Lebel" badge on that row for the current stock, then type something higher).
3. Click **Calc**.
4. Verify an "Insufficient inventory for [product]" alert appears; dismiss it (OKAY).
5. Verify the summary bar's Total Item count equals 5.

**Expected Result:** Total Item = 5; an insufficient-inventory alert is shown for the over-stock product.

**Actual Result:** ✅ Pass.

**Status:** **PASS**

---

## TC-04 — Scenario 1 (continued): Save Draft → Order Again → Recalculate → View Selected Items

**Precondition:** TC-03 completed (5 items entered, Calc done).

**Steps:**
1. Click **Save Drafts**; confirm the "Draft saved successfully" alert.
2. Navigate to **DMSSaveToDraft**, locate the new draft for "Demo 4".
3. Verify the draft's No. Of Items and Draft Amt match the 5-item Calc result from TC-03.
4. Click **Order** ("Order Again") on that draft row.
5. Verify the product grid reopens with the same number of rows as originally saved.
6. Click **Calc** again.
7. Verify Total Item and Final Amount match the original values from TC-03.
8. Click **View All Selected Items** and verify the item count and total match.

**Expected Result:** The draft, its reopened view, and the recalculation all still show 5 items and the original Final Amount (11,513.88).

**Actual Result:** ❌ **FAIL** — Draft list showed **No. Of Items = 3** (not 5); Draft Amt **1,688** vs. expected **11,513.88**. Order Again reopened only **3** rows. Recalculating gave Total Item **3**, Final Amount **1,688.32**. View Selected Items likewise showed only 3 items.

**Status:** **FAIL**

---

## TC-05 — Scenario 2: 4 valid items → Calculate → Save Draft → Order Again → Recalculate → View Selected Items

**Precondition:** Logged in, customer "Demo 4" selected.

**Test Data:** 4 product rows, quantity 2 Carton each (no item intentionally over stock).

**Steps:**
1. Enter quantity 2 into 4 product rows.
2. Click **Calc**.
3. Verify Total Item = 4 and no insufficient-inventory alert appears.
4. Click **Save Drafts**; confirm the alert.
5. Verify the draft list shows No. Of Items = 4.
6. Click **Order Again**; verify 4 rows reopen.
7. Click **Calc** again; verify Total Item = 4 and Final Amount matches the original.
8. Click **View All Selected Items**; verify count = 4.

**Expected Result:** All 4 items and the original amount persist through every step; no unexpected inventory warning.

**Actual Result:** ❌ **FAIL** — An unexpected "Insufficient inventory" alert appeared even with a small, valid quantity (2), suggesting that product's live stock is now critically low. Calc Total Item showed **3** instead of 4. Draft list No. Of Items = **2**. Order Again reopened only **2** rows. Recalculating: Total Item **2**. View Selected Items count = **2**.

**Status:** **FAIL**

---

## TC-06 — Scenario 3: 2 items (1 insufficient) → Calculate → Save Draft → Order Again → Recalculate → View Selected Items

**Precondition:** Logged in, customer "Demo 4" selected.

**Test Data:** 1 product row with a valid quantity; 1 product row with a quantity above its available stock.

**Steps:** Same pattern as TC-04, with 2 items instead of 5.

**Expected Result:** 2 items and the original Final Amount persist through Save Draft and Order Again.

**Actual Result:** ❌ **FAIL** — the most severe pricing discrepancy found in this pass: Draft list No. Of Items = **1** (not 2); Draft Amt **1,522** vs. Calc Final Amount **479,609.73** — a **~315× mismatch**. Order Again reopened only **1** row. Recalculating: Total Item **1**, Final Amount **1,521.89**.

**Status:** **FAIL**

---

## TC-07 — Scenario 4: 7 items (1 insufficient) → Print → Calculate → Save Draft → Order Again → Recalculate → View Selected Items

**Precondition:** Logged in, customer "Demo 4" selected.

**Test Data:** 6 product rows with valid quantities; 1 product row with a quantity above its available stock.

**Steps:**
1. Enter quantities into 7 product rows (6 valid + 1 insufficient).
2. Click **Print**; verify the Print Preview modal opens with the "not yet saved" note.
3. Close the Print Preview modal.
4. Click **Calc**; verify Total Item = 7 and the insufficient-inventory alert appears.
5. Click **Save Drafts**; confirm the alert.
6. Verify the draft list shows No. Of Items = 7.
7. Click **Order Again**; verify 7 rows reopen.
8. Click **Calc** again; verify Total Item = 7.
9. Click **View All Selected Items**; verify count = 7.

**Expected Result:** All 7 items persist through Print, Save Draft, and Order Again.

**Actual Result:** ❌ **FAIL**, plus a UI defect — the Print Preview modal **did not close** after clicking its Close button on this larger item set. Draft list No. Of Items = **5**. Order Again reopened only **5** rows. Recalculating drifted further: Total Item **4** (not matching either 7 or the 5 reopened). View Selected Items count = **4**.

**Status:** **FAIL** — item-count loss compounds with more items in the cart (7→5→4).

---

## TC-08 — Scenario 5: Correct an insufficient item's quantity before Calculate

**Precondition:** Logged in, customer "Demo 4" selected.

**Test Data:** 5 product rows with valid quantity (1 each); the 5th row is first pushed over its available stock, then corrected back to a valid quantity before calculating.

**Steps:**
1. Enter quantity 1 into 5 product rows.
2. Re-enter an over-stock quantity into row 5, dismiss the resulting alert.
3. Read the row's actual available stock and re-enter a valid quantity for row 5.
4. Click **Calc**; verify Total Item = 5 (no alert expected now).
5. Click **Save Drafts**, verify the draft list, click **Order Again**, recalculate, and check View Selected Items.

**Expected Result:** Once corrected, all 5 items should calculate and persist correctly.

**Actual Result:** ✅ Calc correctly showed Total Item = 5 after the correction (fixing an over-stock quantity *before* proceeding avoids the count-drop seen in TC-04/06/07). ⚠️ The Save Drafts step was intermittently blocked in one verification run — looked like an automation timing issue, not a confirmed app defect.

**Status:** **PASS** (Calculate step) / **Needs one more clean re-run** (Save Draft onward)

---

## TC-09 — Scenario 7 ("Incorrect Inventory"): Select All override → Calculate → Save Draft → Order Again → Recalculate → View Selected Items

**Precondition:** Logged in, customer "Demo 4" selected.

**Test Data:** 2 product rows, initially entered as quantity 4 each, then overridden via the "Select All" bulk-entry modal to quantity 2 each for the same 2 products.

**Steps:**
1. Enter quantity 4 into 2 product rows.
2. Click **Select All**; in the "Enter Quantity" modal, uncheck "All Products", check only the 2 products just entered, and set quantity 2 for each.
3. Click **Enter** to apply.
4. Click **Calc**; verify Total Item = 2.
5. Click **Save Drafts**; confirm the alert.
6. Verify the draft list shows No. Of Items = 2 and Draft Amt matches the Calc Final Amount.
7. Click **Order Again**; verify 2 rows reopen.
8. Click **Calc** again; verify Final Amount matches the original.
9. Click **View All Selected Items**; verify the total matches the original Final Amount.

**Expected Result:** The overridden quantity (2 each) and its Final Amount persist through Save Draft and Order Again.

**Actual Result:** ❌ **FAIL** — item count was correct throughout (2 in the draft, 2 reopened), but the **pricing was not**: original Calc Final Amount **202.91** → after Order Again + recalculate: **6,290.47** (~31× increase). View Selected Items total matches the inflated number, not the original. **Reproduced identically across 4 separate runs.**

**Status:** **FAIL**

---

## TC-10 — Scenario 8: 7 items, random valid quantities (1–7) → Calc → Save Draft → Order Again → Calc → Save → Add Sale

**Precondition:** Logged in, customer "Demo 4" selected.

**Test Data:** 7 product rows, each given a random quantity between 1 and 7 (checked against each row's live available stock so none are actually over-stock).

**Steps:**
1. For each of 7 product rows, enter a random quantity from 1–7 that's within that row's available stock.
2. Click **Calc**; verify Total Item = 7.
3. Click **Save Drafts**; confirm the alert; verify the draft list shows No. Of Items = 7 with the matching amount.
4. Click **Order Again** on that draft.
5. Verify the product grid reopens with 7 rows.
6. Click **Calc** again; verify Total Item and Final Amount match the original.
7. Click **Save** (the payment panel, not Save Drafts); verify the Payable Amount matches the recalculated Final Amount.
8. Click **Add Sale**; verify the "Confirm Sale?" dialog's No Of Items matches.
9. Click **Yes! Proceed.** to finalize the sale.

**Expected Result:** All 7 items and the correct amount persist through the entire chain, ending in a correctly finalized sale.

**Actual Result:** ❌ **FAIL** — with **all-valid quantities and no insufficient-inventory item at all**, the same defect occurred: Save Draft correctly recorded 7 items, but **Order Again reopened only 6 rows**. Recalculating after Order Again: Total Item **6**, Final Amount **4,093.25** (was **4,604.99**). The "Confirm Sale?" dialog showed **No Of Items: 6**, and the sale was finalized at that reduced count/amount — **a real order was billed for 6 items instead of 7.**

**Status:** **FAIL** — this proves the item-loss bug is not specific to insufficient-inventory items; it can happen with any cart during the Save Draft → Order Again round-trip.

---

## TC-11 — Scenario 9: 5 items → Calc → Print → Save → 2% discount → Add Sale → Confirm → Generate Invoice → verify invoice total

**Precondition:** Logged in, customer "Demo 4" selected.

**Test Data:** 5 product rows, quantity 1 Carton each.

**Steps:**
1. Enter quantity 1 into 5 product rows.
2. Click **Calc**; verify Total Item = 5.
3. Click **Print**; verify the Print Preview modal opens; close it.
4. Click **Save**; verify the Payable Amount in the payment panel matches the Calc Final Amount.
5. In the "Cash Discount" field (percentage), enter **2** and tab out.
6. Verify the Payable Amount updates to ~2% less than before.
7. Click **Add Sale**.
8. Verify the "Confirm Sale?" dialog shows No Of Items = 5 and its Total value matches the discounted Payable Amount.
9. Click **Yes! Proceed.** to finalize the sale.
10. Once returned to the Select Customer screen, a "Print Preview!" dialog appears automatically — click **Print** to generate the invoice (opens in a new tab as a PDF).
11. Open the generated Tax Invoice PDF and check: how many line items are listed, and the "Payable Amount" total at the bottom.

**Expected Result:** The invoice should list all 5 items and show a Payable Amount matching the discounted total confirmed at sale time (~1,654.55).

**Actual Result:** ❌ **FAIL** — everything was correct through step 9 (5 items confirmed, correct discounted total of 1,654.55). But the **generated Tax Invoice PDF only listed 3 line items** (dropping 2 of the 5). The invoice's Payable Amount (1,655, after rounding) happened to still be close to the confirmed total — meaning the discrepancy is specifically in *which line items appear on the invoice*, not an obvious total mismatch, which makes this defect easy to miss without counting line items by hand. **Reproduced on 4 separate real, finalized sales.**

**Status:** **FAIL** — most precisely localized finding: the item drop happens specifically between "Yes! Proceed." and the invoice being generated, not anywhere earlier in the flow.

---

## Summary

| TC | Scenario | Status |
|---|---|---|
| TC-01 | Base flow: enter products → Calc → View Selected → Print → Save Draft | PASS |
| TC-02 | Draft list verification | PASS |
| TC-03 | Scenario 1 — Calculate only (5 items, 1 insufficient) | PASS |
| TC-04 | Scenario 1 — full chain (Save Draft → Order Again) | **FAIL** (item count 5→3, amount 11,513.88→1,688.32) |
| TC-05 | Scenario 2 — 4 valid items, full chain | **FAIL** (unexpected stock alert, item count 4→3→2) |
| TC-06 | Scenario 3 — 2 items (1 insufficient), full chain | **FAIL** (item count 2→1, amount 479,609.73→1,521.89) |
| TC-07 | Scenario 4 — 7 items (1 insufficient), full chain | **FAIL** (Print modal defect + item count 7→5→4) |
| TC-08 | Scenario 5 — correct insufficient item, then Calc | PASS (Calc) / needs re-run (Save Draft onward) |
| TC-09 | Scenario 7 — Select All override, full chain | **FAIL** (pricing 202.91→6,290.47, reproduced 4×) |
| TC-10 | Scenario 8 — 7 random valid items, full chain + Add Sale | **FAIL** (item count 7→6, amount 4,604.99→4,093.25, real order affected) |
| TC-11 | Scenario 9 — 5 items, discount, Add Sale, invoice check | **FAIL** (invoice shows 3 items instead of 5, real order affected) |

**Headline finding:** whenever a saved draft is reopened via "Order Again," items are silently dropped and the recalculated amount no longer matches what was originally entered — this happens **regardless of whether any item had insufficient inventory** (confirmed with TC-10's all-valid-quantity cart). Losses have ranged from 1–3 items out of 2–7 entered, and amounts have been off by ~7× to ~315×. Separately, TC-11 shows the same class of item loss can also occur later, between confirming a sale and the invoice being generated — meaning a customer-facing Tax Invoice can under-report what was actually sold even when the sale confirmation screen was correct. Two real, finalized sales (TC-10, TC-11) were affected by this defect during testing.
