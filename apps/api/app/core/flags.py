"""Feature switches (IMD-11): FEATURES_DISABLED is a comma-separated list of switch names.

A listed switch turns its feature off: its routes return 404 NOT_FOUND and its tests skip with a
reason. The cards that build the switched features check them with ``is_enabled``.

Default-off switches (Amendment A2 §3.1, IMD-216): a name in ``DEFAULT_OFF`` is OFF unless the
list holds its ``!`` token (``!any_city_mode``) and not the plain name, so an empty value keeps it
OFF. ``parse_features_disabled`` treats the token as just another name.
"""

from typing import Final

from app.core.config import Settings

DEFAULT_OFF: Final = frozenset({"any_city_mode"})


def parse_features_disabled(raw: str) -> frozenset[str]:
    """`"versions, Packing,,"` -> {"versions", "packing"}."""
    return frozenset(name.strip().lower() for name in raw.split(",") if name.strip())


def disabled_features(settings: Settings) -> frozenset[str]:
    return parse_features_disabled(settings.features_disabled)


def is_enabled(settings: Settings, name: str) -> bool:
    name = name.lower()
    listed = disabled_features(settings)
    if name in DEFAULT_OFF:
        # ON only with the "!" token and no explicit OFF: an explicit OFF wins.
        return f"!{name}" in listed and name not in listed
    return name not in listed
