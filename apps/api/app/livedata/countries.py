"""Country table, time-zone choice, bbox clipping and capital fallback (A2 §6.1, §6.4; IMD-216).

Pure reference data and pure functions: no I/O, no framework, no database.

* ``country(code)`` returns the :class:`Country` for an ISO 3166-1 alpha-2 code (any case), or
  ``None``; the caller turns ``None`` into 422 "This country is not supported yet".
* ``choose_timezone(code, lat, lon)``: a single-zone country uses its zone; a multi-zone country
  takes the zone whose ``zone1970.tab`` representative point is nearest (great-circle distance)
  to the settlement centre, ties broken by zone name.
* ``capital(code)`` names the country's capital (for a territory, its main settlement), used as
  the ``nearby_city`` fallback of the insufficient-data gate (A2 §6.4).
* ``clip_bbox(center_lat, center_lon, bbox)`` caps a Nominatim box around the centre.

Currency is the ISO 4217 code in current use. Money keeps two decimals (IMD-05): zero-decimal
currencies (for example JPY, KRW) are shown with ``.00`` and three-decimal currencies (for
example KWD, BHD, OMR) are rounded to two decimals. This is a recorded limitation; live places
carry no prices.

Data sources. The table below was generated once and is committed as static data (IMD-216);
it is not regenerated at runtime and nothing here reads a tz file.

* Zones and representative points: IANA tz database ``zone1970.tab`` from the Python ``tzdata``
  package 2026.5 (IANA_VERSION 2026e), ``tzdata/zoneinfo/zone1970.tab``. Each line's ISO 6709
  coordinates were converted to decimal degrees (4 places); a zone listed for several country
  codes counts for each of them.
* Country names: ``iso3166.tab`` of the same package (identical to macOS
  ``/usr/share/zoneinfo/iso3166.tab``, tz 2026f), with the typographic apostrophe of CI
  written as an ASCII apostrophe.
* Every ISO 3166-1 code of ``iso3166.tab`` has a zone in ``zone1970.tab`` except BV (Bouvet
  Island) and HM (Heard Island & McDonald Islands), which are uninhabited and have no zone in
  ``zone.tab`` either, so they are absent (247 of 249 codes).
* Currency and capital: reference data typed per country code.

Bbox rule (A2 §6.1), applied per dimension around the centre:

1. The box is cut to at most ``MAX_HALF_SPAN_DEG`` (0.25°) of latitude and
   ``MAX_HALF_SPAN_DEG / cos(lat)`` of longitude either side of the centre (about 28 km);
   ``cos(lat)`` is floored at ``MIN_COS_LAT`` (0.1, about 84°) so the longitude span stays finite
   near the poles.
2. The box is extended, if needed, so that it contains the centre.
3. Point-like: a dimension whose span is below ``POINT_HALF_SPAN_DEG`` (0.05°), or a missing box,
   becomes centre ± 0.05° in that dimension.
4. The result is clamped to latitude [-90, 90] and longitude [-180, 180]. A box that would cross
   the antimeridian is clamped at ±180 rather than wrapped.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from app.livedata.providers.base import BBox

MAX_HALF_SPAN_DEG = 0.25
POINT_HALF_SPAN_DEG = 0.05
MIN_COS_LAT = 0.1
_EARTH_RADIUS_KM = 6371.0088


@dataclass(frozen=True)
class ZonePoint:
    """An IANA zone and its ``zone1970.tab`` representative point in decimal degrees."""

    zone: str
    lat: float
    lon: float


@dataclass(frozen=True)
class Country:
    """One ISO 3166-1 country or territory."""

    code: str
    name: str
    currency: str
    capital: str
    zones: tuple[ZonePoint, ...]


_Row = tuple[str, str, str, str, tuple[tuple[str, float, float], ...]]

_ROWS: tuple[_Row, ...] = (
    ("AD", "Andorra", "EUR", "Andorra la Vella", (("Europe/Andorra", 42.5, 1.5167),)),
    ("AE", "United Arab Emirates", "AED", "Abu Dhabi", (("Asia/Dubai", 25.3, 55.3),)),
    ("AF", "Afghanistan", "AFN", "Kabul", (("Asia/Kabul", 34.5167, 69.2),)),
    (
        "AG",
        "Antigua & Barbuda",
        "XCD",
        "Saint John's",
        (("America/Puerto_Rico", 18.4683, -66.1061),),
    ),
    ("AI", "Anguilla", "XCD", "The Valley", (("America/Puerto_Rico", 18.4683, -66.1061),)),
    ("AL", "Albania", "ALL", "Tirana", (("Europe/Tirane", 41.3333, 19.8333),)),
    ("AM", "Armenia", "AMD", "Yerevan", (("Asia/Yerevan", 40.1833, 44.5),)),
    ("AO", "Angola", "AOA", "Luanda", (("Africa/Lagos", 6.45, 3.4),)),
    (
        "AQ",
        "Antarctica",
        "USD",
        "McMurdo Station",
        (
            ("Antarctica/Casey", -66.2833, 110.5167),
            ("Antarctica/Davis", -68.5833, 77.9667),
            ("Antarctica/Mawson", -67.6, 62.8833),
            ("Antarctica/Palmer", -64.8, -64.1),
            ("Antarctica/Rothera", -67.5667, -68.1333),
            ("Antarctica/Troll", -72.0114, 2.535),
            ("Antarctica/Vostok", -78.4, 106.9),
            ("Asia/Riyadh", 24.6333, 46.7167),
            ("Asia/Singapore", 1.2833, 103.85),
            ("Pacific/Auckland", -36.8667, 174.7667),
            ("Pacific/Port_Moresby", -9.5, 147.1667),
        ),
    ),
    (
        "AR",
        "Argentina",
        "ARS",
        "Buenos Aires",
        (
            ("America/Argentina/Buenos_Aires", -34.6, -58.45),
            ("America/Argentina/Catamarca", -28.4667, -65.7833),
            ("America/Argentina/Cordoba", -31.4, -64.1833),
            ("America/Argentina/Jujuy", -24.1833, -65.3),
            ("America/Argentina/La_Rioja", -29.4333, -66.85),
            ("America/Argentina/Mendoza", -32.8833, -68.8167),
            ("America/Argentina/Rio_Gallegos", -51.6333, -69.2167),
            ("America/Argentina/Salta", -24.7833, -65.4167),
            ("America/Argentina/San_Juan", -31.5333, -68.5167),
            ("America/Argentina/San_Luis", -33.3167, -66.35),
            ("America/Argentina/Tucuman", -26.8167, -65.2167),
            ("America/Argentina/Ushuaia", -54.8, -68.3),
        ),
    ),
    ("AS", "Samoa (American)", "USD", "Pago Pago", (("Pacific/Pago_Pago", -14.2667, -170.7),)),
    ("AT", "Austria", "EUR", "Vienna", (("Europe/Vienna", 48.2167, 16.3333),)),
    (
        "AU",
        "Australia",
        "AUD",
        "Canberra",
        (
            ("Antarctica/Macquarie", -54.5, 158.95),
            ("Asia/Tokyo", 35.6544, 139.7447),
            ("Australia/Adelaide", -34.9167, 138.5833),
            ("Australia/Brisbane", -27.4667, 153.0333),
            ("Australia/Broken_Hill", -31.95, 141.45),
            ("Australia/Darwin", -12.4667, 130.8333),
            ("Australia/Eucla", -31.7167, 128.8667),
            ("Australia/Hobart", -42.8833, 147.3167),
            ("Australia/Lindeman", -20.2667, 149.0),
            ("Australia/Lord_Howe", -31.55, 159.0833),
            ("Australia/Melbourne", -37.8167, 144.9667),
            ("Australia/Perth", -31.95, 115.85),
            ("Australia/Sydney", -33.8667, 151.2167),
        ),
    ),
    ("AW", "Aruba", "AWG", "Oranjestad", (("America/Puerto_Rico", 18.4683, -66.1061),)),
    ("AX", "Åland Islands", "EUR", "Mariehamn", (("Europe/Helsinki", 60.1667, 24.9667),)),
    ("AZ", "Azerbaijan", "AZN", "Baku", (("Asia/Baku", 40.3833, 49.85),)),
    ("BA", "Bosnia & Herzegovina", "BAM", "Sarajevo", (("Europe/Belgrade", 44.8333, 20.5),)),
    ("BB", "Barbados", "BBD", "Bridgetown", (("America/Barbados", 13.1, -59.6167),)),
    ("BD", "Bangladesh", "BDT", "Dhaka", (("Asia/Dhaka", 23.7167, 90.4167),)),
    ("BE", "Belgium", "EUR", "Brussels", (("Europe/Brussels", 50.8333, 4.3333),)),
    ("BF", "Burkina Faso", "XOF", "Ouagadougou", (("Africa/Abidjan", 5.3167, -4.0333),)),
    ("BG", "Bulgaria", "EUR", "Sofia", (("Europe/Sofia", 42.6833, 23.3167),)),
    ("BH", "Bahrain", "BHD", "Manama", (("Asia/Qatar", 25.2833, 51.5333),)),
    ("BI", "Burundi", "BIF", "Gitega", (("Africa/Maputo", -25.9667, 32.5833),)),
    ("BJ", "Benin", "XOF", "Porto-Novo", (("Africa/Lagos", 6.45, 3.4),)),
    ("BL", "St Barthelemy", "EUR", "Gustavia", (("America/Puerto_Rico", 18.4683, -66.1061),)),
    ("BM", "Bermuda", "BMD", "Hamilton", (("Atlantic/Bermuda", 32.2833, -64.7667),)),
    ("BN", "Brunei", "BND", "Bandar Seri Begawan", (("Asia/Kuching", 1.55, 110.3333),)),
    ("BO", "Bolivia", "BOB", "Sucre", (("America/La_Paz", -16.5, -68.15),)),
    ("BQ", "Caribbean NL", "USD", "Kralendijk", (("America/Puerto_Rico", 18.4683, -66.1061),)),
    (
        "BR",
        "Brazil",
        "BRL",
        "Brasília",
        (
            ("America/Araguaina", -7.2, -48.2),
            ("America/Bahia", -12.9833, -38.5167),
            ("America/Belem", -1.45, -48.4833),
            ("America/Boa_Vista", 2.8167, -60.6667),
            ("America/Campo_Grande", -20.45, -54.6167),
            ("America/Cuiaba", -15.5833, -56.0833),
            ("America/Eirunepe", -6.6667, -69.8667),
            ("America/Fortaleza", -3.7167, -38.5),
            ("America/Maceio", -9.6667, -35.7167),
            ("America/Manaus", -3.1333, -60.0167),
            ("America/Noronha", -3.85, -32.4167),
            ("America/Porto_Velho", -8.7667, -63.9),
            ("America/Recife", -8.05, -34.9),
            ("America/Rio_Branco", -9.9667, -67.8),
            ("America/Santarem", -2.4333, -54.8667),
            ("America/Sao_Paulo", -23.5333, -46.6167),
        ),
    ),
    ("BS", "Bahamas", "BSD", "Nassau", (("America/Toronto", 43.65, -79.3833),)),
    ("BT", "Bhutan", "BTN", "Thimphu", (("Asia/Thimphu", 27.4667, 89.65),)),
    ("BW", "Botswana", "BWP", "Gaborone", (("Africa/Maputo", -25.9667, 32.5833),)),
    ("BY", "Belarus", "BYN", "Minsk", (("Europe/Minsk", 53.9, 27.5667),)),
    ("BZ", "Belize", "BZD", "Belmopan", (("America/Belize", 17.5, -88.2),)),
    (
        "CA",
        "Canada",
        "CAD",
        "Ottawa",
        (
            ("America/Cambridge_Bay", 69.1139, -105.0528),
            ("America/Dawson", 64.0667, -139.4167),
            ("America/Dawson_Creek", 55.7667, -120.2333),
            ("America/Edmonton", 53.55, -113.4667),
            ("America/Fort_Nelson", 58.8, -122.7),
            ("America/Glace_Bay", 46.2, -59.95),
            ("America/Goose_Bay", 53.3333, -60.4167),
            ("America/Halifax", 44.65, -63.6),
            ("America/Inuvik", 68.3497, -133.7167),
            ("America/Iqaluit", 63.7333, -68.4667),
            ("America/Moncton", 46.1, -64.7833),
            ("America/Panama", 8.9667, -79.5333),
            ("America/Phoenix", 33.4483, -112.0733),
            ("America/Puerto_Rico", 18.4683, -66.1061),
            ("America/Rankin_Inlet", 62.8167, -92.0831),
            ("America/Regina", 50.4, -104.65),
            ("America/Resolute", 74.6956, -94.8292),
            ("America/St_Johns", 47.5667, -52.7167),
            ("America/Swift_Current", 50.2833, -107.8333),
            ("America/Toronto", 43.65, -79.3833),
            ("America/Vancouver", 49.2667, -123.1167),
            ("America/Whitehorse", 60.7167, -135.05),
            ("America/Winnipeg", 49.8833, -97.15),
        ),
    ),
    ("CC", "Cocos (Keeling) Islands", "AUD", "West Island", (("Asia/Yangon", 16.7833, 96.1667),)),
    (
        "CD",
        "Congo (Dem. Rep.)",
        "CDF",
        "Kinshasa",
        (("Africa/Lagos", 6.45, 3.4), ("Africa/Maputo", -25.9667, 32.5833)),
    ),
    ("CF", "Central African Rep.", "XAF", "Bangui", (("Africa/Lagos", 6.45, 3.4),)),
    ("CG", "Congo (Rep.)", "XAF", "Brazzaville", (("Africa/Lagos", 6.45, 3.4),)),
    ("CH", "Switzerland", "CHF", "Bern", (("Europe/Zurich", 47.3833, 8.5333),)),
    ("CI", "Côte d'Ivoire", "XOF", "Yamoussoukro", (("Africa/Abidjan", 5.3167, -4.0333),)),
    ("CK", "Cook Islands", "NZD", "Avarua", (("Pacific/Rarotonga", -21.2333, -159.7667),)),
    (
        "CL",
        "Chile",
        "CLP",
        "Santiago",
        (
            ("America/Coyhaique", -45.5667, -72.0667),
            ("America/Punta_Arenas", -53.15, -70.9167),
            ("America/Santiago", -33.45, -70.6667),
            ("Pacific/Easter", -27.15, -109.4333),
        ),
    ),
    ("CM", "Cameroon", "XAF", "Yaoundé", (("Africa/Lagos", 6.45, 3.4),)),
    (
        "CN",
        "China",
        "CNY",
        "Beijing",
        (("Asia/Shanghai", 31.2333, 121.4667), ("Asia/Urumqi", 43.8, 87.5833)),
    ),
    ("CO", "Colombia", "COP", "Bogotá", (("America/Bogota", 4.6, -74.0833),)),
    ("CR", "Costa Rica", "CRC", "San José", (("America/Costa_Rica", 9.9333, -84.0833),)),
    ("CU", "Cuba", "CUP", "Havana", (("America/Havana", 23.1333, -82.3667),)),
    ("CV", "Cape Verde", "CVE", "Praia", (("Atlantic/Cape_Verde", 14.9167, -23.5167),)),
    ("CW", "Curaçao", "XCG", "Willemstad", (("America/Puerto_Rico", 18.4683, -66.1061),)),
    ("CX", "Christmas Island", "AUD", "Flying Fish Cove", (("Asia/Bangkok", 13.75, 100.5167),)),
    (
        "CY",
        "Cyprus",
        "EUR",
        "Nicosia",
        (("Asia/Famagusta", 35.1167, 33.95), ("Asia/Nicosia", 35.1667, 33.3667)),
    ),
    ("CZ", "Czech Republic", "CZK", "Prague", (("Europe/Prague", 50.0833, 14.4333),)),
    (
        "DE",
        "Germany",
        "EUR",
        "Berlin",
        (("Europe/Berlin", 52.5, 13.3667), ("Europe/Zurich", 47.3833, 8.5333)),
    ),
    ("DJ", "Djibouti", "DJF", "Djibouti", (("Africa/Nairobi", -1.2833, 36.8167),)),
    ("DK", "Denmark", "DKK", "Copenhagen", (("Europe/Berlin", 52.5, 13.3667),)),
    ("DM", "Dominica", "XCD", "Roseau", (("America/Puerto_Rico", 18.4683, -66.1061),)),
    (
        "DO",
        "Dominican Republic",
        "DOP",
        "Santo Domingo",
        (("America/Santo_Domingo", 18.4667, -69.9),),
    ),
    ("DZ", "Algeria", "DZD", "Algiers", (("Africa/Algiers", 36.7833, 3.05),)),
    (
        "EC",
        "Ecuador",
        "USD",
        "Quito",
        (("America/Guayaquil", -2.1667, -79.8333), ("Pacific/Galapagos", -0.9, -89.6)),
    ),
    ("EE", "Estonia", "EUR", "Tallinn", (("Europe/Tallinn", 59.4167, 24.75),)),
    ("EG", "Egypt", "EGP", "Cairo", (("Africa/Cairo", 30.05, 31.25),)),
    ("EH", "Western Sahara", "MAD", "Laayoune", (("Africa/El_Aaiun", 27.15, -13.2),)),
    ("ER", "Eritrea", "ERN", "Asmara", (("Africa/Nairobi", -1.2833, 36.8167),)),
    (
        "ES",
        "Spain",
        "EUR",
        "Madrid",
        (
            ("Africa/Ceuta", 35.8833, -5.3167),
            ("Atlantic/Canary", 28.1, -15.4),
            ("Europe/Madrid", 40.4, -3.6833),
        ),
    ),
    ("ET", "Ethiopia", "ETB", "Addis Ababa", (("Africa/Nairobi", -1.2833, 36.8167),)),
    ("FI", "Finland", "EUR", "Helsinki", (("Europe/Helsinki", 60.1667, 24.9667),)),
    ("FJ", "Fiji", "FJD", "Suva", (("Pacific/Fiji", -18.1333, 178.4167),)),
    ("FK", "Falkland Islands", "FKP", "Stanley", (("Atlantic/Stanley", -51.7, -57.85),)),
    (
        "FM",
        "Micronesia",
        "USD",
        "Palikir",
        (
            ("Pacific/Guadalcanal", -9.5333, 160.2),
            ("Pacific/Kosrae", 5.3167, 162.9833),
            ("Pacific/Port_Moresby", -9.5, 147.1667),
        ),
    ),
    ("FO", "Faroe Islands", "DKK", "Tórshavn", (("Atlantic/Faroe", 62.0167, -6.7667),)),
    ("FR", "France", "EUR", "Paris", (("Europe/Paris", 48.8667, 2.3333),)),
    ("GA", "Gabon", "XAF", "Libreville", (("Africa/Lagos", 6.45, 3.4),)),
    ("GB", "Britain (UK)", "GBP", "London", (("Europe/London", 51.5083, -0.1253),)),
    ("GD", "Grenada", "XCD", "St. George's", (("America/Puerto_Rico", 18.4683, -66.1061),)),
    ("GE", "Georgia", "GEL", "Tbilisi", (("Asia/Tbilisi", 41.7167, 44.8167),)),
    ("GF", "French Guiana", "EUR", "Cayenne", (("America/Cayenne", 4.9333, -52.3333),)),
    ("GG", "Guernsey", "GBP", "Saint Peter Port", (("Europe/London", 51.5083, -0.1253),)),
    ("GH", "Ghana", "GHS", "Accra", (("Africa/Abidjan", 5.3167, -4.0333),)),
    ("GI", "Gibraltar", "GIP", "Gibraltar", (("Europe/Gibraltar", 36.1333, -5.35),)),
    (
        "GL",
        "Greenland",
        "DKK",
        "Nuuk",
        (
            ("America/Danmarkshavn", 76.7667, -18.6667),
            ("America/Nuuk", 64.1833, -51.7333),
            ("America/Scoresbysund", 70.4833, -21.9667),
            ("America/Thule", 76.5667, -68.7833),
        ),
    ),
    ("GM", "Gambia", "GMD", "Banjul", (("Africa/Abidjan", 5.3167, -4.0333),)),
    ("GN", "Guinea", "GNF", "Conakry", (("Africa/Abidjan", 5.3167, -4.0333),)),
    ("GP", "Guadeloupe", "EUR", "Basse-Terre", (("America/Puerto_Rico", 18.4683, -66.1061),)),
    ("GQ", "Equatorial Guinea", "XAF", "Malabo", (("Africa/Lagos", 6.45, 3.4),)),
    ("GR", "Greece", "EUR", "Athens", (("Europe/Athens", 37.9667, 23.7167),)),
    (
        "GS",
        "South Georgia & the South Sandwich Islands",
        "GBP",
        "King Edward Point",
        (("Atlantic/South_Georgia", -54.2667, -36.5333),),
    ),
    ("GT", "Guatemala", "GTQ", "Guatemala City", (("America/Guatemala", 14.6333, -90.5167),)),
    ("GU", "Guam", "USD", "Hagåtña", (("Pacific/Guam", 13.4667, 144.75),)),
    ("GW", "Guinea-Bissau", "XOF", "Bissau", (("Africa/Bissau", 11.85, -15.5833),)),
    ("GY", "Guyana", "GYD", "Georgetown", (("America/Guyana", 6.8, -58.1667),)),
    ("HK", "Hong Kong", "HKD", "Hong Kong", (("Asia/Hong_Kong", 22.2833, 114.15),)),
    ("HN", "Honduras", "HNL", "Tegucigalpa", (("America/Tegucigalpa", 14.1, -87.2167),)),
    ("HR", "Croatia", "EUR", "Zagreb", (("Europe/Belgrade", 44.8333, 20.5),)),
    ("HT", "Haiti", "HTG", "Port-au-Prince", (("America/Port-au-Prince", 18.5333, -72.3333),)),
    ("HU", "Hungary", "HUF", "Budapest", (("Europe/Budapest", 47.5, 19.0833),)),
    (
        "ID",
        "Indonesia",
        "IDR",
        "Jakarta",
        (
            ("Asia/Jakarta", -6.1667, 106.8),
            ("Asia/Jayapura", -2.5333, 140.7),
            ("Asia/Makassar", -5.1167, 119.4),
            ("Asia/Pontianak", -0.0333, 109.3333),
        ),
    ),
    ("IE", "Ireland", "EUR", "Dublin", (("Europe/Dublin", 53.3333, -6.25),)),
    ("IL", "Israel", "ILS", "Jerusalem", (("Asia/Jerusalem", 31.7806, 35.2239),)),
    ("IM", "Isle of Man", "GBP", "Douglas", (("Europe/London", 51.5083, -0.1253),)),
    ("IN", "India", "INR", "New Delhi", (("Asia/Kolkata", 22.5333, 88.3667),)),
    (
        "IO",
        "British Indian Ocean Territory",
        "USD",
        "Diego Garcia",
        (("Indian/Chagos", -7.3333, 72.4167),),
    ),
    ("IQ", "Iraq", "IQD", "Baghdad", (("Asia/Baghdad", 33.35, 44.4167),)),
    ("IR", "Iran", "IRR", "Tehran", (("Asia/Tehran", 35.6667, 51.4333),)),
    ("IS", "Iceland", "ISK", "Reykjavík", (("Africa/Abidjan", 5.3167, -4.0333),)),
    ("IT", "Italy", "EUR", "Rome", (("Europe/Rome", 41.9, 12.4833),)),
    ("JE", "Jersey", "GBP", "Saint Helier", (("Europe/London", 51.5083, -0.1253),)),
    ("JM", "Jamaica", "JMD", "Kingston", (("America/Jamaica", 17.9681, -76.7933),)),
    ("JO", "Jordan", "JOD", "Amman", (("Asia/Amman", 31.95, 35.9333),)),
    ("JP", "Japan", "JPY", "Tokyo", (("Asia/Tokyo", 35.6544, 139.7447),)),
    ("KE", "Kenya", "KES", "Nairobi", (("Africa/Nairobi", -1.2833, 36.8167),)),
    ("KG", "Kyrgyzstan", "KGS", "Bishkek", (("Asia/Bishkek", 42.9, 74.6),)),
    ("KH", "Cambodia", "KHR", "Phnom Penh", (("Asia/Bangkok", 13.75, 100.5167),)),
    (
        "KI",
        "Kiribati",
        "AUD",
        "South Tarawa",
        (
            ("Pacific/Kanton", -2.7833, -171.7167),
            ("Pacific/Kiritimati", 1.8667, -157.3333),
            ("Pacific/Tarawa", 1.4167, 173.0),
        ),
    ),
    ("KM", "Comoros", "KMF", "Moroni", (("Africa/Nairobi", -1.2833, 36.8167),)),
    ("KN", "St Kitts & Nevis", "XCD", "Basseterre", (("America/Puerto_Rico", 18.4683, -66.1061),)),
    ("KP", "Korea (North)", "KPW", "Pyongyang", (("Asia/Pyongyang", 39.0167, 125.75),)),
    ("KR", "Korea (South)", "KRW", "Seoul", (("Asia/Seoul", 37.55, 126.9667),)),
    ("KW", "Kuwait", "KWD", "Kuwait City", (("Asia/Riyadh", 24.6333, 46.7167),)),
    ("KY", "Cayman Islands", "KYD", "George Town", (("America/Panama", 8.9667, -79.5333),)),
    (
        "KZ",
        "Kazakhstan",
        "KZT",
        "Astana",
        (
            ("Asia/Almaty", 43.25, 76.95),
            ("Asia/Aqtau", 44.5167, 50.2667),
            ("Asia/Aqtobe", 50.2833, 57.1667),
            ("Asia/Atyrau", 47.1167, 51.9333),
            ("Asia/Oral", 51.2167, 51.35),
            ("Asia/Qostanay", 53.2, 63.6167),
            ("Asia/Qyzylorda", 44.8, 65.4667),
        ),
    ),
    ("LA", "Laos", "LAK", "Vientiane", (("Asia/Bangkok", 13.75, 100.5167),)),
    ("LB", "Lebanon", "LBP", "Beirut", (("Asia/Beirut", 33.8833, 35.5),)),
    ("LC", "St Lucia", "XCD", "Castries", (("America/Puerto_Rico", 18.4683, -66.1061),)),
    ("LI", "Liechtenstein", "CHF", "Vaduz", (("Europe/Zurich", 47.3833, 8.5333),)),
    ("LK", "Sri Lanka", "LKR", "Sri Jayawardenepura Kotte", (("Asia/Colombo", 6.9333, 79.85),)),
    ("LR", "Liberia", "LRD", "Monrovia", (("Africa/Monrovia", 6.3, -10.7833),)),
    ("LS", "Lesotho", "LSL", "Maseru", (("Africa/Johannesburg", -26.25, 28.0),)),
    ("LT", "Lithuania", "EUR", "Vilnius", (("Europe/Vilnius", 54.6833, 25.3167),)),
    ("LU", "Luxembourg", "EUR", "Luxembourg", (("Europe/Brussels", 50.8333, 4.3333),)),
    ("LV", "Latvia", "EUR", "Riga", (("Europe/Riga", 56.95, 24.1),)),
    ("LY", "Libya", "LYD", "Tripoli", (("Africa/Tripoli", 32.9, 13.1833),)),
    ("MA", "Morocco", "MAD", "Rabat", (("Africa/Casablanca", 33.65, -7.5833),)),
    ("MC", "Monaco", "EUR", "Monaco", (("Europe/Paris", 48.8667, 2.3333),)),
    ("MD", "Moldova", "MDL", "Chișinău", (("Europe/Chisinau", 47.0, 28.8333),)),
    ("ME", "Montenegro", "EUR", "Podgorica", (("Europe/Belgrade", 44.8333, 20.5),)),
    ("MF", "St Martin (French)", "EUR", "Marigot", (("America/Puerto_Rico", 18.4683, -66.1061),)),
    ("MG", "Madagascar", "MGA", "Antananarivo", (("Africa/Nairobi", -1.2833, 36.8167),)),
    (
        "MH",
        "Marshall Islands",
        "USD",
        "Majuro",
        (("Pacific/Kwajalein", 9.0833, 167.3333), ("Pacific/Tarawa", 1.4167, 173.0)),
    ),
    ("MK", "North Macedonia", "MKD", "Skopje", (("Europe/Belgrade", 44.8333, 20.5),)),
    ("ML", "Mali", "XOF", "Bamako", (("Africa/Abidjan", 5.3167, -4.0333),)),
    ("MM", "Myanmar (Burma)", "MMK", "Naypyidaw", (("Asia/Yangon", 16.7833, 96.1667),)),
    (
        "MN",
        "Mongolia",
        "MNT",
        "Ulaanbaatar",
        (("Asia/Hovd", 48.0167, 91.65), ("Asia/Ulaanbaatar", 47.9167, 106.8833)),
    ),
    ("MO", "Macau", "MOP", "Macau", (("Asia/Macau", 22.1972, 113.5417),)),
    ("MP", "Northern Mariana Islands", "USD", "Saipan", (("Pacific/Guam", 13.4667, 144.75),)),
    ("MQ", "Martinique", "EUR", "Fort-de-France", (("America/Martinique", 14.6, -61.0833),)),
    ("MR", "Mauritania", "MRU", "Nouakchott", (("Africa/Abidjan", 5.3167, -4.0333),)),
    ("MS", "Montserrat", "XCD", "Brades", (("America/Puerto_Rico", 18.4683, -66.1061),)),
    ("MT", "Malta", "EUR", "Valletta", (("Europe/Malta", 35.9, 14.5167),)),
    ("MU", "Mauritius", "MUR", "Port Louis", (("Indian/Mauritius", -20.1667, 57.5),)),
    ("MV", "Maldives", "MVR", "Malé", (("Indian/Maldives", 4.1667, 73.5),)),
    ("MW", "Malawi", "MWK", "Lilongwe", (("Africa/Maputo", -25.9667, 32.5833),)),
    (
        "MX",
        "Mexico",
        "MXN",
        "Mexico City",
        (
            ("America/Bahia_Banderas", 20.8, -105.25),
            ("America/Cancun", 21.0833, -86.7667),
            ("America/Chihuahua", 28.6333, -106.0833),
            ("America/Ciudad_Juarez", 31.7333, -106.4833),
            ("America/Hermosillo", 29.0667, -110.9667),
            ("America/Matamoros", 25.8333, -97.5),
            ("America/Mazatlan", 23.2167, -106.4167),
            ("America/Merida", 20.9667, -89.6167),
            ("America/Mexico_City", 19.4, -99.15),
            ("America/Monterrey", 25.6667, -100.3167),
            ("America/Ojinaga", 29.5667, -104.4167),
            ("America/Tijuana", 32.5333, -117.0167),
        ),
    ),
    (
        "MY",
        "Malaysia",
        "MYR",
        "Kuala Lumpur",
        (("Asia/Kuching", 1.55, 110.3333), ("Asia/Singapore", 1.2833, 103.85)),
    ),
    ("MZ", "Mozambique", "MZN", "Maputo", (("Africa/Maputo", -25.9667, 32.5833),)),
    ("NA", "Namibia", "NAD", "Windhoek", (("Africa/Windhoek", -22.5667, 17.1),)),
    ("NC", "New Caledonia", "XPF", "Nouméa", (("Pacific/Noumea", -22.2667, 166.45),)),
    ("NE", "Niger", "XOF", "Niamey", (("Africa/Lagos", 6.45, 3.4),)),
    ("NF", "Norfolk Island", "AUD", "Kingston", (("Pacific/Norfolk", -29.05, 167.9667),)),
    ("NG", "Nigeria", "NGN", "Abuja", (("Africa/Lagos", 6.45, 3.4),)),
    ("NI", "Nicaragua", "NIO", "Managua", (("America/Managua", 12.15, -86.2833),)),
    ("NL", "Netherlands", "EUR", "Amsterdam", (("Europe/Brussels", 50.8333, 4.3333),)),
    ("NO", "Norway", "NOK", "Oslo", (("Europe/Berlin", 52.5, 13.3667),)),
    ("NP", "Nepal", "NPR", "Kathmandu", (("Asia/Kathmandu", 27.7167, 85.3167),)),
    ("NR", "Nauru", "AUD", "Yaren", (("Pacific/Nauru", -0.5167, 166.9167),)),
    ("NU", "Niue", "NZD", "Alofi", (("Pacific/Niue", -19.0167, -169.9167),)),
    (
        "NZ",
        "New Zealand",
        "NZD",
        "Wellington",
        (("Pacific/Auckland", -36.8667, 174.7667), ("Pacific/Chatham", -43.95, -176.55)),
    ),
    ("OM", "Oman", "OMR", "Muscat", (("Asia/Dubai", 25.3, 55.3),)),
    ("PA", "Panama", "PAB", "Panama City", (("America/Panama", 8.9667, -79.5333),)),
    ("PE", "Peru", "PEN", "Lima", (("America/Lima", -12.05, -77.05),)),
    (
        "PF",
        "French Polynesia",
        "XPF",
        "Papeete",
        (
            ("Pacific/Gambier", -23.1333, -134.95),
            ("Pacific/Marquesas", -9.0, -139.5),
            ("Pacific/Tahiti", -17.5333, -149.5667),
        ),
    ),
    (
        "PG",
        "Papua New Guinea",
        "PGK",
        "Port Moresby",
        (("Pacific/Bougainville", -6.2167, 155.5667), ("Pacific/Port_Moresby", -9.5, 147.1667)),
    ),
    ("PH", "Philippines", "PHP", "Manila", (("Asia/Manila", 14.5867, 120.9678),)),
    ("PK", "Pakistan", "PKR", "Islamabad", (("Asia/Karachi", 24.8667, 67.05),)),
    ("PL", "Poland", "PLN", "Warsaw", (("Europe/Warsaw", 52.25, 21.0),)),
    ("PM", "St Pierre & Miquelon", "EUR", "Saint-Pierre", (("America/Miquelon", 47.05, -56.3333),)),
    ("PN", "Pitcairn", "NZD", "Adamstown", (("Pacific/Pitcairn", -25.0667, -130.0833),)),
    ("PR", "Puerto Rico", "USD", "San Juan", (("America/Puerto_Rico", 18.4683, -66.1061),)),
    (
        "PS",
        "Palestine",
        "ILS",
        "Ramallah",
        (("Asia/Gaza", 31.5, 34.4667), ("Asia/Hebron", 31.5333, 35.095)),
    ),
    (
        "PT",
        "Portugal",
        "EUR",
        "Lisbon",
        (
            ("Atlantic/Azores", 37.7333, -25.6667),
            ("Atlantic/Madeira", 32.6333, -16.9),
            ("Europe/Lisbon", 38.7167, -9.1333),
        ),
    ),
    ("PW", "Palau", "USD", "Ngerulmud", (("Pacific/Palau", 7.3333, 134.4833),)),
    ("PY", "Paraguay", "PYG", "Asunción", (("America/Asuncion", -25.2667, -57.6667),)),
    ("QA", "Qatar", "QAR", "Doha", (("Asia/Qatar", 25.2833, 51.5333),)),
    ("RE", "Réunion", "EUR", "Saint-Denis", (("Asia/Dubai", 25.3, 55.3),)),
    ("RO", "Romania", "RON", "Bucharest", (("Europe/Bucharest", 44.4333, 26.1),)),
    ("RS", "Serbia", "RSD", "Belgrade", (("Europe/Belgrade", 44.8333, 20.5),)),
    (
        "RU",
        "Russia",
        "RUB",
        "Moscow",
        (
            ("Asia/Anadyr", 64.75, 177.4833),
            ("Asia/Barnaul", 53.3667, 83.75),
            ("Asia/Chita", 52.05, 113.4667),
            ("Asia/Irkutsk", 52.2667, 104.3333),
            ("Asia/Kamchatka", 53.0167, 158.65),
            ("Asia/Khandyga", 62.6564, 135.5539),
            ("Asia/Krasnoyarsk", 56.0167, 92.8333),
            ("Asia/Magadan", 59.5667, 150.8),
            ("Asia/Novokuznetsk", 53.75, 87.1167),
            ("Asia/Novosibirsk", 55.0333, 82.9167),
            ("Asia/Omsk", 55.0, 73.4),
            ("Asia/Sakhalin", 46.9667, 142.7),
            ("Asia/Srednekolymsk", 67.4667, 153.7167),
            ("Asia/Tomsk", 56.5, 84.9667),
            ("Asia/Ust-Nera", 64.5603, 143.2267),
            ("Asia/Vladivostok", 43.1667, 131.9333),
            ("Asia/Yakutsk", 62.0, 129.6667),
            ("Asia/Yekaterinburg", 56.85, 60.6),
            ("Europe/Astrakhan", 46.35, 48.05),
            ("Europe/Kaliningrad", 54.7167, 20.5),
            ("Europe/Kirov", 58.6, 49.65),
            ("Europe/Moscow", 55.7558, 37.6178),
            ("Europe/Samara", 53.2, 50.15),
            ("Europe/Saratov", 51.5667, 46.0333),
            ("Europe/Simferopol", 44.95, 34.1),
            ("Europe/Ulyanovsk", 54.3333, 48.4),
            ("Europe/Volgograd", 48.7333, 44.4167),
        ),
    ),
    ("RW", "Rwanda", "RWF", "Kigali", (("Africa/Maputo", -25.9667, 32.5833),)),
    ("SA", "Saudi Arabia", "SAR", "Riyadh", (("Asia/Riyadh", 24.6333, 46.7167),)),
    ("SB", "Solomon Islands", "SBD", "Honiara", (("Pacific/Guadalcanal", -9.5333, 160.2),)),
    ("SC", "Seychelles", "SCR", "Victoria", (("Asia/Dubai", 25.3, 55.3),)),
    ("SD", "Sudan", "SDG", "Khartoum", (("Africa/Khartoum", 15.6, 32.5333),)),
    ("SE", "Sweden", "SEK", "Stockholm", (("Europe/Berlin", 52.5, 13.3667),)),
    ("SG", "Singapore", "SGD", "Singapore", (("Asia/Singapore", 1.2833, 103.85),)),
    ("SH", "St Helena", "SHP", "Jamestown", (("Africa/Abidjan", 5.3167, -4.0333),)),
    ("SI", "Slovenia", "EUR", "Ljubljana", (("Europe/Belgrade", 44.8333, 20.5),)),
    ("SJ", "Svalbard & Jan Mayen", "NOK", "Longyearbyen", (("Europe/Berlin", 52.5, 13.3667),)),
    ("SK", "Slovakia", "EUR", "Bratislava", (("Europe/Prague", 50.0833, 14.4333),)),
    ("SL", "Sierra Leone", "SLE", "Freetown", (("Africa/Abidjan", 5.3167, -4.0333),)),
    ("SM", "San Marino", "EUR", "San Marino", (("Europe/Rome", 41.9, 12.4833),)),
    ("SN", "Senegal", "XOF", "Dakar", (("Africa/Abidjan", 5.3167, -4.0333),)),
    ("SO", "Somalia", "SOS", "Mogadishu", (("Africa/Nairobi", -1.2833, 36.8167),)),
    ("SR", "Suriname", "SRD", "Paramaribo", (("America/Paramaribo", 5.8333, -55.1667),)),
    ("SS", "South Sudan", "SSP", "Juba", (("Africa/Juba", 4.85, 31.6167),)),
    ("ST", "Sao Tome & Principe", "STN", "São Tomé", (("Africa/Sao_Tome", 0.3333, 6.7333),)),
    ("SV", "El Salvador", "USD", "San Salvador", (("America/El_Salvador", 13.7, -89.2),)),
    (
        "SX",
        "St Maarten (Dutch)",
        "XCG",
        "Philipsburg",
        (("America/Puerto_Rico", 18.4683, -66.1061),),
    ),
    ("SY", "Syria", "SYP", "Damascus", (("Asia/Damascus", 33.5, 36.3),)),
    ("SZ", "Eswatini (Swaziland)", "SZL", "Mbabane", (("Africa/Johannesburg", -26.25, 28.0),)),
    (
        "TC",
        "Turks & Caicos Is",
        "USD",
        "Cockburn Town",
        (("America/Grand_Turk", 21.4667, -71.1333),),
    ),
    ("TD", "Chad", "XAF", "N'Djamena", (("Africa/Ndjamena", 12.1167, 15.05),)),
    (
        "TF",
        "French S. Terr.",
        "EUR",
        "Port-aux-Français",
        (("Asia/Dubai", 25.3, 55.3), ("Indian/Maldives", 4.1667, 73.5)),
    ),
    ("TG", "Togo", "XOF", "Lomé", (("Africa/Abidjan", 5.3167, -4.0333),)),
    ("TH", "Thailand", "THB", "Bangkok", (("Asia/Bangkok", 13.75, 100.5167),)),
    ("TJ", "Tajikistan", "TJS", "Dushanbe", (("Asia/Dushanbe", 38.5833, 68.8),)),
    ("TK", "Tokelau", "NZD", "Fakaofo", (("Pacific/Fakaofo", -9.3667, -171.2333),)),
    ("TL", "East Timor", "USD", "Dili", (("Asia/Dili", -8.55, 125.5833),)),
    ("TM", "Turkmenistan", "TMT", "Ashgabat", (("Asia/Ashgabat", 37.95, 58.3833),)),
    ("TN", "Tunisia", "TND", "Tunis", (("Africa/Tunis", 36.8, 10.1833),)),
    ("TO", "Tonga", "TOP", "Nuku'alofa", (("Pacific/Tongatapu", -21.1333, -175.2),)),
    ("TR", "Turkey", "TRY", "Ankara", (("Europe/Istanbul", 41.0167, 28.9667),)),
    (
        "TT",
        "Trinidad & Tobago",
        "TTD",
        "Port of Spain",
        (("America/Puerto_Rico", 18.4683, -66.1061),),
    ),
    ("TV", "Tuvalu", "AUD", "Funafuti", (("Pacific/Tarawa", 1.4167, 173.0),)),
    ("TW", "Taiwan", "TWD", "Taipei", (("Asia/Taipei", 25.05, 121.5),)),
    ("TZ", "Tanzania", "TZS", "Dodoma", (("Africa/Nairobi", -1.2833, 36.8167),)),
    (
        "UA",
        "Ukraine",
        "UAH",
        "Kyiv",
        (("Europe/Kyiv", 50.4333, 30.5167), ("Europe/Simferopol", 44.95, 34.1)),
    ),
    ("UG", "Uganda", "UGX", "Kampala", (("Africa/Nairobi", -1.2833, 36.8167),)),
    (
        "UM",
        "US minor outlying islands",
        "USD",
        "Wake Island",
        (("Pacific/Pago_Pago", -14.2667, -170.7), ("Pacific/Tarawa", 1.4167, 173.0)),
    ),
    (
        "US",
        "United States",
        "USD",
        "Washington, D.C.",
        (
            ("America/Adak", 51.88, -176.6581),
            ("America/Anchorage", 61.2181, -149.9003),
            ("America/Boise", 43.6136, -116.2025),
            ("America/Chicago", 41.85, -87.65),
            ("America/Denver", 39.7392, -104.9842),
            ("America/Detroit", 42.3314, -83.0458),
            ("America/Indiana/Indianapolis", 39.7683, -86.1581),
            ("America/Indiana/Knox", 41.2958, -86.625),
            ("America/Indiana/Marengo", 38.3756, -86.3447),
            ("America/Indiana/Petersburg", 38.4919, -87.2786),
            ("America/Indiana/Tell_City", 37.9531, -86.7614),
            ("America/Indiana/Vevay", 38.7478, -85.0672),
            ("America/Indiana/Vincennes", 38.6772, -87.5286),
            ("America/Indiana/Winamac", 41.0514, -86.6031),
            ("America/Juneau", 58.3019, -134.4197),
            ("America/Kentucky/Louisville", 38.2542, -85.7594),
            ("America/Kentucky/Monticello", 36.8297, -84.8492),
            ("America/Los_Angeles", 34.0522, -118.2428),
            ("America/Menominee", 45.1078, -87.6142),
            ("America/Metlakatla", 55.1269, -131.5764),
            ("America/New_York", 40.7142, -74.0064),
            ("America/Nome", 64.5011, -165.4064),
            ("America/North_Dakota/Beulah", 47.2642, -101.7778),
            ("America/North_Dakota/Center", 47.1164, -101.2992),
            ("America/North_Dakota/New_Salem", 46.845, -101.4108),
            ("America/Phoenix", 33.4483, -112.0733),
            ("America/Sitka", 57.1764, -135.3019),
            ("America/Yakutat", 59.5469, -139.7272),
            ("Pacific/Honolulu", 21.3069, -157.8583),
        ),
    ),
    ("UY", "Uruguay", "UYU", "Montevideo", (("America/Montevideo", -34.9092, -56.2125),)),
    (
        "UZ",
        "Uzbekistan",
        "UZS",
        "Tashkent",
        (("Asia/Samarkand", 39.6667, 66.8), ("Asia/Tashkent", 41.3333, 69.3)),
    ),
    ("VA", "Vatican City", "EUR", "Vatican City", (("Europe/Rome", 41.9, 12.4833),)),
    ("VC", "St Vincent", "XCD", "Kingstown", (("America/Puerto_Rico", 18.4683, -66.1061),)),
    ("VE", "Venezuela", "VES", "Caracas", (("America/Caracas", 10.5, -66.9333),)),
    (
        "VG",
        "Virgin Islands (UK)",
        "USD",
        "Road Town",
        (("America/Puerto_Rico", 18.4683, -66.1061),),
    ),
    (
        "VI",
        "Virgin Islands (US)",
        "USD",
        "Charlotte Amalie",
        (("America/Puerto_Rico", 18.4683, -66.1061),),
    ),
    (
        "VN",
        "Vietnam",
        "VND",
        "Hanoi",
        (("Asia/Bangkok", 13.75, 100.5167), ("Asia/Ho_Chi_Minh", 10.75, 106.6667)),
    ),
    ("VU", "Vanuatu", "VUV", "Port Vila", (("Pacific/Efate", -17.6667, 168.4167),)),
    ("WF", "Wallis & Futuna", "XPF", "Mata-Utu", (("Pacific/Tarawa", 1.4167, 173.0),)),
    ("WS", "Samoa (western)", "WST", "Apia", (("Pacific/Apia", -13.8333, -171.7333),)),
    ("YE", "Yemen", "YER", "Sanaa", (("Asia/Riyadh", 24.6333, 46.7167),)),
    ("YT", "Mayotte", "EUR", "Mamoudzou", (("Africa/Nairobi", -1.2833, 36.8167),)),
    ("ZA", "South Africa", "ZAR", "Pretoria", (("Africa/Johannesburg", -26.25, 28.0),)),
    ("ZM", "Zambia", "ZMW", "Lusaka", (("Africa/Maputo", -25.9667, 32.5833),)),
    ("ZW", "Zimbabwe", "ZWG", "Harare", (("Africa/Maputo", -25.9667, 32.5833),)),
)

COUNTRIES: Mapping[str, Country] = MappingProxyType(
    {
        code: Country(
            code=code,
            name=name,
            currency=currency,
            capital=capital_name,
            zones=tuple(ZonePoint(zone, lat, lon) for zone, lat, lon in zones),
        )
        for code, name, currency, capital_name, zones in _ROWS
    }
)


def country(code: str) -> Country | None:
    """Return the country for an ISO 3166-1 alpha-2 code in any case, else ``None``."""
    return COUNTRIES.get(code.strip().upper())


def capital(code: str) -> str | None:
    """Return the capital (or main settlement) of the country, else ``None``."""
    found = country(code)
    return found.capital if found is not None else None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def choose_timezone(code: str, lat: float, lon: float) -> str | None:
    """Return the IANA zone for a settlement at (lat, lon) in the country, else ``None``."""
    found = country(code)
    if found is None:
        return None
    if len(found.zones) == 1:
        return found.zones[0].zone
    best = min(
        found.zones,
        key=lambda point: (_haversine_km(lat, lon, point.lat, point.lon), point.zone),
    )
    return best.zone


def _clip_axis(
    center: float, low: float | None, high: float | None, max_half: float, limit: float
) -> tuple[float, float]:
    if low is None or high is None:
        lo, hi = center - POINT_HALF_SPAN_DEG, center + POINT_HALF_SPAN_DEG
    else:
        lo = min(max(low, center - max_half), center)
        hi = max(min(high, center + max_half), center)
        if hi - lo < POINT_HALF_SPAN_DEG:
            lo, hi = center - POINT_HALF_SPAN_DEG, center + POINT_HALF_SPAN_DEG
    return max(lo, -limit), min(hi, limit)


def clip_bbox(center_lat: float, center_lon: float, bbox: BBox | None) -> BBox:
    """Cap (or widen) a geocoder box around the centre by the rule in the module docstring."""
    if not (math.isfinite(center_lat) and math.isfinite(center_lon)):
        raise ValueError("centre must be finite")
    if not (-90 <= center_lat <= 90 and -180 <= center_lon <= 180):
        raise ValueError("centre out of range")
    cos_lat = max(math.cos(math.radians(center_lat)), MIN_COS_LAT)
    south, north = _clip_axis(
        center_lat,
        bbox.south if bbox else None,
        bbox.north if bbox else None,
        MAX_HALF_SPAN_DEG,
        90.0,
    )
    west, east = _clip_axis(
        center_lon,
        bbox.west if bbox else None,
        bbox.east if bbox else None,
        MAX_HALF_SPAN_DEG / cos_lat,
        180.0,
    )
    return BBox(south=south, west=west, north=north, east=east)
