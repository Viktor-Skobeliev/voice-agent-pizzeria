"""Unit tests for read-only tool logic — no LLM, no network, deterministic."""

from __future__ import annotations

import pytest

from voice_agent_pizzeria.tools import item_details_text, menu_text, order_status_text
from voice_agent_pizzeria.validation import normalize_phone, validate_quantity

# --- menu ---------------------------------------------------------------- #


def test_menu_lists_all_categories() -> None:
    out = menu_text(None)
    assert "Маргарита" in out
    assert "Coca-Cola" in out
    assert "Тірамісу" in out


def test_menu_filter_pizza_excludes_drinks() -> None:
    out = menu_text("pizza")
    assert "Маргарита" in out
    assert "Coca-Cola" not in out


def test_menu_ukrainian_alias() -> None:
    assert "Маргарита" in menu_text("піца")


def test_menu_marks_unavailable() -> None:
    out = menu_text("pizza")
    assert "Гавайська" in out
    assert "недоступно" in out.lower()


def test_menu_unknown_category_is_friendly() -> None:
    assert "немає" in menu_text("xyz").lower()


# --- item details -------------------------------------------------------- #


def test_item_details_ok() -> None:
    out = item_details_text("pz1")
    assert "Маргарита" in out
    assert "189" in out


def test_item_details_unknown() -> None:
    assert "не знайшла" in item_details_text("zzz").lower()


def test_item_details_unavailable() -> None:
    assert "недоступна" in item_details_text("pz4").lower()  # Гавайська


def test_item_details_empty_input() -> None:
    assert "уточніть" in item_details_text("   ").lower()


# --- order status -------------------------------------------------------- #


def test_status_known_order() -> None:
    out = order_status_text("ORD-101")
    assert "ORD-101" in out
    assert "статус" in out.lower()


def test_status_unknown_order() -> None:
    assert "не знайдено" in order_status_text("ORD-999").lower()


def test_status_normalizes_digits_only() -> None:
    assert "ORD-101" in order_status_text("101")


def test_status_empty_input() -> None:
    assert "назвіть" in order_status_text("").lower()
    assert "назвіть" in order_status_text("   ").lower()


# --- phone normalization ------------------------------------------------- #


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+380991234567", "+380991234567"),
        ("380991234567", "+380991234567"),
        ("0991234567", "+380991234567"),
        ("099 123 45 67", "+380991234567"),
        ("(099) 123-45-67", "+380991234567"),
    ],
)
def test_phone_valid(raw: str, expected: str) -> None:
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", ["", "123", "abc", "+1 555 0000", None])
def test_phone_invalid(raw: str | None) -> None:
    assert normalize_phone(raw) is None


# --- quantity ------------------------------------------------------------ #


@pytest.mark.parametrize(
    ("qty", "valid"),
    [
        (1, True),
        (50, True),
        (0, False),
        (-1, False),
        (51, False),
        (True, False),
        ("3", True),
        ("x", False),
        ("1.0", True),
        ("2.5", False),
        (2.0, True),
        (2.5, False),
    ],
)
def test_quantity(qty: object, valid: bool) -> None:
    assert (validate_quantity(qty) is not None) is valid
