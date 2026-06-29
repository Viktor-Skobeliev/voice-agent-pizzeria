"""Unit tests for the session cart logic — no LLM, no network."""

from __future__ import annotations

from voice_agent_pizzeria.cart import (
    CartData,
    add_to_cart,
    place_order,
    remove_from_cart,
    view_cart,
)

_CONTACT = ("Іван", "+380991112233", "вул. Тестова, 1")


# --- add ----------------------------------------------------------------- #


def test_add_item() -> None:
    cart = CartData()
    out = add_to_cart(cart, [{"id": "pz1", "quantity": 2}])
    assert cart.items == {"pz1": 2}
    assert "Маргарита" in out


def test_add_accumulates_same_item() -> None:
    cart = CartData()
    add_to_cart(cart, [{"id": "pz1", "quantity": 1}])
    add_to_cart(cart, [{"id": "pz1", "quantity": 2}])
    assert cart.items["pz1"] == 3


def test_add_unavailable_rejected() -> None:
    cart = CartData()
    out = add_to_cart(cart, [{"id": "pz4", "quantity": 1}])  # Гавайська: unavailable
    assert "недоступна" in out.lower()
    assert cart.items == {}


def test_add_unknown_rejected() -> None:
    cart = CartData()
    out = add_to_cart(cart, [{"id": "zzz", "quantity": 1}])
    assert "немає" in out.lower()
    assert cart.items == {}


def test_add_bad_quantity_rejected() -> None:
    cart = CartData()
    assert "кількість" in add_to_cart(cart, [{"id": "pz1", "quantity": 0}]).lower()
    assert cart.items == {}


def test_add_empty() -> None:
    assert "додати" in add_to_cart(CartData(), []).lower()


# --- view ---------------------------------------------------------------- #


def test_view_empty() -> None:
    assert "порожн" in view_cart(CartData()).lower()


def test_view_with_items() -> None:
    out = view_cart(CartData(items={"pz1": 2, "dr1": 1}))
    assert "Маргарита" in out
    assert "Coca-Cola" in out
    assert "грн" in out


# --- remove -------------------------------------------------------------- #


def test_remove_item() -> None:
    cart = CartData(items={"pz1": 1})
    out = remove_from_cart(cart, "pz1")
    assert cart.items == {}
    assert "прибрала" in out.lower()


def test_remove_absent() -> None:
    assert "немає" in remove_from_cart(CartData(), "pz1").lower()


# --- place order --------------------------------------------------------- #


def test_place_order_happy_path() -> None:
    cart = CartData(items={"pz1": 2, "dr1": 1})
    out = place_order(cart, *_CONTACT)
    assert "прийнято" in out.lower()
    assert "номер замовлення" in out.lower()
    assert cart.items == {}  # cart cleared after a successful order


def test_place_order_empty_cart() -> None:
    assert "порожн" in place_order(CartData(), *_CONTACT).lower()


def test_place_order_bad_phone() -> None:
    cart = CartData(items={"pz1": 1})
    assert "телефон" in place_order(cart, "Іван", "123", "адреса").lower()


def test_place_order_missing_name() -> None:
    cart = CartData(items={"pz1": 1})
    assert "ім'я" in place_order(cart, "  ", "+380991112233", "адреса").lower()


def test_place_order_empty_address() -> None:
    cart = CartData(items={"pz1": 1})
    assert "адрес" in place_order(cart, "Іван", "+380991112233", "  ").lower()
