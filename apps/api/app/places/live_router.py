"""Any-city routes API-76 to API-79 (Amendment A2 §5), mounted only when ``any_city_mode`` is ON.

``app.main.create_app`` includes this router under ``/api/v1`` (bearer dependency) only when the
switch is ON, so with the switch OFF its paths answer 404 NOT_FOUND and ``openapi.v1.json`` is
unchanged (A2 §3.3). The routes are added by IMP-725; until then the router is empty.
"""

from fastapi import APIRouter

router = APIRouter(tags=["any-city"])
