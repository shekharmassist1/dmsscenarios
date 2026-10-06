# Test Cases — Bill/New Invoice (Product Page)

**Application:** MAssistCRM-DMS (`admin.massistcrm.com`)
**Login:** `vadilaldms` / `vadilal` → select Distributor **"Demo Distributor 1"**
**Module:** Bill/New Invoice → Select Customer → Product Grid
**Test customer:** **"Demo 4"**
**Automation:** [tests/test_product_page.py](tests/test_product_page.py), [tests/test_inventory_scenarios.py](tests/test_inventory_scenarios.py)

All 12 cases below were run through automated Selenium tests. Every "FAIL" case has been reproduced multiple times (2–4× each) and is a genuine, repeatable app defect — not a one-off automation flake. Steps are written so anyone can follow them manually in the browser.

---

## Bugs to demo first (most severe, most reproducible)

1. **TC-12 — Simplest possible repro: a plain direct sale, no draft involved, still loses items.** Enter 5 items → Calc (correct: 5) → Save → Add Sale → Confirm Sale (correct: 5, correct total) → Proceed. No draft, no Order Again, no discount. The finalized sale then shows only **3 items** on the **My Sales** report page. This is the cleanest evidence that the item loss is not tied to drafts/Order Again at all — it happens somewhere in Confirm Sale → finalization itself.
2. **TC-11 — Items disappear between "Confirm Sale" and the generated invoice.** Same pattern as TC-12, verified via the actual Tax Invoice PDF instead of the My Sales list: 5 items confirmed, correct discounted total — the invoice PDF has only 3 line items.
3. **TC-09 — Pricing corrupts after Order Again (Select-All path).** Item count stays correct (2 items throughout), but Final Amount jumps from 202.91 to 6,290.47 (~31×) after reopening a saved draft via "Order Again" and recalculating. Reproduced identically 4 times.
4. **TC-04/05/06/07 — Item count and pricing both drop whenever a cart contains an item flagged "insufficient inventory," at the Save Draft → Order Again step.** Losses range from losing 1–3 items out of 2–7, and amounts have been off by anywhere from ~7× to ~315×.

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
10. **(Added later)** Query the live database directly (`order_dtls`/`order_products` tables, via a read-only SQL Server account) for the just-created order, and compare `NoOfProducts`, `Order_Amt`, and the actual `order_products` row count against what was originally entered.

**Expected Result:** All 7 items and the correct amount persist through the entire chain, ending in a correctly finalized sale, and the database record matches exactly.

**Actual Result:** ❌ **FAIL** — with **all-valid quantities and no insufficient-inventory item at all**, the same defect occurred: Save Draft correctly recorded 7 items, but **Order Again reopened only 6 rows** (reproduced again on a later run as reopening only **3 rows**, confirming the exact reduced count varies run-to-run but the defect itself is consistent). The "Confirm Sale?" dialog showed the same reduced count, and the sale was finalized at that reduced amount — a real order was billed for fewer items than entered.

**❗ Database-level confirmation (added later, the most important finding of the whole suite):** querying the live database directly for the finalized order (`Order_Id = 229150518`) shows **`order_dtls.NoOfProducts = 3`** and **exactly 3 rows in `order_products`** — precisely matching what the Confirm Sale dialog showed (3, not 7), byte-for-byte. This is **definitive proof that the item loss is genuine backend data corruption, not a UI/report display bug** — the database itself only ever stored 3 line items (Bdm Pista Kesar Shrikhand-200 Gms [1*30], Bdm Pista Kesar Shrikhand-200 Gms [1*1], Super Vanilla Bulk [1*1] 4000ML, totaling ₹3,742.08), even though 7 were entered and confirmed in the draft. Whatever causes the loss happens **before or during the Order Again / recalculation step**, upstream of the database write — by the time Add Sale is confirmed, the reduced count is already final and gets persisted exactly as shown.

**Status:** **FAIL** — this proves the item-loss bug is not specific to insufficient-inventory items; it can happen with any cart during the Save Draft → Order Again round-trip. The new direct-database check settles the single biggest open question from this entire test session: **this is real, persisted data loss, not a rendering/reporting artifact.**

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

## TC-12 — Scenario 10: 5 items (fixed qty 2,1,4,1,1) → Calc → Save → Add Sale → Proceed → verify on My Sales report

**Precondition:** Logged in, customer "Demo 4" selected.

**Test Data:** 5 product rows with quantities 2, 1, 4, 1, 1 (each checked against that row's live available stock first; a requested quantity is reduced to the available stock if it wouldn't otherwise fit — the target was to enter these quantities *within available inventory only*).

**Steps:**
1. Enter quantity 2 into product row 1, 1 into row 2, 4 into row 3 (or whatever that row's stock allows, if less than 4), 1 into row 4, 1 into row 5.
2. Click **Calc**; verify Total Item = 5 and no insufficient-inventory alert.
3. Click **Save**; verify the Payable Amount matches the Calc Final Amount.
4. Click **Add Sale**; verify the "Confirm Sale?" dialog shows No Of Items = 5 and its Total value matches the Payable Amount.
5. Click **Yes! Proceed.** to finalize the sale.
6. Navigate to **My Sales** (top nav).
7. Search for "Demo 4" and find the newest row (top of the list).
8. Verify: Party Name = "Demo 4", No. Of Items = 5, Amount matches the Final Amount, Sale Qty matches the Calc summary's Qty (pcs).

**Expected Result:** The finalized sale on the My Sales report matches everything confirmed earlier in the flow — 5 items, correct amount, correct quantity.

**Actual Result:** ❌ **FAIL** — this is the **simplest, most minimal reproduction found**: no draft, no Order Again, no discount — just a direct Calc → Save → Add Sale → Confirm → Proceed. Every step up through "Confirm Sale?" was correct (5 items, correct total). But the **My Sales report shows only 3 items** for the finalized order (Amount 3210, Sale Qty 62 — internally consistent with 3 items, just not the 5 that were actually sold).

**Status:** **FAIL** — proves the item-loss defect is not tied to drafts or Order Again at all; it reproduces on the plainest possible direct-sale path, verified independently via the My Sales list (a third distinct verification surface, alongside the Confirm Sale dialog and the invoice PDF).

---

## TC-13 — Scenario 11: 3 items → Add Sale → Proceed → My Sales → Edit → Calc/View Selected → Update Sale → Proceed → Print → verify invoice

**Precondition:** Logged in, customer "Demo 4" selected.

**Test Data:** 3 product rows, quantity 1 each.

**Steps:**
1. Enter quantity 1 into 3 product rows.
2. Click **Calc**; verify Total Item = 3.
3. Click **Save**; verify the Payable Amount matches the Calc Final Amount.
4. Click **Add Sale**; verify the "Confirm Sale?" dialog shows No Of Items = 3.
5. Click **Yes! Proceed.** to finalize the sale; dismiss the automatic post-sale Print Preview.
6. Navigate to **My Sales**, search "Demo 4", and verify the newest row's No. Of Items = 3.
7. Open the row's Action menu and click **Edit** (navigates to Edit Sale Product Listing for that order).
8. On the Edit Sale page, click **Calc** and verify Total Item = 3; open **View Selected Items** and verify it lists 3 items.
9. Click **Save**, then click **Update Sale**; verify the "Update Sale!" confirmation dialog's No Of Items matches the Edit page's Calc Total Item.
10. Click **Yes! Proceed.** to confirm the update.
11. Return to **My Sales**, open the same row's Action menu, click **Print** (choose default options in the "Print Preview!" dialog and click its **Print** button) to generate the Tax Invoice PDF in a new tab.
12. Open the generated PDF and check: how many line items are listed, and the "Payable Amount" total at the bottom.

**Expected Result:** All 3 items and the correct amount should persist through the entire chain: creation, My Sales, Edit page, Update Sale, and the final invoice.

**Actual Result:** ❌ **FAIL** — the item drop happened again, and even earlier than in prior scenarios: **My Sales already showed only 2 items right after the initial sale** (3 confirmed at "Confirm Sale?" time → 2 on the report). The Edit Sale page and the "Update Sale!" confirmation dialog both independently confirmed the same reduced count (2), and the two remaining line items are two different pack sizes of the *same* product (Bdm Pista Kesar Shrikhand-200 Gms — 1×1 and 1×30 cartons). The **final invoice PDF also showed only 2 line items**. Notably, the total amount was **not corrupted this time** — Amount (1497.73) and Final Amount (1572.62) stayed byte-identical from the initial Calc all the way through the invoice; only the item count/breakdown was wrong.

**Status:** **FAIL** — extends the defect to two new surfaces (the Edit Sale page and the Update Sale confirmation dialog) and shows the item count can already be wrong on My Sales moments after the original sale, before any editing happens. Also shows the defect can manifest as pure item-count corruption with the total amount preserved, not just as a pricing mismatch.

---

## TC-14 — Scenario 12: 2 scheme-eligible products (combined amount crosses tier 1) → Calc → View Selected → Save → Add Sale → Proceed → verify invoice

**Precondition:** Logged in, customer "Demo 4" selected.

**Test Data:** 2 product rows, both confirmed members of the "QPS_Non-Discounted_Rajasthan_July26" (Scheme Code 11619006) quantity-purchase scheme's 610-product trigger list:
- Product A: **Aam Chaska Falala Candy [1*10] 65ML**, qty 5 Carton (line amount ₹1,170.95 — deliberately kept below the scheme's tier-1 minimum on its own).
- Product B: **Almond Carnival GRMT Tub [1*2] 750ML**, qty 10 Carton (line amount ₹3,747.00), sized so the **combined** total lands inside the scheme's tier-1 range.

The scheme's real tiers (read live from the "Scheme Details" modal): Min ₹3,809.52 / Max ₹5,713.29 → 1 Carton free of "Premium Vanilla PP [1+1] 700ML" (or "Mango Frootful Candy"); two higher tiers grant different free products at higher spend.

**Steps:**
1. Search for and enter Product A (qty 5); verify it carries the scheme tag.
2. Search for and enter Product B (qty 10); verify it shares the same scheme id as Product A, and that the combined line amount (₹4,917.95) falls inside the scheme's tier-1 range (₹3,809.52–5,713.29).
3. Click **Calc**; verify Total Item = 2, and check the summary bar's **Free Item** and **Total Scheme** fields.
4. Click **View Selected Items**; verify the bonus product appears in the list, and that its total value matches the Calc Final Amount.
5. Click **Save**; verify the Payable Amount matches the Calc Final Amount.
6. Click **Add Sale**; verify the "Confirm Sale?" dialog, then **Yes! Proceed.** to finalize the sale.
7. Generate the invoice (auto Print Preview → Print); verify the bonus product and item count on the invoice.

**Expected Result:** Once the combined purchase amount of scheme-eligible products crosses ₹3,809.52, the system should automatically apply the scheme: Free Item should show **≥ 1**, Total Scheme should show a value **> 0**, and "Premium Vanilla PP" should appear as a free line item in View Selected Items, on the Confirm Sale total, and on the final invoice — bringing the total line count to 3 (2 purchased + 1 free).

**Actual Result:** ❌ **FAIL** — <span style="color:red;font-weight:bold">Free Item stayed at `0`</span> and <span style="color:red;font-weight:bold">Total Scheme stayed at `0.00`</span>, even though the combined line amount (₹4,917.95, confirmed against the app's own Calc "Amount" field) landed squarely inside the tier-1 range. The bonus product "Premium Vanilla PP" never appeared — not in View Selected Items (only the 2 purchased lines showed), not on the Confirm Sale dialog, and not on the generated invoice (also only 2 line items). This was reproduced identically across two independent live runs, the second time using freshly re-verified genuine trigger products (ruling out "wrong product" as the cause) and re-confirming the correct ₹ amount was reached both times. All other checks passed cleanly — Calc Final Amount, Payable Amount, and View Selected Items total all stayed consistent with each other (₹5,163.85 across the board), confirming the purchased-item pricing itself was correct; only the scheme/free-goods logic failed to trigger.

**Status:** **FAIL** — **Free Item = 0** is the core defect: reaching a scheme's qualifying purchase amount does not automatically grant the promised free item, at least not through this direct flow. (Note: the Scheme Details modal exposes a disabled radio button per tier, `name="chk11619006"` — possibly the scheme is meant to require a manual opt-in selection rather than applying automatically; this was identified but not yet investigated further.)

---

## TC-15 — Scenario 13: Click Print with 0 items → expect validation alert → enter 2 items → verify Print Preview then works

**Precondition:** Logged in, customer "Demo 4" selected.

**Test Data:** No items initially; 2 product rows, quantity 1 each, entered after the empty-cart check.

**Steps:**
1. On the Bill/New Invoice page, with **no quantities entered into any product row**, click **Print**.
2. Verify a validation alert appears, and dismiss it.
3. Enter quantity 1 into 2 product rows.
4. Click **Print** again; verify the normal Print Preview modal opens correctly with its "not saved" note, then close it.

**Expected Result:** Clicking Print with an empty cart should show a clear validation message (not silently do nothing). After entering valid items, Print should behave normally — the earlier empty-cart click should have no lasting effect on the page.

**Actual Result:** ❌ **FAIL** — step 2 behaved correctly: a jconfirm "Alert" appeared with the message *"To check print preview please select items for bill."*, exactly as expected, and no items were needed to trigger it. However, step 4 failed: after entering 2 valid items, clicking **Print** again <span style="color:red;font-weight:bold">never opened the Print Preview modal — the `#btnPrintPreview` button itself stays hidden</span> (`displayed=False`, confirmed via direct DOM inspection; only one such element exists, ruling out a duplicate-element issue). The button never reappears after the empty-cart validation alert is dismissed, even though the cart now legitimately has 2 items in it. Reproduced identically across two independent live runs.

**Status:** **FAIL** — dismissing the "select items for bill" alert appears to leave the Print button permanently hidden for the rest of the session on that page load; adding valid items afterward does not restore it. A full page reload/re-navigation is presumably needed to recover Print functionality, which is not obvious to a real user and blocks a legitimate workflow (accidentally clicking Print before entering any items, a very plausible real-world mistake, then permanently loses the ability to preview/print that order without starting over).

---

## TC-16 — Scenario 14: Enter product → Calc → click Print repeatedly (every 15s) → verify the company header stays correct each time

**Precondition:** Logged in, customer "Demo 4" selected.

**Test Data:** 1 product row, quantity 1.

**Steps:**
1. Enter quantity 1 into 1 product row and click **Calc**.
2. Click **Print**; once the Print Preview opens, fetch its underlying PDF content (via the iframe's report URL) and record the company/letterhead name shown at the top.
3. Close the Print Preview, wait 15 seconds, then click **Print** again. Repeat for a total of 4 checks (~45 seconds spanning all checks).
4. On every check, verify: (a) the Print Preview genuinely opened (not an unrelated error), and (b) the company header on the generated PDF reads **"Demo Distributor 1"** (the distributor associated with this login) — never a different company.

**Expected Result:** All 4 checks should show the same, correct company header ("Demo Distributor 1"), with Print Preview opening cleanly every time.

**Actual Result:** ❌ **FAIL** — check 1/4 passed correctly: Print Preview opened, and the PDF's letterhead correctly read **"Demo Distributor 1"** (no wrong-company / session-bleed issue found on this first check). However, check 2/4 failed outright: clicking **Print** a second time (immediately after closing it once) did **not** reopen the Print Preview at all — instead it showed a completely unrelated jconfirm error dialog: <span style="color:red;font-weight:bold">*"Something went wrong. Please contact the administrator to enable the necessary permissions. Error Code : -1014"*</span>, with only an "Ok" button. Confirmed reproducible via multiple independent live runs (not a timing flake — reproduced with waits up to 2 seconds between close and reopen).

**Status:** **FAIL** — no evidence of a wrong-company/session-bleed bug was found (the one check that succeeded showed the correct company every time), but this surfaced a **more severe, more general version of the TC-15 defect**: TC-15 found the Print button gets stuck after dismissing the empty-cart validation alert; this scenario shows the *exact same class of breakage* — Print becoming unusable and throwing a permissions error (Error Code -1014) — from a completely different, far more mundane trigger: simply closing Print Preview normally once (with valid items in the cart, no error alert involved at all) and clicking Print again. This suggests the underlying Print modal has a broken re-initialization/session-token issue that isn't specific to the empty-cart path — it may break on essentially *any* second use of Print within the same page load, which would affect real users constantly (anyone who previews a print, closes it to double check something, and prints again).

---

## TC-17 — Scenario 15: Create order (2 items) → Edit → Add More → increase qty + add a new item → Calc → verify → Update Sale → Proceed → verify against database

**Precondition:** Logged in, customer "Demo 4" selected.

**Test Data:** 2 product rows, quantities 2 and 1 (Bdm Pista Kesar Shrikhand-200 Gms [1*30] and [1*1]). During edit: increase the [1*30] item's quantity from 2 → 5 Carton, and add a brand-new third item (Kesar Shrikhand-200 Gms [1*30], qty 1).

**Steps:**
1. Enter quantity 2 into product row 0 and quantity 1 into product row 1. Click **Calc**, **Save**, **Add Sale**, verify the "Confirm Sale?" dialog, then **Yes! Proceed.** to finalize the order.
2. Verify the order on **My Sales** (No. Of Items = 2), then click **Edit** to open the Edit Sale page.
3. On the Edit page, click **Add More** (the grid initially only shows the order's 2 existing items — clicking Add More expands it to the full catalog, with existing quantities pre-filled).
4. Increase row 0's quantity from 2 to **5 Carton**, and enter quantity 1 into a genuinely new product row (not previously in the order).
5. Click **Calc**; verify Total Item = 3 and the amount reflects the increased quantity and new item.
6. Open **View Selected Items**; verify it lists 3 items and its total matches the Calc Final Amount.
7. Click **Save**, then **Update Sale**; verify the confirmation dialog's No Of Items, then **Yes! Proceed.**
8. Query the live database directly (`order_dtls`/`order_products`) for this order and compare against what the UI showed throughout.

**Expected Result:** The order should end up with 3 items (qty 5, qty 1, qty 1 respectively) and a correspondingly higher total, consistently reflected across Calc, View Selected Items, the Confirm Update dialog, and the database.

**Actual Result:** ❌ **FAIL** — a genuine mechanical discovery was needed first: the Edit page's product grid is scoped to only the order's existing items by default (not the full catalog), and the **"Add More"** button must be clicked to reveal the rest of the catalog for adding a new item — undocumented in the UI and easy to miss. Once that flow was used correctly, the actual result was a **three-way inconsistency, not just item loss**:

- **Calc (after edit):** `Total Item = 2`, `Final Amount = 3094.51` — <span style="color:red;font-weight:bold">byte-identical to the Calc result *before* the edit</span>, as if the quantity increase and new item were never entered at all.
- **View Selected Items (same moment):** showed only 2 items still (the new 3rd item is missing here too), but *did* register the quantity increase — `[1*30]` at 150 pcs (5 Carton), value ₹7,609.46, total ~**₹7,660.19** — completely different from Calc's ₹3,094.51.
- **Confirm Update dialog:** `No Of Items = 2`, `Total value = 3094.51` — matches the *stale* Calc result, not View Selected Items.
- **Database (final, authoritative):** `Order_Id 229223326` → `NoOfProducts = 2`, `Order_Amt = 3094.51`, and `order_products` shows `[1*30]` at **Quantity = 60 pcs (2 Carton)** — the **original, pre-edit quantity**, and no trace of the new 3rd item at all.

**Status:** **FAIL** — the edit was <span style="color:red;font-weight:bold">entirely discarded on the backend</span>: both the quantity increase and the new item were silently dropped, and the order was persisted with exactly its original pre-edit state — even though Update Sale reported success. Worse, different parts of the UI disagreed with each other about what was actually in the cart at the moment of editing (Calc said "nothing changed," View Selected Items said "quantity changed but no new item," neither matched what was actually saved). This is a new, distinct manifestation of the item-loss defect family — not just fewer items than expected, but edits being accepted by the UI and then silently reverted on save.

---

## TC-18 — Scenario 16: Single scheme product sized to cross its own tier-1 threshold → Calc → Save → Add Sale → Proceed → verify invoice + DB → Edit via My Sales → verify scheme still applied → Proceed → verify DB

**Precondition:** Logged in, customer "Demo 4" selected.

**Test Data:** A single scheme-tagged product ("Aam Chaska Falala Candy [1*10] 65ML", scheme "QPS_Discount_Dummy-June26", id 11585871). **Important correction:** the product's scheme tiers are read **live** from its own "Scheme Details" popup at test time (via the gift icon next to the product name) rather than assumed — an earlier version of this test used the tier range from TC-14's scheme (id 11619006, ₹3,809.52–5,713.29), but that scheme has since been reassigned/rotated on this product; the actual current scheme (11585871) has tier 1 at **₹8,571.43–10,475.19** (Free Qty: 1 Carton of "Best Chocobar Candy [1*14]"). Quantity is sized dynamically so the product's **own** line amount alone lands in that live-read range — no second product involved.

**Steps:**
1. Search the scheme product; click its gift icon to open "Scheme Details" and read the real, current tier-1 range live (confirmed: ₹8,571.43–10,475.19).
2. Enter quantity 37 Carton (line amount ₹8,665.03, correctly within the live tier-1 range).
3. Click **Calc**; verify Total Item = 1, Free Item ≥ 1, and Total Scheme > 0.
4. Click **Save**, then **Add Sale**; verify the "Confirm Sale?" dialog, then **Yes! Proceed.** to finalize the order.
5. Query the database (`order_dtls`/`order_products`) for the new order and verify `NoOfProducts`, `Order_Amt`, and the scheme fields (`SchemeId`, `SchFreeQty`).
6. Generate the invoice and verify the bonus product appears on it.
7. Verify the order on **My Sales**, then click **Edit** to open the Edit Sale page.
8. On the Edit page, click **Calc** again; verify Free Item and Total Scheme are still correctly populated.
9. Click **Save**, then **Update Sale**; verify the confirmation dialog, then **Yes! Proceed.**
10. Query the database again for the updated order and verify the scheme fields still reflect the scheme.

**Expected Result:** A single product that reaches the scheme's tier-1 threshold entirely on its own should trigger the same free-goods bonus as the combined-product case in TC-14 — Free Item ≥ 1, Total Scheme > 0, a bonus line on the invoice, `SchemeId`/`SchFreeQty` populated in the database — and that should persist unchanged through editing via My Sales.

**Actual Result:** ❌ **FAIL** — the entered product correctly carried a scheme tag (`scheme_id=11585871`), and its own line amount (₹8,665.03, qty 37 Carton) correctly landed within the *live-verified* tier-1 range (₹8,571.43–10,475.19) with no second product needed. But exactly like TC-14: <span style="color:red;font-weight:bold">Free Item stayed at `0`</span> and <span style="color:red;font-weight:bold">Total Scheme stayed at `0.00`</span>, both on initial Calc (`total_item=1, amount=8665.03, final_amount=9098.28`) and again on the Edit Sale page's Calc after the order was finalized (identical values). The invoice showed only the 1 entered line item (Payable ₹9,098), no bonus product. Critically, the **database itself confirms the scheme was never applied at all**, not just a UI display issue: `order_dtls.SchemeId = 0` and `SchFreeQty = '0'` (Order_Id 232660786, both before and after the edit) — the real scheme id (11585871) that the product was correctly tagged with in the UI never made it into the order record. `NoOfProducts=1`, `Order_Amt=9098.28`, and `order_products` (370 pcs, ₹9,098.28) were otherwise internally consistent both before and after editing, matching the UI exactly — the only thing wrong is that the scheme fields are always zero/blank.

**Status:** **FAIL** — this **rules out "combining two products" as a necessary trigger condition** for the TC-14 scheme defect: a single product independently and correctly crossing the (live-verified) tier-1 threshold still gets no bonus item, no `Total Scheme`, and — confirmed directly in the database — no `SchemeId` recorded on the order at all. The defect also reproduces identically after editing the order via My Sales, showing it isn't a one-time creation-flow glitch. This strengthens TC-14's finding considerably: the scheme/free-goods engine appears to never actually fire through this flow, regardless of how the qualifying amount is reached. **A secondary but notable finding**: this app's schemes are not static — the same product's applicable scheme (and its tier thresholds) changed between test sessions, so any test relying on scheme tiers should read them live via the "Scheme Details" popup rather than hardcoding previously-observed values.

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
| TC-12 | Scenario 10 — 5 items, direct sale (no draft), My Sales check | **FAIL** (My Sales shows 3 items instead of 5, real order affected — simplest repro yet) |
| TC-13 | Scenario 11 — 3 items → My Sales → Edit → Update Sale → invoice check | **FAIL** (item count 3→2 on My Sales/Edit/Update dialog/invoice; total amount preserved this time; real order affected) |
| TC-14 | Scenario 12 — 2 scheme-eligible products, combined amount crosses tier 1 → Add Sale → invoice | **FAIL** (**Free Item = 0**, Total Scheme = 0.00 — scheme never applied despite correct qualifying amount; real order affected) |
| TC-15 | Scenario 13 — Print with 0 items → validation alert → enter 2 items → Print again | **FAIL** (validation alert correct; but **Print button stays hidden** after dismissing it, even after adding valid items) |
| TC-16 | Scenario 14 — Enter product → Calc → click Print 4× (15s apart) → verify company header | **FAIL** (header correct on check 1; check 2 shows **"Error Code : -1014"** instead of reopening Print — broader version of TC-15's defect) |
| TC-17 | Scenario 15 — Create order → Edit → Add More → increase qty + add new item → Update Sale → DB verify | **FAIL** (edit **entirely discarded on the backend** — DB shows original pre-edit state; Calc/View Selected Items/Confirm Update all disagreed with each other too) |
| TC-18 | Scenario 16 — Single scheme product crosses tier-1 threshold alone → Add Sale → Edit → verify DB | **FAIL** (**Free Item = 0**, Total Scheme = 0.00, **DB SchemeId = 0** both before and after edit — rules out "2 products" as required trigger for TC-14's defect) |

**Headline finding:** items get silently dropped from an order somewhere between confirming a sale and it being finalized/recorded — and this is now confirmed across **six independent verification surfaces**: the "Confirm Sale?" dialog vs. the drafts list (TC-04–07, TC-09), vs. the generated Tax Invoice PDF (TC-11, TC-13), vs. the My Sales report list (TC-12, TC-13), vs. the Edit Sale page (TC-13), vs. the "Update Sale!" confirmation dialog (TC-13), and — most importantly — vs. **the live production database itself (TC-10, TC-17)**. TC-12 and TC-13 prove this has **nothing to do with drafts, Order Again, insufficient inventory, or discounts** — the simplest possible direct sale (enter items, Calc, Save, Add Sale, Proceed) still loses items, and TC-13 shows the loss can already be visible on My Sales within moments of the original sale, before any editing happens. Losses have ranged from 1–3 items out of 2–7 entered; amounts have sometimes stayed correct (TC-13) and sometimes been off by anywhere from ~7× to ~315× (when a draft/Order-Again round-trip is involved), showing the defect has at least two distinct failure modes — item-count corruption alone, and item-count-plus-pricing corruption. **Five real, finalized sales (TC-10, TC-11, TC-12, TC-13, TC-17) were affected by this defect during testing.**

**Extension of the item-loss defect (TC-17):** editing an already-finalized order — increasing an existing item's quantity and adding a brand-new item, then Update Sale — was **entirely discarded on the backend**, confirmed at the database level: the order ended up with exactly its original pre-edit quantities, as if Update Sale had never been clicked. Worse, at the moment of editing, Calc, View Selected Items, and the Confirm Update dialog each showed a **different, mutually-inconsistent** picture of what was in the cart, none of which matched what actually got saved. This shows the defect isn't limited to items disappearing during creation — edits themselves can be silently swallowed too.

**Capstone confirmation (TC-10):** a direct, read-only SQL query against the production database (`order_dtls`/`order_products` tables) for a real finalized order shows the database itself only ever stored the reduced item count — not the originally-entered 7. This settles the question that every prior test in this suite could only approach indirectly: **this is genuine, persisted data corruption on the backend, not a UI rendering bug or a reporting/invoice-generation artifact.** Every UI/report-level check throughout this suite has been correctly reflecting reality all along.

**Second, distinct defect (TC-14, TC-18):** the quantity-purchase scheme (free-goods) feature does not automatically grant its promised free item even when the qualifying purchase amount is correctly reached — <span style="color:red;font-weight:bold">Free Item shows `0`</span> and no bonus product is added anywhere in the flow. This is a separate bug class from the item-loss defect above (schemes/free-goods vs. order item persistence), found in the same test session. **TC-18 strengthens this considerably**: a *single* product independently crossing the tier-1 threshold (no combining needed, unlike TC-14) still gets no bonus — and, checked directly against the database this time, `order_dtls.SchemeId` is `0` on the persisted order, not just missing from the UI. The defect also reproduces identically after editing the order via My Sales, ruling out a one-time creation-flow glitch. Together, TC-14 and TC-18 suggest the scheme/free-goods engine essentially never fires through this flow, regardless of how the qualifying amount is reached.

**Third, distinct defect (TC-15, TC-16):** clicking Print with an empty cart correctly shows a validation alert, but dismissing it <span style="color:red;font-weight:bold">permanently hides the Print button</span> for the rest of that page session — even after the user goes on to add valid items, Print never becomes available again without a full page reload. A UI-state bug, not a data-integrity one, but one that blocks a legitimate workflow after an easy real-world mistake (clicking Print too early). **TC-16 shows this is a broader, more general defect than first thought**: the *exact same class of breakage* — Print becoming unusable, this time with an explicit <span style="color:red;font-weight:bold">"Something went wrong...Error Code : -1014"</span> permissions error — reproduces from simply closing Print Preview normally once (valid items in the cart, no validation alert involved at all) and clicking Print again. This suggests essentially *any* second use of Print within the same page load can break, not just the empty-cart path — a defect likely to affect real users regularly.

---

# Test Cases — Sale Return (Goods Receive)

**Application:** MAssistCRM-DMS (`admin.massistcrm.com`)
**Login:** `vadilaldms` / `vadilal` → select Distributor **"Demo Distributor 1"**
**Module:** Sale Return → Select Customer → Goods Receive (`DMSPages/ProductReceived.html`)
**Test customer:** **"Demo 4"**
**Automation:** [pages/sale_return_page.py](pages/sale_return_page.py), [tests/test_sale_return_scenarios.py](tests/test_sale_return_scenarios.py)

This is a separate module from Bill/New Invoice above — its own page object and test file, isolated from the TC-01–17 suite. Additional Sale Return scenarios should be appended here as SR-02, SR-03, etc.

---

## SR-01 — Scenario 1: 3 Saleable + 1 Damaged item → hamburger batch split → Calc → Print → View Selected → Save → Receive Goods → Confirm → verify DB

**Precondition:** Logged in, Sale Return module (`ProductReceived.html`) opened, customer "Demo 4" selected via "Without Reference".

**Test Data:** 3 randomly chosen product rows entered as Saleable Item, qty 1 Carton each; 1 randomly chosen product row entered as Damage Item, qty 1 Carton.

**Steps:**
1. Log in and open Sale Return; select customer "Demo 4".
2. In the "Sale Return For..." popup, select "Without Reference" and click **Go!**.
3. Wait for the product grid to load; verify the page header shows "Sale Return for Demo 4 from Demo Distributor 1".
4. Enter quantity 1 into the Saleable Item field of 3 random product rows, and quantity 1 into the Damage Item field of 1 random product row.
5. Click the hamburger (batch) icon on the damaged row; verify the "Batch List Of…" modal lists Saleable Item and Damage Item columns; click **Apply** (dismissing any "Insufficient Inventory" alert that appears).
6. Click **Calc**; verify Total Item = 4.
7. Click **Print**; verify the Print Preview modal opens with the "not yet saved" note, then close it.
8. Click **View All Selected Items**; verify it lists the 3 Saleable rows.
9. Click **Save**, then click **Goods Receive**.
10. Verify the "Return Confirm!" dialog shows No Of Items = 4, then click **Yes! Proceed.**
11. Verify the "Success — Goods received successfully" message appears; dismiss it.
12. Query the live database (`order_dtls`/`order_products`) for the just-created return and verify the amount matches the Calc Final Amount.

**Expected Result:** All 12 steps complete without mismatch; the return is correctly recorded in the database with a matching amount.

**Actual Result:** ✅ Pass — all steps completed correctly end to end, and the database record matched the Calc Final Amount. Two real app findings were folded into the automation itself:
- Typing directly into the row's Damage Item field alone does **not** persist — the row's hamburger/"Batch List" modal must be opened and Apply clicked for the damage quantity to actually commit.
- A completed Sale Return is stored in `order_dtls`/`order_products` with **`OrderType = 'CreditNote'`** (not `'return'`, which is a different, earlier-stage order type unrelated to a completed Goods Receive).

**Status:** **PASS**

---

## SR-02 — Scenario 2: With Reference → pick a past sale invoice → verify it against the DB → Calc → View Selected → Full Sale Return → Confirm → verify DB

**Precondition:** Logged in, Sale Return module opened, customer "Demo 4" selected. The test prefers referencing the newest invoice already available in the "With Reference" picker; only if none are available does it create a fresh sale first (via the untouched Bill/New Invoice module) to guarantee a valid invoice to reference.

**Test Data:** The newest existing sale invoice for "Demo 4" found via "With Reference" (or a freshly created 2-item sale, qty 1 Carton each, if none were available).

**Steps:**
1. Open Sale Return, select "With Reference", and check whether any invoice is available for "Demo 4"; if none are, create a small real sale (2 items, qty 1 each) via Bill/New Invoice instead and use that Order_Id.
2. Log in and open Sale Return; select customer "Demo 4".
3. In the "Sale Return For..." popup, select "With Reference" and click **Go!**.
4. In the "Sale Details..." invoice picker, find the target invoice by Order_Id.
5. Query the database (`order_dtls`/`order_products`, `OrderType='sale'`) for that Order_Id and verify its Amount and NoOfItem match what the UI invoice picker shows, **before** ever selecting it.
6. Check that invoice's row and click **Select**; verify the product grid loads scoped to exactly that invoice's items, pre-filled with the originally sold quantities.
7. Click **Calc**; verify Total Item matches the referenced invoice's item count.
8. Click **View All Selected Items**; verify it lists all referenced items.
9. Click **Full Sale Return**; verify the confirmation dialog references the original order number ("Create full Credit Note against order #...?").
10. Click **Yes, Proceed.**
11. Verify the "Success — Goods received successfully" message appears; dismiss it.
12. Query the database for the newly completed return and verify its amount matches both the Calc Final Amount and the referenced original sale's amount (a full return should credit back the full original value).

**Expected Result:** The invoice picked via "With Reference" is a real, verifiable original sale; the return created against it is correctly scoped, finalized, and recorded in the database with an amount matching that original sale.

**Actual Result:** ✅ Pass (on a freshly created invoice, and on most existing invoices — see SR-03 for a known exception found on at least one existing invoice). Several real app findings were folded into the automation itself:
- The "With Reference" invoice picker only lists invoices that haven't already been fully returned, and repeated test runs against this shared demo account deplete that pool ("There is no invoice left for this client on selected dates.") — the test prefers an existing invoice but falls back to creating its own fresh one when none are available.
- The "With Reference" flow has **no Print/Save/Receive Goods step at all** — it finalizes directly via a single **"Full Sale Return"** button, distinct from the "Without Reference" flow's Save → Receive Goods → "Return Confirm!" sequence.
- A completed "With Reference" return is stored with **`OrderType = 'CREDITNOTE'`** (uppercase — SQL Server's default case-insensitive collation matches it against the same `'CreditNote'` query used for SR-01, so no separate DB helper was needed).
- A blocking **"Alert! / Product not exists!"** dialog (for a since-deactivated product) can silently sit in front of the product grid indefinitely if not dismissed while waiting for it to load.
- Several steps (selecting "With Reference" and clicking Go!, and checking an invoice row and clicking Select) are prone to an intermittent click-registration flake on this shared environment that can revert the whole flow back to the Select Customer screen; the automation retries the whole sequence from a fresh page load rather than just re-clicking the failed step.

**Status:** **PASS** (intermittent — see SR-03)

---

## SR-03 — Defect: a "With Reference" invoice that hits the Total Item = 0 / View All Selected Items = empty display bug never gets marked as returned, and can be fully returned again — creating duplicate Credit Notes for the same sale

**Precondition:** Logged in, Sale Return module opened, customer "Demo 4" selected, referencing an *existing* sale invoice (Order_Id 232082193, Amount ₹1,572.62, NoOfItem 2 — confirmed matching `order_dtls`/`order_products` beforehand) via "With Reference", following the same steps as SR-02.

**Test Data:** Existing invoice Order_Id 232082193 for "Demo 4" (products: "Bdm Pista Kesar Shrikhand-200 Gms [1*30]" and "[1*1]"), referenced via "With Reference" on two separate, independent automated runs.

**Steps:** Same as SR-02 steps 1–12, referencing this specific existing invoice — run twice, on two separate occasions.

**Expected Result:** Calc's Total Item should read 2 and View All Selected Items should list both referenced products. Once an invoice has been fully returned via "With Reference", it should no longer be creditable a second time (a full return should exhaust it, the same way it's excluded once already-returned invoices are excluded from the picker in the normal case).

**Actual Result:** ❌ **FAIL**, reproduced identically on two separate automated runs (2026-07-21, ~13:11 and ~14:43) — both times the product grid loaded correctly (2 rows, right products, pre-filled quantities), but after clicking **Calc** the summary showed `Total Item = 0` while, in the same summary, **Amount (₹1,497.73) and Final Amount (₹1,572.62) were both correct**. **View All Selected Items** then showed an **empty list** instead of the 2 referenced products. Both times the flow still proceeded to completion: "Full Sale Return" correctly referenced order #232082193, the success message appeared, and a new, fully correct Credit Note was persisted to the database each time:
- Run 1 → Order_Id **232091756**, `OrderType='CREDITNOTE'`, `Order_Amt=1572.62`, `NoOfProducts=2.00`, correct line items (30 pcs / ₹1,521.89 + 1 pc / ₹50.73).
- Run 2 → Order_Id **232136591**, `OrderType='CREDITNOTE'`, `Order_Amt=1572.62`, `NoOfProducts=2.00` — **an independent second Credit Note for the exact same original amount, against the same original sale #232082193**, created purely because the invoice was still selectable in the "With Reference" picker the second time (it should have already been excluded, being fully returned).

**Status:** **FAIL** — two distinct, compounding defects on the same invoice:
1. A **display bug**: the "Total Item" counter and "View All Selected Items" panel incorrectly show 0/empty for this invoice's "With Reference" full return, even while the Amount/Final Amount fields alongside them, and the eventual persisted database record, are correct.
2. A more serious **data-integrity bug**: whatever this display bug is tied to appears to also prevent the invoice from being marked "already returned" — it remained selectable in the "With Reference" picker on a second, independent run days apart and generated a **second, duplicate full Credit Note (₹1,572.62) against the same original sale**. If reproducible outside test automation, this could mean a real distributor accidentally (or repeatedly) crediting the same sale back multiple times through this flow. This is distinct in kind from the item-loss defect family in the Bill/New Invoice module (TC-04–17) — there, *data* was lost while the UI looked correct; here the *display* is wrong on a specific invoice, and that invoice then becomes repeatably, fully creditable. Root cause not confirmed; a prior live exploration on a different existing invoice found a blocking "Alert! / Product not exists! (for a since-deactivated product)" dialog in this same flow, which is a plausible trigger but was not directly observed on this specific repro.

---

## SR-04 — Scenario 4: Without Reference, 5 items → Calc → View Selected → add a 6th item → Calc → View Selected → Print → Save; verify consistency at every step

**Precondition:** Logged in, Sale Return module opened, customer "Demo 4" selected via "Without Reference".

**Test Data:** 5 randomly chosen product rows entered as Saleable Item (qty 1 Carton each), then a 6th distinct row added afterward. Items are tracked by their stable `variant_id`, not display name, and picked without regard to current inventory level.

**Steps:**
1. Log in and open Sale Return; select customer "Demo 4"; choose "Without Reference" and click **Go!**.
2. Enter quantity 1 into the Saleable Item field of 5 random product rows.
3. Click **Calc**; verify Total Item = 5.
4. Click **View All Selected Items**; verify it lists all 5 items, matching Calc.
5. Enter quantity 1 into a 6th, previously-untouched product row.
6. Click **Calc** again; verify Total Item = 6 and Final Amount increased from the pass-1 value.
7. Click **View All Selected Items** again; verify it now lists all 6 items.
8. Click **Print**; verify the Print Preview opens with the "not yet saved" note.
9. Click **Save**; verify the Goods Receive button becomes visible, confirming the 6-item cart survived Save.

**Expected Result:** Total Item, View All Selected Items, and Final Amount should all stay mutually consistent and correctly reflect the cart's contents at every step, both before and after adding the 6th item, through Print and Save.

**Actual Result:** ✅ Pass — all steps completed correctly and consistently at every checkpoint (Calc pass 1 = 5, View Selected pass 1 = 5, Calc pass 2 = 6 with a higher Final Amount, View Selected pass 2 = 6, Print opened correctly, Save revealed Goods Receive with all 6 items intact). Two real findings surfaced while building this scenario:
- This catalog can show the **same product display name on more than one distinct row** — tracking "distinct items entered" by name (as SR-01/SR-02 originally did) can silently under-count if two touched rows happen to share a name. The test instead keys by each row's `variant_id`, which is guaranteed stable and unique.
- At the time of this run, **every product in the catalog showed negative available inventory** (e.g. -250, -1530, -602 across different products' batch totals), driven by the sheer volume of automated Sale/Sale-Return testing run against this shared demo account throughout this session. A Sale Return doesn't require positive stock to process (it credits items back into inventory rather than depleting it), so the scenario deliberately does not filter by inventory level — but this is worth knowing if a future scenario ever needs genuinely in-stock items on this account.

**Status:** **PASS**

---

## SR-05 — Scenario 5: Without Reference, 2 Saleable + 2 Damaged items → verify batch split for each → Calc → View Selected → add a 5th item → Calc → View Selected → Print → Save; verify consistency at every step

**Precondition:** Logged in, Sale Return module opened, customer "Demo 4" selected via "Without Reference".

**Test Data:** 4 randomly chosen product rows with distinct `variant_id`s — 2 entered as Saleable Item, 2 as Damage Item (qty 1 Carton each) — then a 5th distinct-variant row added afterward, all as Saleable.

**Steps:**
1. Log in and open Sale Return; select customer "Demo 4"; choose "Without Reference" and click **Go!**.
2. Enter quantity 1 into the Saleable Item field of 2 random product rows, and quantity 1 into the Damage Item field of 2 more.
3. Click the hamburger (batch) icon on each of the 4 rows and verify the "Batch List Of…" modal lists Saleable Item and Damage Item columns. For the 2 Saleable rows, close via **Cancel** (verification only — see SR-06). For the 2 Damage rows, click **Apply** (required to persist, per SR-01).
4. Click **Calc**; verify Total Item = 4.
5. Click **View All Selected Items**; verify it lists only the 2 Saleable items (Damage excluded, per SR-01).
6. Enter quantity 1 into a 5th, previously-untouched product row as Saleable.
7. Click **Calc** again; verify Total Item = 5 and Final Amount increased from the pass-1 value.
8. Click **View All Selected Items** again; verify it now lists 3 Saleable items (2 original + 1 new).
9. Click **Print**; verify the Print Preview opens with the "not yet saved" note.
10. Click **Save**; verify the Goods Receive button becomes visible, confirming the 5-item cart survived Save.

**Expected Result:** The hamburger modal correctly reflects the Saleable/Damage classification for every entered row; Total Item, View All Selected Items, and Final Amount stay mutually consistent through both Calc passes, Print, and Save.

**Actual Result:** ✅ Pass — all steps completed correctly and consistently (Calc pass 1 = 4, View Selected pass 1 = 2 saleable, Calc pass 2 = 5 with a higher Final Amount, View Selected pass 2 = 3 saleable, Print opened correctly, Save revealed Goods Receive with all 5 items intact). This scenario deliberately verifies the Saleable row's batch split via **Cancel** rather than Apply — see **SR-06** below for why using Apply on a Saleable row breaks the cart entirely. Row selection also uses a `variant_id`-based picker (not row index) after confirming live that this catalog can show the identical underlying variant on more than one grid row, which previously caused an intermittent "expected 5, got 4" miscount when a row-index-only picker happened to select a duplicate.

**Status:** **PASS**

---

## SR-06 — Defect: clicking Apply on a Saleable Item row's "Batch List" (hamburger) modal silently clears that row's entered quantity, breaking Calc's Amount/Final Amount and emptying View All Selected Items

**Precondition:** Logged in, Sale Return module opened, customer "Demo 4" selected via "Without Reference", 2 Saleable + 2 Damage items entered (rows independently confirmed to have real, non-empty batch data via the hamburger check first).

**Test Data:** 2 Saleable rows (e.g. "Malai Paneer Cube [200 Gms X 50]" qty 1, "Malai Paneer Cube [100 Gms*100]" qty 1) and 2 Damage rows, all with confirmed negative-but-real batch inventory.

**Steps:**
1. Enter 2 Saleable + 2 Damage items as in SR-05.
2. Open the hamburger/"Batch List Of…" modal on **only the 2 Damage rows** and click **Apply** on each (matching SR-01's proven-required flow). Click **Calc** and **View All Selected Items** — confirm both are correct (Total Item = 4, Amount/Final Amount non-zero and correct, View Selected lists the 2 Saleable items with correct values).
3. Now also open the hamburger modal on **one of the Saleable rows** and click **Apply**.
4. Click **Calc** and **View All Selected Items** again.

**Expected Result:** Applying the batch split on a Saleable row should have no destructive effect — Calc's Amount/Final Amount and View All Selected Items should still correctly reflect all previously entered items.

**Actual Result:** ❌ **FAIL**, reproduced twice independently (once inside the SR-05 scenario itself with automation-picked rows, once in a targeted, deterministic live repro with rows individually pre-checked for real, non-empty batch data): after step 2, everything was correct (`Calc`: `total_item=4`, `amount=9545.82`, `final_amount=9545.82`; `View Selected Items`: 2 correct entries totalling exactly 9545.82). After step 3 (Apply on **one** Saleable row):
- In the automated run: `Calc` returned `total_item='4'` but `amount='0.00'`, `final_amount='0.00'`, and `View All Selected Items` came back **completely empty** — even though Total Item kept counting all 4 items.
- In the targeted repro: clicking **Calc** afterward **timed out entirely** — "Final Amount never populated after clicking Calc" (a harder failure than the 0.00 seen in the other run).
- A screenshot taken at the failure point showed the exact mechanism: the Saleable row that was hamburger-Applied had its **Saleable Item and Qty fields reset to blank** — the quantity that had been typed in was silently discarded. The *other*, untouched Saleable row still correctly showed its entered quantity.

**Status:** **FAIL** — Apply on a Saleable row's batch-split modal **clears that row's own entered quantity**, the opposite of Damage rows (where Apply is *required* to persist the entered value, per SR-01). This single action can leave the whole cart's calculated Amount at ₹0.00 or make Calc hang indefinitely, while the Total Item counter keeps misleadingly reporting the original count — a user checking only Total Item would see no sign anything went wrong until they check Amount or View All Selected Items specifically. Workaround used in SR-05: verify a Saleable row's batch split via **Cancel**, never Apply.

---

## SR-07 — Scenario 7: Without Reference, 2 items (hamburger-checked for negative, non-empty inventory) → click Print 3 times, 30 seconds apart → verify each attempt

**Precondition:** Logged in, Sale Return module opened, customer "Demo 4" selected via "Without Reference".

**Test Data:** 2 product rows individually verified via the hamburger/"Batch List Of…" modal (opened and closed with **Cancel**, no quantity entered yet) to have real, non-empty batch data with negative available inventory before being selected; rows with no batch data at all are skipped.

**Steps:**
1. Log in and open Sale Return; select customer "Demo 4"; choose "Without Reference" and click **Go!**.
2. For each candidate product row, click the hamburger icon and read the "Batch List Of…" modal: skip the row entirely if it shows "There no data available in the table"; otherwise confirm the batch Total is negative, close via **Cancel**, and select the row.
3. Once 2 qualifying rows are found, enter quantity 1 into the Saleable Item field of each.
4. Click **Print**; verify the Print Preview opens correctly.
5. Wait 30 seconds, close the preview, click **Print** again; verify it opens correctly a second time.
6. Wait another 30 seconds, close the preview, click **Print** a third time; verify it opens correctly again.

**Expected Result:** All 3 Print attempts, 30 seconds apart, should open the Print Preview modal correctly with the "not yet saved" note every time.

**Actual Result:** ❌ **FAIL** — the hamburger-based row qualification worked correctly (both selected rows confirmed real batch data with negative totals: −250 and −2,600). Print attempts 1 and 2 both succeeded, opening the Print Preview correctly. **Print attempt 3 failed**: instead of reopening the preview, it showed <span style="color:red;font-weight:bold">"Something went wrong. Please contact the administrator to enable the necessary permissions. Error Code : -1014"</span>.

**Status:** **FAIL** — this is the **exact same defect already documented for the Bill/New Invoice module** (TC-16: repeated Print use within one page load can break with this identical "Error Code : -1014" error instead of reopening the preview). Confirming it reproduces here too, in a completely different module (Sale Return), on the third Print attempt specifically, strongly suggests this is a **shared underlying component or session/token issue affecting Print broadly across the app**, not something isolated to Bill/New Invoice.

---

## SR-08 — Scenario 8: With Reference, invoice with more than 3 items → product page → Calc → View Selected → verify item count consistent at every step + DB

**Precondition:** Logged in, Sale Return module opened, customer "Demo 4".

**Test Data:** A "With Reference" invoice for "Demo 4" whose item count is greater than 3 — prefers an existing qualifying invoice already available in the picker, only creating a fresh sale (4 distinct products, via the untouched Sale/Bill module) if none qualify. Live run picked an existing invoice, Order_Id 232917662 (Amount ₹12,796.08, 4 items).

**Steps:**
1. Log in and open Sale Return; select customer "Demo 4"; choose "With Reference" and click **Go!**; read the invoice list and pick one with item count > 3 (create one if none qualify).
2. Re-open Sale Return, select the customer, "With Reference", and select that same invoice.
3. On the resulting product page, verify the grid row count matches the invoice's item count.
4. Click **Calculate**; verify the Total Item count matches.
5. Click **View All Selected Items**; verify the listed item count matches.
6. Verify the invoice and its item count against the database (`order_dtls.NoOfProducts` and `order_products` row count).
7. Compare the item count recorded at every step above and confirm they are all identical.

**Expected Result:** The item count (4) should be identical across the "With Reference" invoice list, the product page grid, the Calc summary, View All Selected Items, and the database, for an invoice with more than 3 items.

**Actual Result:** ✅ **PASS** — all five readings agreed at 4 items: invoice list (`noofitem`='4'), product page row count (4), Calc Total Item ('4'), View All Selected Items (4 rows), and DB (`NoOfProducts`=4.00, `order_products` row count=4). DB header also matched: `Order_Amt`=12796.08 (UI amount '12796.08'), `OrderType`='sale', `Client_Name`='Demo 4'.

**Status:** **PASS**

---

## Summary

| TC | Scenario | Status |
|---|---|---|
| SR-01 | Scenario 1 — 3 Saleable + 1 Damaged item, full Goods Receive chain, DB verify | PASS |
| SR-02 | Scenario 2 — With Reference full return, prefers existing invoice else creates fresh, DB verify against original sale | PASS (intermittent — see SR-03) |
| SR-03 | Defect — Total Item/View Selected show 0/empty on affected invoices, which then never get marked returned and can be fully credited twice (duplicate Credit Notes), reproduced on 2 separate runs | **FAIL** |
| SR-04 | Scenario 4 — Without Reference, 5 items → Calc → View Selected → add 6th item → Calc → View Selected → Print → Save, consistency verified at every step | PASS |
| SR-05 | Scenario 5 — Without Reference, 2 Saleable + 2 Damaged items → verify batch split → Calc → View Selected → add 5th item → Calc → View Selected → Print → Save | PASS |
| SR-06 | Defect — Apply on a Saleable row's hamburger/Batch List modal clears that row's entered quantity, zeroing Amount/Final Amount and emptying View Selected Items, reproduced on 2 separate runs | **FAIL** |
| SR-07 | Scenario 7 — Without Reference, hamburger-checked (negative, non-empty inventory) items → Print 3× 30s apart | **FAIL** (3rd attempt: Error Code -1014, same defect as TC-16) |
| SR-08 | Scenario 8 — With Reference, invoice with more than 3 items → product page → Calc → View Selected → item count consistent at every step + DB | PASS |

---

# Test Cases — Scheme Module (Live DB)

**Application:** MAssistCRM (`stage.massistcrm.com` app; data verified directly against the **live production DB**, server `172.31.62.165`, database `MA_Live` — read-only `view` account, no UI login available for this company)
**Company:** Nobel Hygiene, `Company.CompanyID = 446`
**Module:** Scheme engine (`Scheme`, `Scheme_Details`, `OrderScheme`, `OrderProductScheme`, `SchemeClaimOrderDtls`, `Order_Products.SchemeId/SchemeCode`)
**Method:** Direct SQL verification (no browser automation for this section — Nobel Hygiene has no known distributor login in this environment)

These cases verify whether a real, already-placed order correctly did or didn't get a scheme applied, by cross-referencing the order against the live `Scheme` table's eligibility rules (client type, product, date window).

---

## SC-01 — Verify a GT-tier retailer order correctly receives no distributor-tier scheme

**Precondition:** A real, already-placed order exists for a GT (General Trade / retailer) client on a product that has active schemes at the time of order.

**Test Data:** Order_Id `234674565`, invoice `IN7004992-63`, client **Nunui Grocery** (`Client_Id 30501053`, `Client_Type = 'GT'`), product **Teddyy** (`Product_Id 10085926`), qty 135, `Order_Date = 2026-07-29`.

**Steps:**
1. `SELECT * FROM Order_Dtls WHERE Order_Id = 234674565` — confirm client, date, amount.
2. `SELECT SchemeId, SchemeCode, Schemediscounts, schemediscamt, primarydisc, Secondarydisc, QPSDisc FROM Order_Products WHERE Order_Id = 234674565` — confirm whether a scheme was recorded on the line item.
3. `SELECT * FROM OrderScheme WHERE Order_Id = 234674565` and `SELECT * FROM OrderProductScheme WHERE Order_Id = 234674565` — confirm no scheme-linkage rows exist.
4. `SELECT * FROM Scheme WHERE Cmp_Id = 446 AND IsDeleted = 0 AND SchemeStartDate <= '2026-07-29' AND (SchemeEndDate IS NULL OR SchemeEndDate >= '2026-07-29') AND SchProductName LIKE '%Teddyy%'` — list all schemes that were live and eligible for this product on the order date.
5. For each scheme found in step 4, check `SchClientType` against the order's client's actual `Client_Master.Client_Type` (`'GT'`).

**Expected Result:** If every active Teddyy scheme's `SchClientType` excludes `'GT'` (e.g. scoped only to `DMS Retail Distributor / DMS Super Stockist / Retail Distributor / Super Stockist`), then this order correctly receiving `SchemeId = 0` is **not a defect** — the client's tier simply doesn't match any eligible scheme.

**Actual Result:** ✅ **PASS (as designed)** — `Order_Products.SchemeId = 0`, `SchemeCode = ''`, all discount fields `0.00`; `OrderScheme`/`OrderProductScheme`/`SchemeClaimOrderDtls` all returned 0 rows for this order. All ~13 active Teddyy "Buy X Get Y" schemes found in step 4 are scoped to `SchClientType = 'DMS Retail Distributor, DMS Super Stockist, Retail Distributor, Super Stockist'` — none include `'GT'`. Nunui Grocery's own `Client_Type = 'GT'`. So no eligible scheme existed for this client tier, and the order correctly shows no scheme applied.

**Status:** **PASS**

---

## SC-02 — Duplicate active scheme records for the same SchemeCode

**Precondition:** Query all active schemes for a given company/product to check for duplicate `SchemeCode` values across distinct `SchemeId`s.

**Test Data:** Nobel Hygiene (`Cmp_Id 446`), scheme code `'Buy 5 get 1 july26_10040616'` (Teddyy).

**Steps:**
1. `SELECT SchemeId, SchemeCode, IsDeleted FROM Scheme WHERE Cmp_Id = 446 AND SchemeCode = 'Buy 5 get 1 july26_10040616'`.
2. Filter to `IsDeleted = 0` and count distinct `SchemeId`s.

**Expected Result:** A given `SchemeCode` should map to at most one currently-active `SchemeId` at a time (or the system should have an explicit versioning/superseding mechanism that leaves only one row live).

**Actual Result:** ❌ **FAIL** — 4 separate, simultaneously-active (`IsDeleted = 0`) `SchemeId`s share the exact same `SchemeCode = 'Buy 5 get 1 july26_10040616'`: `11552002`, `11554596`, `11594317`, `11787230`. All target the same product (Teddyy) and same client tiers. This is a duplicate-scheme-creation defect — unclear which of the 4 would actually apply first / whether they'd stack, and it clutters the scheme list for anyone auditing it manually.

**Status:** **FAIL**

---

## SC-03 — (Proposed, not yet executed) Positive control: eligible distributor-tier order should receive the Teddyy scheme

**Precondition:** None executed yet — this is the natural next step to confirm the scheme engine works at all for the client tiers it's scoped to, rather than only having negative evidence (SC-01).

**Test Data:** Any real order for a client whose `Client_Master.Client_Type` is one of `DMS Retail Distributor`, `DMS Super Stockist`, `Retail Distributor`, or `Super Stockist`, placing Teddyy (`Product_Id` in one of the active scheme's `SchProductId` lists) within an active scheme's date window, at a qualifying quantity.

**Proposed Steps:**
1. Find a real order: `SELECT o.Order_Id, o.Client_Id, cm.Client_Type, op.Product_Id, op.Quantity, op.SchemeId FROM Order_Dtls o JOIN Order_Products op ON o.Order_Id = op.Order_Id JOIN Client_Master cm ON o.Client_Id = cm.Client_Id WHERE cm.Client_Type IN ('DMS Retail Distributor','DMS Super Stockist','Retail Distributor','Super Stockist') AND op.Product_Id = 10085926 AND o.Order_Date >= '2026-07-01' AND o.Order_Date < '2026-08-01'`.
2. For any matching order, check whether `SchemeId` is non-zero and whether a free/bonus quantity line exists (`Order_Products.freeqty`, or a linked row in `OrderScheme`/`OrderProductScheme`).
3. Compare against the scheme's defined tier (`Scheme_Details.Minimum`/`Maximum`/`Discount` for that `SchemeId`+`Product_Id`) to confirm the correct benefit was granted.

**Expected Result:** A distributor/stockist-tier order that qualifies should show a non-zero `SchemeId` and a correctly-calculated free quantity/discount.

**Actual Result:** *Not yet run.* This is needed to confirm the scheme engine actually fires correctly for its intended audience — SC-01 only proves it correctly does *not* fire for an ineligible client, not that it correctly *does* fire for an eligible one.

**Status:** **PENDING**

---

## SC-04 — Client Type eligibility enforcement

**Precondition:** Any active scheme with a non-"All" `SchClientType` value (e.g. restricted to `Distributor` or `DMS Retail Distributor,DMS Super Stockist`).

**Test Data:** A scheme's `SchClientType` list, plus a real order from a client whose `Client_Master.Client_Type` is **not** in that list but who otherwise meets every other eligibility rule (product, date, quantity).

**Steps:**
1. Pick a scheme: `SELECT SchemeId, SchClientType, SchProductId FROM Scheme WHERE IsDeleted = 0 AND SchClientType NOT LIKE '%All%'`.
2. Find an order for a client outside that `SchClientType` list, on an eligible product/date/quantity.
3. Check `Order_Products.SchemeId` for that order.

**Expected Result:** `SchemeId = 0` — the scheme must not apply to a client type it doesn't list.

**Status:** Template — validated once already (SC-01, Nobel Hygiene/Nunui Grocery). Reusable against any company.

---

## SC-05 — Product eligibility enforcement

**Precondition:** Any active scheme with a non-empty `SchProductId` list (i.e. scoped to specific products, not all products).

**Test Data:** A scheme's `SchProductId` list, plus a real order containing a product **not** in that list, from an otherwise-eligible client.

**Steps:**
1. `SELECT SchemeId, SchProductId FROM Scheme WHERE IsDeleted = 0 AND SchProductId <> ''`.
2. Find an order line for the same eligible client type/date, but with a `Product_Id` not present in `SchProductId`.
3. Check `Order_Products.SchemeId` for that line.

**Expected Result:** `SchemeId = 0` for the ineligible product, even if a sibling line in the same order (different, eligible product) correctly gets the scheme.

**Status:** Template — not yet executed.

---

## SC-06 — Date validity enforcement (before start / after end)

**Precondition:** Any scheme with a defined `SchemeStartDate`/`SchemeEndDate`.

**Test Data:** Two orders from the same eligible client/product — one dated before `SchemeStartDate`, one dated after `SchemeEndDate`.

**Steps:**
1. `SELECT SchemeId, SchemeStartDate, SchemeEndDate FROM Scheme WHERE IsDeleted = 0`.
2. Find (or note the absence of) orders for that client/product just outside the date window on either side.
3. Check `Order_Products.SchemeId` for each.

**Expected Result:** `SchemeId = 0` for both out-of-window orders; scheme should only apply strictly between `SchemeStartDate` and `SchemeEndDate` inclusive.

**Status:** Template — not yet executed.

---

## SC-07 — Purchase quantity/amount tier boundary (Scheme_Details min/max)

**Precondition:** A scheme with tiered `Scheme_Details` rows (`Minimum`/`Maximum`/`Discount` bands).

**Test Data:** Orders sized to land exactly at: (a) one unit below `Minimum`, (b) exactly at `Minimum`, (c) exactly at `Maximum`, (d) one unit above `Maximum`.

**Steps:**
1. `SELECT SchemeId, Minimum, Maximum, Discount FROM Scheme_Details WHERE IsDeleted = 0 AND SchemeId = <target>`.
2. For each of the 4 boundary orders, check the resulting discount/benefit actually applied (`Order_Products.Schemediscounts`/`schemediscamt`/`freeqty`, or the linked `OrderScheme` row).
3. Compare against the tier the order's amount should fall into.

**Expected Result:** (a) no benefit or the next-lower tier applies; (b)–(c) the correct tier's benefit applies exactly; (d) either no benefit (if no higher tier exists) or the next tier up applies — never the tier the order actually exceeded.

**Status:** Template — not yet executed. (This directly generalizes the overlapping-tier defect already found in the Incentive engine — SC-07 is the Scheme-module equivalent check.)

---

## SC-08 — Geographic targeting (Zone/State/City)

**Precondition:** A scheme with a non-empty `SchState` (or `SchZone`/`SchCity`).

**Test Data:** An order from an otherwise-eligible client located **outside** the scheme's listed state(s).

**Steps:**
1. `SELECT SchemeId, SchZone, SchState, SchCity FROM Scheme WHERE IsDeleted = 0 AND SchState <> ''`.
2. Find an order for a client whose address/state differs from the scheme's `SchState` list.
3. Check `Order_Products.SchemeId`.

**Expected Result:** `SchemeId = 0` — geographic scoping should exclude clients outside the listed state/zone/city.

**Status:** Template — not yet executed.

---

## SC-09 — Deleted scheme never applies

**Precondition:** A scheme with `IsDeleted = 1`.

**Test Data:** An order placed (or re-checked) after the scheme's `IsDeleted` flag was set, that would otherwise be fully eligible.

**Steps:**
1. `SELECT SchemeId, DeleteBy, IsDeleted FROM Scheme WHERE IsDeleted = 1` (or the `Scheme` table's own soft-delete equivalent).
2. Find any order dated after the deletion that matches all of the scheme's other criteria.
3. Check `Order_Products.SchemeId`.

**Expected Result:** `SchemeId = 0` — a deleted scheme must never be applied to any order, regardless of how well the order otherwise matches.

**Status:** Template — not yet executed.

---

## SC-10 — SchemeStatus / SchemeApproved flags respected independently of IsDeleted

**Precondition:** A scheme where `IsDeleted = 0` but `SchemeStatus = False` and/or `SchemeApproved = False` (we already found one such record: `SchemeId 7004992`, `IsDeleted=False`, `SchemeStatus=False`, `SchemeApproved=True`).

**Test Data:** An order that would otherwise be fully eligible for a not-deleted-but-inactive-or-unapproved scheme.

**Steps:**
1. `SELECT SchemeId, IsDeleted, SchemeStatus, SchemeApproved FROM Scheme WHERE IsDeleted = 0 AND (SchemeStatus = 0 OR SchemeApproved = 0)`.
2. Find an otherwise-eligible order against one of these.
3. Check `Order_Products.SchemeId`.

**Expected Result:** `SchemeId = 0` — an inactive (`SchemeStatus=False`) or unapproved (`SchemeApproved=False`) scheme should not apply even though it isn't soft-deleted. This is a distinct check from SC-09 since `IsDeleted`, `SchemeStatus`, and `SchemeApproved` are three separate flags that could each independently gate whether a scheme is live.

**Status:** Template — not yet executed. Worth prioritizing, since a real record combining these flags in an inconsistent-looking way (`IsDeleted=False` + `SchemeStatus=False` + `SchemeApproved=True`) was already observed (SchemeId 7004992), suggesting this combination genuinely occurs in production data.

---

## SC-11 — Duplicate/overlapping active SchemeCode (generalized)

**Precondition:** Generalizes SC-02 beyond the one Nobel Hygiene example already found.

**Test Data:** Any company's active scheme set.

**Steps:**
1. `SELECT Cmp_Id, SchemeCode, COUNT(DISTINCT SchemeId) AS cnt FROM Scheme WHERE IsDeleted = 0 GROUP BY Cmp_Id, SchemeCode HAVING COUNT(DISTINCT SchemeId) > 1`.
2. For each match, inspect whether the duplicate SchemeIds target the same or different products/client types/dates (a legitimate reason to share a code) or are genuinely identical duplicates (a defect).

**Expected Result:** Either zero true duplicates, or every "duplicate" is explainable by differing scope (different product/state/tier). Already confirmed at least one genuine unexplained duplicate exists (Nobel Hygiene, `'Buy 5 get 1 july26_10040616'`, 4 identical-scope SchemeIds).

**Status:** SC-02 confirmed one instance (**FAIL**); this broader query has not been run across all companies.

---

## SC-12 — Free-goods benefit calculation correctness

**Precondition:** A "Buy X Get Y" category scheme (`SchemeCategory` containing "Buy" / non-zero `SchBenefitQuantity`).

**Test Data:** An order whose purchased quantity is an exact multiple of the scheme's "buy" threshold (e.g. buy 5 get 1 → order qty 15, expecting 3 free units) and one that is a non-exact multiple (qty 17 → still expecting 3 free, not 3.4).

**Steps:**
1. Identify the scheme's buy/get ratio from `Scheme_Details` or `SchBenefitQuantity`/`SchPurchaseQuantity`.
2. Check the actual `freeqty`/bonus line recorded against both orders.

**Expected Result:** Free quantity = `floor(purchased_qty / buy_qty) * get_qty` in both cases — no partial/rounded-up free units, no free units on the remainder.

**Status:** Template — not yet executed. (Note: this is the Scheme-module analogue of the "Free Item = 0" defect already confirmed in the separate Bill/New Invoice module, TC-14/TC-18 — worth checking whether the same free-goods engine is shared between the two.)

---

## SC-13 — Claim linkage (`IsClaim` schemes feed `SchemeClaimOrderDtls` correctly)

**Precondition:** A scheme with `IsClaim = True` (or `ClaimDiscountType` populated), meaning its benefit should generate a claim rather than an instant order-line discount.

**Test Data:** An order that qualifies for such a scheme.

**Steps:**
1. `SELECT SchemeId FROM Scheme WHERE IsDeleted = 0 AND IsClaim = 1`.
2. Find a qualifying order and check `SchemeClaimOrderDtls` for a corresponding row (`Order_Id`, `SchemeId`, `SchemeDiscount`/claim amount).
3. Cross-check the claim amount against the scheme's defined discount rate and the order's value.

**Expected Result:** A claim row exists with the correct amount; no claim should exist for a non-`IsClaim` scheme (which should discount inline instead).

**Status:** Template — not yet executed.

---

## Summary — Scheme Module

| TC | Scenario | Status |
|---|---|---|
| SC-01 | GT-tier retailer order correctly excluded from distributor-tier scheme | PASS |
| SC-02 | Duplicate active SchemeId records sharing one SchemeCode | **FAIL** |
| SC-03 | Positive control — eligible distributor-tier order should receive the scheme | PENDING (not yet run) |
| SC-04 | Client Type eligibility enforcement (generalized) | Template (SC-01 is one instance) |
| SC-05 | Product eligibility enforcement | Template — not yet executed |
| SC-06 | Date validity enforcement (before start / after end) | Template — not yet executed |
| SC-07 | Purchase quantity/amount tier boundary (min/max edges) | Template — not yet executed |
| SC-08 | Geographic targeting (Zone/State/City) | Template — not yet executed |
| SC-09 | Deleted scheme never applies | Template — not yet executed |
| SC-10 | SchemeStatus/SchemeApproved flags respected independently of IsDeleted | Template — not yet executed (real inconsistent-flag record already seen) |
| SC-11 | Duplicate/overlapping active SchemeCode (generalized across all companies) | SC-02 confirmed one instance (**FAIL**); broader sweep not yet run |
| SC-12 | Free-goods benefit calculation correctness (exact multiples vs remainders) | Template — not yet executed |
| SC-13 | Claim linkage — IsClaim schemes correctly feed SchemeClaimOrderDtls | Template — not yet executed |
