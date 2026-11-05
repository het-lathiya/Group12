# Seed-data plan: the two demo destinations (IMP-115)

- Card: IMP-115 · Seed-data plan and choice of the two demo destinations (US-152)
- Plan owner: Malhar · Reviewer: Junaid
- Status: **plan recorded; review pending (IMD-120)**
- Used by: IMP-206 (curate and load destination 1, Jeel with Malhar), IMP-603 (curate and load destination 2, Junaid with Manya and Kirtan), IMP-205 (quality gate and minimum count)
- File format: [README.md](README.md) (specification §5.6)

The fields below record Malhar's plan answers, which were prepared at a desk and accepted by the operator on 5 November 2026 under IMD-120. Malhar's confirmation and Junaid's review are due before the Sprint 3 gate (SG-3). A field the answers do not cover says so; nothing is guessed.

## 1. The two destinations

Choose both by **data availability**: whether public pages exist, under a licence that allows this use, for enough places, opening hours and prices to reach the minimum usable count of section 2.

| | Destination 1 | Destination 2 |
| --- | --- | --- |
| Name | Ahmedabad (with Gandhinagar and Adalaj), Gujarat, India | Jaipur, Rajasthan, India |
| Slug (folder `data/places/<slug>/`) | `ahmedabad` (IMD-120) | Not stated in the accepted answers; to be confirmed before SG-3 (IMD-120); set by IMP-603 |
| Country code, IANA time zone, currency | IN, Asia/Kolkata, INR | IN, Asia/Kolkata, INR |
| Reason, judged by data availability | Official pages from Gujarat Tourism, the Ahmedabad Municipal Corporation heritage portal, the Sabarmati Riverfront, Gujarat Science City and Akshardham Gandhinagar publish descriptions, timings and ticket prices. It is a UNESCO World Heritage City, and it is close to our college in Gandhinagar, so the team can check places in person. | Its main monuments (Amer Fort, Hawa Mahal, Jantar Mantar, City Palace and others) have official tourism pages with timings and ticket prices, and it is one of the best documented Indian destinations. |

Evidence for the reason, one row per destination. Count only what the listed sources actually show; do not estimate.

| Data availability evidence | Destination 1 | Destination 2 |
| --- | --- | --- |
| Places with a public source, roughly counted | 103 places remain after the desk check (section 2) | Not stated in the accepted answers; to be confirmed before SG-3 (IMD-120) |
| Of those, places with opening hours on a public page | Not stated in the accepted answers; to be confirmed before SG-3 (IMD-120) | Not stated in the accepted answers; to be confirmed before SG-3 (IMD-120) |
| Of those, places with prices on a public page | Not stated in the accepted answers; to be confirmed before SG-3 (IMD-120) | None yet: Incredible India gives no prices, and monument ticket rates stay `unavailable` until the IMP-603 owners take them from the department's notice (section 4) |
| Food places (the meal slots of every day need them) | Not stated in the accepted answers; to be confirmed before SG-3 (IMD-120) | Not stated in the accepted answers; to be confirmed before SG-3 (IMD-120) |
| Spread over the categories (sight, museum, nature, food, shopping, entertainment, religious, activity) | Not stated in the accepted answers; to be confirmed before SG-3 (IMD-120) | Not stated in the accepted answers; to be confirmed before SG-3 (IMD-120) |
| Licences allow entering the facts in this repository | Official and secondary pages: All rights reserved (facts only); Wikipedia: CC BY-SA 4.0; OpenStreetMap: ODbL 1.0 (coordinate checks only) | Official pages: All rights reserved (facts only); OpenStreetMap: ODbL 1.0 |
| Other candidates considered and why not chosen | Not stated in the accepted answers; to be confirmed before SG-3 (IMD-120) | Not stated in the accepted answers; to be confirmed before SG-3 (IMD-120) |

## 2. Minimum usable-place count

A usable place passes the quality gate (IMP-205): it has a known source with licence and retrieved date, a verification status, coordinates inside the bounding box, an allowed category and a duration of 15 to 480 minutes. Hours and prices may be `unavailable`.

| | Destination 1 | Destination 2 |
| --- | --- | --- |
| Figure given by the card and the specification | 100 (IMP-115, IMP-206; §5.6 "curated about 100", AS-06) | No card figure; §5.6 says "curated about 100" |
| Team decision: confirmed, or a lower figure | 100, as the card says. After the desk check of 5 November 2026 (IMD-120), 103 places remain, 43 of them curated_checked; see data/places/ahmedabad/verification_log.md once IMP-206 is merged. | Not stated in the accepted answers; to be confirmed before SG-3 (IMD-120); set by IMP-603 |
| Reason, if lower than 100 | Not lower | Not stated in the accepted answers; to be confirmed before SG-3 (IMD-120) |

## 3. One-city fallback if destination 2 slips

| Item | Decision |
| --- | --- |
| When destination 2 counts as slipped (date or condition) | Not stated in the accepted answers; to be confirmed before SG-3 (IMD-120) |
| What the demo and the gates use instead | Demo destination 1 only |
| What happens to destination 2 data already entered | Not stated in the accepted answers; to be confirmed before SG-3 (IMD-120) |
| Who decides that the fallback applies | Not stated in the accepted answers; to be confirmed before SG-3 (IMD-120) |

## 4. Sources per destination

One row per source, which becomes one row of that destination's `sources.csv`.

**Fields provided:** list the `places.csv` and `opening_hours.csv` columns the source gives, for example `name`, `lat`/`lon`, hours or prices.

**How facts are recorded:** describe who enters the facts, how the curator reads them from the page, which label (`curated` or `estimate`) and which `verification_status` they get, and where the checked-on date goes.

`source_type` is one of `curated_manual`, `osm_import`, `official_site`, `estimate` or `other`.

### Destination 1: Ahmedabad

| Source name | URL | Licence | `source_type` | Fields it provides | How facts are recorded |
| --- | --- | --- | --- | --- | --- |
| Gujarat Tourism | https://www.gujarattourism.com/ | All rights reserved (facts only) | `official_site` | Descriptions, timings and fees where stated | Entered from the page cited per row, desk-checked against it (IMD-120); hours a page states without weekdays are labelled `estimate`, others `curated`; unsupported hours or prices are `unavailable`; `verification_status` is `curated_checked` only where all facts were confirmed, else `unverified`; the checked-on date is the source's retrieved date |
| AMC Heritage Ahmedabad | https://heritage.ahmedabadcity.gov.in/ | All rights reserved (facts only) | `official_site` | Monuments, gates, stepwells and the Heritage Walk | Entered from the page cited per row, desk-checked against it (IMD-120); hours a page states without weekdays are labelled `estimate`, others `curated`; unsupported hours or prices are `unavailable`; `verification_status` is `curated_checked` only where all facts were confirmed, else `unverified`; the checked-on date is the source's retrieved date |
| Sabarmati Riverfront | https://sabarmatiriverfront.com/ | All rights reserved (facts only) | `official_site` | Timings and tickets for Atal Bridge, Flower Park and the riverfront parks | Entered from the page cited per row, desk-checked against it (IMD-120); hours a page states without weekdays are labelled `estimate`, others `curated`; unsupported hours or prices are `unavailable`; `verification_status` is `curated_checked` only where all facts were confirmed, else `unverified`; the checked-on date is the source's retrieved date |
| Gujarat Science City | https://sciencecity.gujarat.gov.in/fees-timing | All rights reserved (facts only) | `official_site` | Timings and ticket prices | Entered from the page cited per row, desk-checked against it (IMD-120); hours a page states without weekdays are labelled `estimate`, others `curated`; unsupported hours or prices are `unavailable`; `verification_status` is `curated_checked` only where all facts were confirmed, else `unverified`; the checked-on date is the source's retrieved date |
| Akshardham Gandhinagar | https://akshardham.com/gujarat/visitor-info | All rights reserved (facts only) | `official_site` | Timings and show/exhibition tickets | Entered from the page cited per row, desk-checked against it (IMD-120); hours a page states without weekdays are labelled `estimate`, others `curated`; unsupported hours or prices are `unavailable`; `verification_status` is `curated_checked` only where all facts were confirmed, else `unverified`; the checked-on date is the source's retrieved date |
| Incredible India (Ministry of Tourism) | https://www.incredibleindia.gov.in/ | All rights reserved (facts only) | `official_site` | Descriptions | Entered from the page cited per row, desk-checked against it (IMD-120); hours a page states without weekdays are labelled `estimate`, others `curated`; unsupported hours or prices are `unavailable`; `verification_status` is `curated_checked` only where all facts were confirmed, else `unverified`; the checked-on date is the source's retrieved date |
| OpenStreetMap | https://www.openstreetmap.org/ | ODbL 1.0, attribution "© OpenStreetMap contributors" | not a `sources.csv` row | Used during review to check coordinates | Coordinates are compared with the map during review |
| Wikipedia (CC BY-SA 4.0) and some secondary pages (news, listings) | One per row in `sources.csv` | CC BY-SA 4.0 (Wikipedia); secondary pages per row | `other` | Used where no official page gave a fact | Entered from the page cited per row, desk-checked against it (IMD-120); hours a page states without weekdays are labelled `estimate`, others `curated`; unsupported hours or prices are `unavailable`; `verification_status` is `curated_checked` only where all facts were confirmed, else `unverified`; the checked-on date is the source's retrieved date; each one is a row in `sources.csv` with `source_type` `other` |

### Destination 2: Jaipur

| Source name | URL | Licence | `source_type` | Fields it provides | How facts are recorded |
| --- | --- | --- | --- | --- | --- |
| Incredible India (Ministry of Tourism) | https://www.incredibleindia.gov.in/en/rajasthan/jaipur | All rights reserved (facts only) | `official_site` | Pages for Amber Fort, Hawa Mahal, Jantar Mantar, City Palace, Albert Hall Museum and Nahargarh Fort: descriptions and timings, but no prices | Entered from the page cited per row, desk-checked against it (IMD-120); hours a page states without weekdays are labelled `estimate`, others `curated`; unsupported hours or prices are `unavailable`; `verification_status` is `curated_checked` only where all facts were confirmed, else `unverified`; the checked-on date is the source's retrieved date |
| Rajasthan Tourism (Govt. of Rajasthan) | http://www.tourism.rajasthan.gov.in/ | All rights reserved (facts only) | `official_site` | The official department site, as listed on india.gov.in: descriptions and visitor information | Entered from the page cited per row, desk-checked against it (IMD-120); hours a page states without weekdays are labelled `estimate`, others `curated`; unsupported hours or prices are `unavailable`; `verification_status` is `curated_checked` only where all facts were confirmed, else `unverified`; the checked-on date is the source's retrieved date |
| Department of Archaeology and Museums, Govt. of Rajasthan | https://museumsrajasthan.gov.in | All rights reserved (facts only) | `official_site` | Runs the Jaipur monuments and their e-ticketing; monument ticket rates were revised from 1 January 2026 | The IMP-603 owners (Junaid, Manya) take the current rates from the department's official notice or the monument ticket counter; until then prices stay `unavailable` |
| OpenStreetMap | https://www.openstreetmap.org/ | ODbL 1.0, attribution "© OpenStreetMap contributors" | not a `sources.csv` row | Used during review to check coordinates | Coordinates are compared with the map during review |

Add rows as needed. A fact whose source is not in this table is not entered.

## 5. Unavailable, never guessed (PR-02)

Confirmed in the plan answers: a fact that cannot be sourced stays "unavailable" and is never guessed (PR-02).

This rule is stated as the specification and the task register give it:

- "Facts that cannot be sourced stay unavailable" (IMP-115 step 2, PR-02).
- "Enter hours and price ranges only from official or public pages named in sources.csv; mark everything else unavailable; never fill a fact from memory or from an AI assistant" (IMP-206 step 2).
- "Curated data under `data/places/<slug>/` is entered by people from the named public pages, never from memory or from a model" (§5.6).
- Unavailable means "Unknown; never shown as zero and never treated as closed" (§9.2). "Unknown hours are never treated as open or closed" (DR-09).

In the files: an unsourced price leaves `price_min`, `price_max` and `price_currency` empty with `price_label` `unavailable`. Unsourced hours mean no rows in `opening_hours.csv`, which the seed stores as `hours_label` `unavailable`. Unknown suitability is left empty, never `false`. See the curator checklist in [README.md](README.md).

## 6. Review by Junaid

| Item | Result |
| --- | --- |
| Review date | Pending. Recorded as due before the Sprint 3 gate (IMD-120). |
| Outcome (approved, or changes requested with the list) | Pending. Recorded as due before the Sprint 3 gate (IMD-120). |
| Changes made after the review | Pending. Recorded as due before the Sprint 3 gate (IMD-120). |
| Decision record | [docs/decisions/destinations.md](../../docs/decisions/destinations.md) |
