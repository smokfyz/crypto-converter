from decimal import Decimal


def quantize_decimal(value: str | Decimal, precision: int) -> Decimal:
    return Decimal(value).quantize(Decimal(10) ** -precision)
