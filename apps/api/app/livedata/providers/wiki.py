"""MediaWiki guide-source client for Wikivoyage and Wikipedia (Amendment A2 §6.5, §7.1; IMP-723).

The only MediaWiki HTTP calls of the live-data module. Requests are serial, carry ``maxlag=5`` and
the identifying ``User-Agent``, and follow the ORS client conventions (one attempt, a timeout from
settings, safe error messages). At most one page per source is read (A2 §7.3: two per import). A
page that does not exist gives no sections for that source; it is not an error. Logs hold counts.
"""

import logging
import re
from typing import Any, Final, Literal

import httpx

from app.livedata.providers.base import (
    LiveDataRateLimited,
    LiveDataTimeout,
    LiveDataUnavailable,
    WikiSection,
)

logger = logging.getLogger(__name__)

WIKIVOYAGE_API: Final = "https://en.wikivoyage.org/w/api.php"
WIKIPEDIA_API: Final = "https://en.wikipedia.org/w/api.php"
GEOSEARCH_RADIUS_M: Final = 10_000
MAXLAG_S: Final = 5
INTRODUCTION: Final = "Introduction"

Source = Literal["wikivoyage", "wikipedia"]
SOURCES: Final[tuple[tuple[Source, str], ...]] = (
    ("wikivoyage", WIKIVOYAGE_API),
    ("wikipedia", WIKIPEDIA_API),
)

# A level-2 heading line of a plain-text extract: "== See ==" (not "=== Museums ===").
_HEADING: Final = re.compile(r"^==(?!=)\s*(?P<title>[^=].*?)\s*(?<!=)==\s*$")
_COMMON: Final[dict[str, str | int]] = {
    "action": "query",
    "format": "json",
    "formatversion": 2,
    "maxlag": MAXLAG_S,
}


def split_sections(extract: str) -> list[tuple[int, str, str]]:
    """``(index, heading, text)`` for each level-2 section with text; the lead is index 0."""
    sections: list[tuple[int, str, list[str]]] = [(0, INTRODUCTION, [])]
    for line in extract.splitlines():
        match = _HEADING.match(line.strip())
        if match:
            sections.append((len(sections), match.group("title"), []))
        else:
            sections[-1][2].append(line)
    result = []
    for index, heading, lines in sections:
        text = "\n".join(lines).strip()
        if text:
            result.append((index, heading, text))
    return result


def _coordinates(page: dict[str, Any]) -> tuple[float | None, float | None]:
    """The page's primary coordinates (the API's default), or ``(None, None)``."""
    listed = page.get("coordinates")
    if not listed:
        return None, None
    return float(listed[0]["lat"]), float(listed[0]["lon"])


class MediaWikiGuides:
    """``GuideSourceProvider``: plain-text sections of the Wikivoyage and Wikipedia pages."""

    def __init__(
        self,
        timeout_s: float,
        user_agent: str,
        sources: tuple[tuple[Source, str], ...] = SOURCES,
    ) -> None:
        self._timeout_s = timeout_s
        self._user_agent = user_agent
        self._sources = sources

    async def _query(
        self, client: httpx.AsyncClient, api: str, params: dict[str, str | int]
    ) -> Any:
        try:
            response = await client.get(
                api, params={**_COMMON, **params}, headers={"User-Agent": self._user_agent}
            )
            response.raise_for_status()
            body = response.json()
        except httpx.TimeoutException:
            raise LiveDataTimeout("timeout") from None
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                raise LiveDataRateLimited("http 429") from None
            raise LiveDataUnavailable(f"http {status}") from None
        except httpx.HTTPError:
            raise LiveDataUnavailable("connection") from None
        except (ValueError, LookupError, TypeError):
            raise LiveDataUnavailable("malformed response") from None
        if not isinstance(body, dict):
            raise LiveDataUnavailable("malformed response")
        error = body.get("error")
        if isinstance(error, dict):
            raise LiveDataUnavailable("maxlag" if error.get("code") == "maxlag" else "api error")
        return body

    async def _page(self, client: httpx.AsyncClient, api: str, title: str) -> dict[str, Any] | None:
        body = await self._query(
            client,
            api,
            {
                "prop": "extracts|info|coordinates",
                "explaintext": 1,
                "exsectionformat": "wiki",
                "inprop": "url",
                "redirects": 1,
                "titles": title,
            },
        )
        pages = body["query"]["pages"]
        if not isinstance(pages, list) or not pages:
            return None
        page = pages[0]
        if not isinstance(page, dict) or page.get("missing") or page.get("invalid"):
            return None
        return page

    async def _geosearch(
        self, client: httpx.AsyncClient, api: str, lat: float, lon: float
    ) -> str | None:
        body = await self._query(
            client,
            api,
            {
                "list": "geosearch",
                "gscoord": f"{float(lat)}|{float(lon)}",
                "gsradius": GEOSEARCH_RADIUS_M,
                "gslimit": 1,
            },
        )
        hits = body["query"]["geosearch"]
        if not isinstance(hits, list) or not hits:
            return None
        title = hits[0]["title"]
        return title if isinstance(title, str) and title else None

    async def _source(
        self, client: httpx.AsyncClient, source: Source, api: str, name: str, lat: float, lon: float
    ) -> list[WikiSection]:
        page = await self._page(client, api, name)
        if page is None:
            title = await self._geosearch(client, api, lat, lon)
            page = await self._page(client, api, title) if title else None
        if page is None:
            return []
        page_id = int(page["pageid"])
        revision_id = int(page["lastrevid"])
        page_title = str(page["title"])
        page_url = str(page["fullurl"])
        page_lat, page_lon = _coordinates(page)
        extract = page.get("extract") or ""
        if not isinstance(extract, str):
            raise TypeError("extract is not text")
        return [
            WikiSection(
                source=source,
                page_id=page_id,
                revision_id=revision_id,
                page_title=page_title,
                page_url=page_url,
                index=index,
                heading=heading,
                text=text,
                page_lat=page_lat,
                page_lon=page_lon,
            )
            for index, heading, text in split_sections(extract)
        ]

    async def fetch(self, name: str, lat: float, lon: float) -> list[WikiSection]:
        """Sections of the Wikivoyage page, then the Wikipedia page, for the settlement."""
        sections: list[WikiSection] = []
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                for source, api in self._sources:
                    found = await self._source(client, source, api, name, lat, lon)
                    logger.info("mediawiki source=%s sections=%d", source, len(found))
                    sections.extend(found)
        except (ValueError, LookupError, TypeError):
            raise LiveDataUnavailable("malformed response") from None
        return sections
