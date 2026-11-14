"""Money.currency is three upper-case letters (§6.1 Money, SG-3 F-1)."""

import pytest
from pydantic import ValidationError

from app.schemas.common import Money


def test_money_accepts_an_iso_4217_code() -> None:
    assert Money(amount="10.00", currency="INR").currency == "INR"


@pytest.mark.parametrize("currency", ["inr", "IN", "INRS", "IN1", " INR", ""])
def test_money_refuses_any_other_currency_format(currency: str) -> None:
    with pytest.raises(ValidationError):
        Money(amount="10.00", currency=currency)


def test_imd_159_currency_pattern_error_uses_plain_language() -> None:
    with pytest.raises(ValidationError) as error:
        Money(amount="10.00", currency="IN1")
    assert error.value.errors()[0]["msg"] == "Currency must be a three-letter ISO 4217 code."
