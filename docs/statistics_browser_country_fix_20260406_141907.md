# Statistics browser/country chart fix

Timestamp: 06/04/26 14:19 CET

## Type
FIX

## Scope
Anonymous application, Statistics module, browser/country pie chart rendering.

## Problem
Browser distribution and country distribution data were being generated and present in runtime HTML, but the UI still showed legacy disabled placeholders and the charts did not render.

## Root cause
The frontend chart renderer expected pie-chart data in array-entry form, while `browserCounts` and `countryCounts` were passed as plain JSON objects.  
Additionally, legacy placeholder text incorrectly stated that the charts were disabled.

## Exact change
Updated `templates/statistics.html` so that:
- `browserCounts` is converted with `Object.entries(...).sort(...)`
- `countryCounts` is converted with `Object.entries(...).sort(...)`
- legacy placeholder text `Browser pie chart disabled` was replaced with `Browser pie chart placeholder`
- legacy placeholder text `Country pie chart disabled` was replaced with `Country pie chart placeholder`

## Files changed
- `templates/statistics.html`

## Verification performed
1. Runtime HTML for:
   - `/statistics?range=today`
   - `/statistics?range=daily`
2. Confirmed:
   - disabled placeholder text removed
   - `browserCounts` present and non-empty
   - `countryCounts` present and non-empty
   - `browserCounts` uses `Object.entries(...)`
   - `countryCounts` uses `Object.entries(...)`
3. Visual verification in browser confirmed that both pie charts now render.

## Confidence
- Technical patch success: ~97%
- End-to-end visual success: confirmed

## Change vs Fix
This was a FIX, not cleanup.

## Risk
Low. Change is limited to the statistics template and presentation-layer data formatting.

## Lesson learned
Final HTTP 200 and presence of data in backend are not sufficient.  
Statistics UI changes must always be verified at final runtime HTML/JS contract level and in the browser.

## Follow-up items (not part of this fix)
- add regression-check procedure for Statistics to repo docs
- consider normalizing chart data format at backend level
- consider explicit JS guard for empty datasets
