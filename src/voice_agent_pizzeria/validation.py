"""Input validation & normalization for tool arguments.

Pure functions (no I/O) so they're trivially unit-testable. Tools call these
before touching the backend, turning bad input into friendly messages instead
of crashes or junk orders.
"""

from __future__ import annotations

import re

MAX_QUANTITY = 50
MAX_NAME_LEN = 80
MAX_ADDRESS_LEN = 200

_UA_SUBSCRIBER_DIGITS = 9  # digits after the +380 prefix


def clean_text(raw: str | None, *, max_len: int) -> str:
    """Trim, drop control chars, collapse whitespace, and cap length."""
    if not raw:
        return ""
    printable = "".join(ch for ch in raw if ch.isprintable() or ch == " ")
    collapsed = " ".join(printable.split())
    return collapsed[:max_len].strip()


def normalize_phone(raw: str | None) -> str | None:
    """Normalize a Ukrainian phone number to ``+380XXXXXXXXX`` or ``None``."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("380") and len(digits) == 12:
        subscriber = digits[3:]
    elif digits.startswith("0") and len(digits) == 10:
        subscriber = digits[1:]
    elif len(digits) == _UA_SUBSCRIBER_DIGITS:
        subscriber = digits
    else:
        return None
    if len(subscriber) != _UA_SUBSCRIBER_DIGITS:
        return None
    return "+380" + subscriber


def validate_quantity(qty: object) -> int | None:
    """Return an int quantity in ``[1, MAX_QUANTITY]`` or ``None`` if invalid."""
    if isinstance(qty, bool):  # bool is an int subclass — reject it explicitly
        return None
    if isinstance(qty, int):
        value = qty
    elif isinstance(qty, str) and qty.strip().lstrip("-").isdigit():
        value = int(qty)
    else:
        return None
    return value if 1 <= value <= MAX_QUANTITY else None
