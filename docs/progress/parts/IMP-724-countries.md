# IMP-724 · countries part (country table, time-zone choice, bbox clipping, capital fallback)

- Card: IMP-724 Normaliser, country table and minimum-places gate (Amendment A2 §6.1, §6.4, §12; 0 points)
- Part: country table, time-zone choice, bbox clipping and the capital fallback
- Run id: RUN-089 (Batch C1a, Sprint 7, inserted under IMD-215)
- Owner: Malhar (Malhar Mer)
- Status: PR_OPEN candidate on `feat/S7-C1a-any-city-foundation`
- Base commit: 08587c0 (on `main`)
- Traces to: IMD-05, IMD-128, IMD-216 (PD-A2-5 as changed); A2 §6.1, §6.4; TC-464

## Changed files

- `apps/api/app/livedata/countries.py` (create, pure): static table generated once from the IANA `zone1970.tab` (Python `tzdata` package 2026.5, IANA_VERSION 2026e, `tzdata/zoneinfo/zone1970.tab`; country names from `iso3166.tab` of the same package). The header names the source and version. `Country(code, name, currency, capital, zones)`, `ZonePoint(zone, lat, lon)`, `COUNTRIES` (read-only), `country(code)` (any case; `None` → 422 "This country is not supported yet"), `choose_timezone(code, lat, lon)` (single zone, or the nearest representative point by great-circle distance, ties by zone name), `capital(code)`, `clip_bbox(center_lat, center_lon, bbox)` (± 0.25° latitude and ± 0.25°/cos(lat) longitude, cos floored at 0.1; a dimension narrower than 0.05° or a missing box widened to ± 0.05°; the centre always inside; clamped to ±90/±180, no antimeridian wrap). Money stays two decimals (IMD-05), noted in the docstring.
- `apps/api/tests/unit/livedata/test_countries.py` (create): TC-464: every zone loads in `zoneinfo`; every country has a three-letter upper-case currency, at least one zone and a capital; coverage of `iso3166.tab` except BV and HM; nearest-point cases for US (New York, Chicago, Los Angeles, Honolulu), IN (Udaipur), RU (Moscow, Novosibirsk, Vladivostok), BR (São Paulo, Manaus), AU (Sydney, Perth); unknown code; lower-case code; capital fallback; clipping, point widening, high latitude, antimeridian, invalid centre.
- `apps/api/.importlinter`: `app.livedata.normalise` and `app.livedata.countries` added to `pure-domain`. These lines are in this commit, not in the throttle part's commit, because import-linter refuses a listed module that does not exist yet (checked by the throttle part with a scratch config), as the run prompt directs.
- `docs/progress/parts/IMP-724-countries.md` (this record).

The generator script is not in the repository. It and its reference data are kept in the operator's scratch folder for this run.

## Table summary

- 247 countries; 33 of them have more than one zone.
- BV (Bouvet Island) and HM (Heard Island and McDonald Islands) have no zone in `zone1970.tab` or `zone.tab`. They are not in the table, so they get the 422.

## Reference data for review (currency ISO 4217, capital, zone count)

AD EUR Andorra la Vella (1 zone); AE AED Abu Dhabi (1 zone); AF AFN Kabul (1 zone); AG XCD Saint John's (1 zone); AI XCD The Valley (1 zone); AL ALL Tirana (1 zone); AM AMD Yerevan (1 zone); AO AOA Luanda (1 zone); AQ USD McMurdo Station (11 zones); AR ARS Buenos Aires (12 zones); AS USD Pago Pago (1 zone); AT EUR Vienna (1 zone); AU AUD Canberra (13 zones); AW AWG Oranjestad (1 zone); AX EUR Mariehamn (1 zone); AZ AZN Baku (1 zone); BA BAM Sarajevo (1 zone); BB BBD Bridgetown (1 zone); BD BDT Dhaka (1 zone); BE EUR Brussels (1 zone); BF XOF Ouagadougou (1 zone); BG EUR Sofia (1 zone); BH BHD Manama (1 zone); BI BIF Gitega (1 zone); BJ XOF Porto-Novo (1 zone); BL EUR Gustavia (1 zone); BM BMD Hamilton (1 zone); BN BND Bandar Seri Begawan (1 zone); BO BOB Sucre (1 zone); BQ USD Kralendijk (1 zone); BR BRL Brasília (16 zones); BS BSD Nassau (1 zone); BT BTN Thimphu (1 zone); BW BWP Gaborone (1 zone); BY BYN Minsk (1 zone); BZ BZD Belmopan (1 zone); CA CAD Ottawa (23 zones); CC AUD West Island (1 zone); CD CDF Kinshasa (2 zones); CF XAF Bangui (1 zone); CG XAF Brazzaville (1 zone); CH CHF Bern (1 zone); CI XOF Yamoussoukro (1 zone); CK NZD Avarua (1 zone); CL CLP Santiago (4 zones); CM XAF Yaoundé (1 zone); CN CNY Beijing (2 zones); CO COP Bogotá (1 zone); CR CRC San José (1 zone); CU CUP Havana (1 zone); CV CVE Praia (1 zone); CW XCG Willemstad (1 zone); CX AUD Flying Fish Cove (1 zone); CY EUR Nicosia (2 zones); CZ CZK Prague (1 zone); DE EUR Berlin (2 zones); DJ DJF Djibouti (1 zone); DK DKK Copenhagen (1 zone); DM XCD Roseau (1 zone); DO DOP Santo Domingo (1 zone); DZ DZD Algiers (1 zone); EC USD Quito (2 zones); EE EUR Tallinn (1 zone); EG EGP Cairo (1 zone); EH MAD Laayoune (1 zone); ER ERN Asmara (1 zone); ES EUR Madrid (3 zones); ET ETB Addis Ababa (1 zone); FI EUR Helsinki (1 zone); FJ FJD Suva (1 zone); FK FKP Stanley (1 zone); FM USD Palikir (3 zones); FO DKK Tórshavn (1 zone); FR EUR Paris (1 zone); GA XAF Libreville (1 zone); GB GBP London (1 zone); GD XCD St. George's (1 zone); GE GEL Tbilisi (1 zone); GF EUR Cayenne (1 zone); GG GBP Saint Peter Port (1 zone); GH GHS Accra (1 zone); GI GIP Gibraltar (1 zone); GL DKK Nuuk (4 zones); GM GMD Banjul (1 zone); GN GNF Conakry (1 zone); GP EUR Basse-Terre (1 zone); GQ XAF Malabo (1 zone); GR EUR Athens (1 zone); GS GBP King Edward Point (1 zone); GT GTQ Guatemala City (1 zone); GU USD Hagåtña (1 zone); GW XOF Bissau (1 zone); GY GYD Georgetown (1 zone); HK HKD Hong Kong (1 zone); HN HNL Tegucigalpa (1 zone); HR EUR Zagreb (1 zone); HT HTG Port-au-Prince (1 zone); HU HUF Budapest (1 zone); ID IDR Jakarta (4 zones); IE EUR Dublin (1 zone); IL ILS Jerusalem (1 zone); IM GBP Douglas (1 zone); IN INR New Delhi (1 zone); IO USD Diego Garcia (1 zone); IQ IQD Baghdad (1 zone); IR IRR Tehran (1 zone); IS ISK Reykjavík (1 zone); IT EUR Rome (1 zone); JE GBP Saint Helier (1 zone); JM JMD Kingston (1 zone); JO JOD Amman (1 zone); JP JPY Tokyo (1 zone); KE KES Nairobi (1 zone); KG KGS Bishkek (1 zone); KH KHR Phnom Penh (1 zone); KI AUD South Tarawa (3 zones); KM KMF Moroni (1 zone); KN XCD Basseterre (1 zone); KP KPW Pyongyang (1 zone); KR KRW Seoul (1 zone); KW KWD Kuwait City (1 zone); KY KYD George Town (1 zone); KZ KZT Astana (7 zones); LA LAK Vientiane (1 zone); LB LBP Beirut (1 zone); LC XCD Castries (1 zone); LI CHF Vaduz (1 zone); LK LKR Sri Jayawardenepura Kotte (1 zone); LR LRD Monrovia (1 zone); LS LSL Maseru (1 zone); LT EUR Vilnius (1 zone); LU EUR Luxembourg (1 zone); LV EUR Riga (1 zone); LY LYD Tripoli (1 zone); MA MAD Rabat (1 zone); MC EUR Monaco (1 zone); MD MDL Chișinău (1 zone); ME EUR Podgorica (1 zone); MF EUR Marigot (1 zone); MG MGA Antananarivo (1 zone); MH USD Majuro (2 zones); MK MKD Skopje (1 zone); ML XOF Bamako (1 zone); MM MMK Naypyidaw (1 zone); MN MNT Ulaanbaatar (2 zones); MO MOP Macau (1 zone); MP USD Saipan (1 zone); MQ EUR Fort-de-France (1 zone); MR MRU Nouakchott (1 zone); MS XCD Brades (1 zone); MT EUR Valletta (1 zone); MU MUR Port Louis (1 zone); MV MVR Malé (1 zone); MW MWK Lilongwe (1 zone); MX MXN Mexico City (12 zones); MY MYR Kuala Lumpur (2 zones); MZ MZN Maputo (1 zone); NA NAD Windhoek (1 zone); NC XPF Nouméa (1 zone); NE XOF Niamey (1 zone); NF AUD Kingston (1 zone); NG NGN Abuja (1 zone); NI NIO Managua (1 zone); NL EUR Amsterdam (1 zone); NO NOK Oslo (1 zone); NP NPR Kathmandu (1 zone); NR AUD Yaren (1 zone); NU NZD Alofi (1 zone); NZ NZD Wellington (2 zones); OM OMR Muscat (1 zone); PA PAB Panama City (1 zone); PE PEN Lima (1 zone); PF XPF Papeete (3 zones); PG PGK Port Moresby (2 zones); PH PHP Manila (1 zone); PK PKR Islamabad (1 zone); PL PLN Warsaw (1 zone); PM EUR Saint-Pierre (1 zone); PN NZD Adamstown (1 zone); PR USD San Juan (1 zone); PS ILS Ramallah (2 zones); PT EUR Lisbon (3 zones); PW USD Ngerulmud (1 zone); PY PYG Asunción (1 zone); QA QAR Doha (1 zone); RE EUR Saint-Denis (1 zone); RO RON Bucharest (1 zone); RS RSD Belgrade (1 zone); RU RUB Moscow (27 zones); RW RWF Kigali (1 zone); SA SAR Riyadh (1 zone); SB SBD Honiara (1 zone); SC SCR Victoria (1 zone); SD SDG Khartoum (1 zone); SE SEK Stockholm (1 zone); SG SGD Singapore (1 zone); SH SHP Jamestown (1 zone); SI EUR Ljubljana (1 zone); SJ NOK Longyearbyen (1 zone); SK EUR Bratislava (1 zone); SL SLE Freetown (1 zone); SM EUR San Marino (1 zone); SN XOF Dakar (1 zone); SO SOS Mogadishu (1 zone); SR SRD Paramaribo (1 zone); SS SSP Juba (1 zone); ST STN São Tomé (1 zone); SV USD San Salvador (1 zone); SX XCG Philipsburg (1 zone); SY SYP Damascus (1 zone); SZ SZL Mbabane (1 zone); TC USD Cockburn Town (1 zone); TD XAF N'Djamena (1 zone); TF EUR Port-aux-Français (2 zones); TG XOF Lomé (1 zone); TH THB Bangkok (1 zone); TJ TJS Dushanbe (1 zone); TK NZD Fakaofo (1 zone); TL USD Dili (1 zone); TM TMT Ashgabat (1 zone); TN TND Tunis (1 zone); TO TOP Nuku'alofa (1 zone); TR TRY Ankara (1 zone); TT TTD Port of Spain (1 zone); TV AUD Funafuti (1 zone); TW TWD Taipei (1 zone); TZ TZS Dodoma (1 zone); UA UAH Kyiv (2 zones); UG UGX Kampala (1 zone); UM USD Wake Island (2 zones); US USD Washington, D.C. (29 zones); UY UYU Montevideo (1 zone); UZ UZS Tashkent (2 zones); VA EUR Vatican City (1 zone); VC XCD Kingstown (1 zone); VE VES Caracas (1 zone); VG USD Road Town (1 zone); VI USD Charlotte Amalie (1 zone); VN VND Hanoi (2 zones); VU VUV Port Vila (1 zone); WF XPF Mata-Utu (1 zone); WS WST Apia (1 zone); YE YER Sanaa (1 zone); YT EUR Mamoudzou (1 zone); ZA ZAR Pretoria (1 zone); ZM ZMW Lusaka (1 zone); ZW ZWG Harare (1 zone)

Entries most worth a second look:
- Currencies: BG → EUR (euro since 2026); CW, SX → XCG; ZW → ZWG; SL → SLE; PA → PAB (USD also legal tender); PS → ILS; AQ → USD; EH → MAD; IO, TL, BQ, EC, SV → USD; KI, NR, TV → AUD; TK, PN → NZD; GS → GBP; TF → EUR.
- Capitals: AQ McMurdo Station; BI Gitega; BO Sucre; CI Yamoussoukro; LK Sri Jayawardenepura Kotte; ZA Pretoria; IL Jerusalem; PS Ramallah; YE Sanaa; MS Brades; NR Yaren; TK Fakaofo; UM Wake Island; IO Diego Garcia; GS King Edward Point; EH Laayoune; SZ Mbabane.

## Commands

| Command | Result line |
| --- | --- |
| `make test-unit ARGS='-k countries'` | `341 passed, 1418 deselected, 1 warning in 0.70s` |
| `make test-unit ARGS='-k "countries or normalise"'` | `440 passed, 1352 deselected, 1 warning in 1.00s` |
| `ruff check` / `ruff format --check` / `mypy --strict` (the two files) | `All checks passed!` / `2 files already formatted` / `Success: no issues found in 2 source files` |
| purity check (`import app.livedata.countries`) | `[]` |

`make imports` and `make check` ran once on the branch head; result lines in the SYNC REPORT of RUN-089.

## Acceptance

- Every zone passes `zoneinfo`: **verified** (TC-464).
- Every country has a currency and a zone; money stays two decimals (IMD-05): **verified** (TC-464; no money code in this module).
- Multi-zone choice by the nearest `zone1970.tab` point: **verified** (US, IN, RU, BR, AU cases).
- The gate's capital fallback: **verified** (`capital("IN") == "New Delhi"`; used by `choose_nearby_city` of the normaliser part).

## Open issues

- BV and HM are left out (no zone data). The alternative is a stand-in entry; for the team.
- The `zoneinfo` test reads the system tz database (the API venv has no `tzdata` package). Ubuntu CI runners ship `/usr/share/zoneinfo`. A very old system tz database could lack a recent zone name.
- The currency and capital columns are typed reference data, not generated. They need the review listed above.

## Proposed decisions

none

## Blockers

none
