# MVP label review · RUN-069

Owner: Manasvi Rathore. Date: 14 November 2026. Scope: IMP-507 steps 3–5, FR-117 / TC-282 / TC-385, IMD-130 and IMD-172.

| Screen | Values and labels | Changes / evidence |
| --- | --- | --- |
| Explore | PlaceCard already labels prices and hours; no hours timestamps exist in PlaceSummary, so no date is invented. Source name is returned by API-16. | No missing displayed-value label found. Existing PlaceCard tests cover prices/hours and unavailable data. No file change needed. |
| Place detail | API-17 and PlaceDetailDrawer are not built (IMP-604); no hours/time/price value is displayed on this absent screen. | Pending IMP-604. No new screen built in this part; future curated hour values must pass hours_checked_on to SourceBadge. |
| Itinerary | Item costs already carry SourceBadge and travel carries the exact routing/distance wording. Added SourceBadge for item.place.hours_label. The API item has no hours check date or opening intervals, so none is invented. Themes/notes keep AiBadge. | apps/web/components/itinerary/ItineraryItemCard.tsx; existing cost label and AiBadge tests now explicitly check both curated price and hours badges. |
| Costs | Planning total, estimate range, per-traveller amount, contingency and daily rows carry Estimate. Category rows use server labels; allowances show Traveller input; unavailable category amounts are hidden. Incomplete estimates have a visible note. | costs/page.tsx; CostBreakdown.tsx; SourceBadge.tsx adds Traveller input; CostBreakdown tests verify labels and shared edit refetch. Day rows follow §6.5 with a separate contingency_share; no per-day label field is invented. |
| Summary | API-35 and the summary screen are not built (IMP-609); no values are displayed there. | Pending IMP-609; re-use the same labelled item and cost components when built. |

No displayed value in the reviewed built screens is missing its source label. No screen claims live or externally verified prices, hours or travel. Prices marked Curated have no date (IMD-130); curated hours carry a date only when returned by the API. No client adds amounts, computes times or estimates travel.

Verification: automated component tests and source review. Live local-stack screenshots and full visual TC-385 review remain not verified: local stack — member to add. Place-detail and summary completion remain with their future cards; this review does not claim those screens are implemented.
