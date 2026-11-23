"""Request and response shapes of the any-city routes API-76 to API-79 (Amendment A2 §5; IMP-725).

Defined once here and used only by ``app.places.live_router``. ``import`` is a Python keyword, so
the import state is the field ``import_`` with the JSON name ``import``. ``import_requested_by`` is
never part of a response (A2 §5, §11).
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.places.schemas import Destination

OSM_REF_PATTERN = r"^[NWR][0-9]{1,12}$"

SettlementKind = Literal["city", "town", "village", "municipality"]
DataTier = Literal["curated", "live"]
ImportStatus = Literal["queued", "running", "completed", "insufficient_data", "failed"]
ImportFailureReason = Literal["provider_unavailable", "rate_limited", "timeout", "internal"]


class CityCandidate(BaseModel):
    osm_ref: str = Field(pattern=OSM_REF_PATTERN, description="Nominatim OSM reference")
    name: str
    display_name: str
    region: str | None
    country_code: str
    lat: float
    lon: float
    kind: SettlementKind
    destination_id: UUID | None = Field(
        description="Set when the settlement already exists as a destination"
    )
    data_tier: DataTier | None


class CitySearchOut(BaseModel):
    results: list[CityCandidate] = Field(max_length=8)


class ResolveCityIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    osm_ref: str = Field(pattern=OSM_REF_PATTERN, description="osm_ref of an API-76 result")


class ImportState(BaseModel):
    status: ImportStatus
    failure_reason: ImportFailureReason | None
    places_found: int | None
    places_usable: int | None
    nearby_city: str | None = Field(description="Set only with insufficient_data")
    started_at: datetime | None
    imported_at: datetime | None
    expires_at: datetime | None


class LiveDestinationOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    destination_id: UUID
    slug: str
    name: str
    region: str | None
    country_code: str
    timezone: str
    currency: str = Field(description="ISO 4217; the trip budget currency (IMD-128)")
    data_tier: Literal["live"]
    import_: ImportState = Field(alias="import")


class Attribution(BaseModel):
    source_name: str
    licence: str
    attribution_text: str | None
    url: str | None


class DestinationDetailOut(Destination):
    """Every field of the API-06 item, plus the tier, attribution and import state."""

    model_config = ConfigDict(populate_by_name=True)

    data_tier: DataTier
    imported_at: datetime | None
    attribution: list[Attribution]
    import_: ImportState | None = Field(alias="import")
