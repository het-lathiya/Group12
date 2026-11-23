"""No request URL with the traveller's search text reaches the logs (IMP-725; Amendment A2 §11).

``configure_logging`` raises the httpx and httpcore loggers to WARNING, so the INFO line httpx
writes for every request (``HTTP Request: GET <url>``) never carries a Nominatim ``q=`` value. The
geocoder is a respx-mocked Nominatim with a SAMPLE answer; no socket is opened.
"""

import io
import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
import respx

from app.core.logging import QUIET_HTTP_LOGGERS, configure_logging
from app.livedata.providers.osm import NominatimGeocoder

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "livedata"
NOMINATIM = "https://nominatim.sample.test"
QUERY = "Secretville Lookup Text"


@pytest.fixture
def log_stream() -> Iterator[io.StringIO]:
    root = logging.getLogger()
    saved_handlers, saved_level = list(root.handlers), root.level
    saved_quiet = {name: logging.getLogger(name).level for name in QUIET_HTTP_LOGGERS}
    stream = io.StringIO()
    configure_logging("INFO", stream)
    try:
        yield stream
    finally:
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)
        for name, level in saved_quiet.items():
            logging.getLogger(name).setLevel(level)


def test_logging_live_query_http_loggers_are_quiet(log_stream: io.StringIO) -> None:
    for name in QUIET_HTTP_LOGGERS:
        assert logging.getLogger(name).getEffectiveLevel() == logging.WARNING


@pytest.mark.asyncio
async def test_logging_live_query_nominatim_search_logs_no_query_text(
    log_stream: io.StringIO,
) -> None:
    answer = json.loads((FIXTURES / "nominatim_search_liveton.json").read_text(encoding="utf-8"))
    with respx.mock(assert_all_called=True) as router:
        router.get(f"{NOMINATIM}/search").respond(200, json=answer)
        await NominatimGeocoder(NOMINATIM, 10, "AITravelPlanner-test/1.0").search(QUERY)
    logged = log_stream.getvalue()
    assert "Secretville" not in logged
    assert "Secretville+Lookup" not in logged
    assert "q=" not in logged
