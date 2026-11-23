"""Export the API contract ``openapi.v1.json`` and the AI JSON Schemas (specification §4.7; IMD-06).

``make openapi`` runs ``python -m app.openapi_export --out <repo>/contracts``: it writes
``openapi.v1.json`` (sorted keys) and ``ai/<version>.schema.json``. ``make openapi-check`` runs it
into a temporary directory and diffs the result with the committed files. The document is built
from the app's routes only; no database, provider or environment value is read.

Amendment A2 §3.4 (IMP-722): it also writes ``openapi.any-city.v1.json``, the contract of the app
built with the switch ON (``features_disabled="!any_city_mode"``). ``openapi.v1.json`` stays the
contract of the switch-OFF app, byte for byte.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app
from app.schemas import ai_export

CONTRACT_FILE = "openapi.v1.json"
ANY_CITY_CONTRACT_FILE = "openapi.any-city.v1.json"
# A2 §3.1: the default-off token that turns any_city_mode ON.
ANY_CITY_ON = "!any_city_mode"
CONTRACT_VERSION = "v1"
# create_app runs the start-up checks, which need a database URL; nothing connects to it.
_EXPORT_DATABASE_URL = SecretStr("postgresql+psycopg://openapi-export@db.invalid/openapi-export")


def openapi_document(*, any_city_mode: bool = False) -> dict[str, Any]:
    settings = Settings(
        _env_file=None,  # pydantic-settings init option: read no .env file
        app_env="test",
        ai_provider="MOCK",
        database_url=_EXPORT_DATABASE_URL,
        features_disabled=ANY_CITY_ON if any_city_mode else "",
    )
    document = create_app(settings).openapi()
    # The build version differs per deploy; the contract is versioned by its file name.
    document["info"]["version"] = CONTRACT_VERSION
    return document


def render(*, any_city_mode: bool = False) -> str:
    document = openapi_document(any_city_mode=any_city_mode)
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def export(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    contract = out_dir / CONTRACT_FILE
    contract.write_text(render(), encoding="utf-8")
    any_city = out_dir / ANY_CITY_CONTRACT_FILE
    any_city.write_text(render(any_city_mode=True), encoding="utf-8")
    return [contract, any_city, *ai_export.export(out_dir / "ai")]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--out", type=Path, required=True, help="contracts directory")
    args = parser.parse_args(argv)
    for path in export(args.out):
        print(f"openapi: wrote {path.relative_to(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
