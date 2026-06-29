"""Per-session order state (the "cart") + its pure operations.

The cart lives in the AgentSession's ``userdata`` so items the customer named
earlier in the conversation are stored server-side and can't be dropped by the
model's memory. ``place_order`` builds the backend order from the cart.

All functions are pure (take the cart, mutate it, return a spoken-friendly
string) so they can be unit-tested without an LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import fake_api
from .validation import (
    MAX_ADDRESS_LEN,
    MAX_NAME_LEN,
    MAX_QUANTITY,
    clean_text,
    normalize_phone,
    validate_quantity,
)


@dataclass
class CartData:
    """Order state for one session: menu item id -> quantity."""

    items: dict[str, int] = field(default_factory=dict)


def _lines(cart: CartData) -> list[tuple[str, int, int]]:
    """(name, quantity, line_total) for each cart entry, using live menu data."""
    out: list[tuple[str, int, int]] = []
    for item_id, qty in cart.items.items():
        info = fake_api.get_item_details(item_id)
        if info.get("success"):
            out.append((info["name"], qty, info["price"] * qty))
    return out


def view_cart(cart: CartData) -> str:
    lines = _lines(cart)
    if not lines:
        return "Кошик поки порожній."
    total = sum(line_total for _, _, line_total in lines)
    parts = ", ".join(f"{name} x{qty}" for name, qty, _ in lines)
    return f"У замовленні: {parts}. Разом {total} грн."


def add_to_cart(cart: CartData, items: list[dict[str, Any]]) -> str:
    if not items:
        return "Що саме додати до замовлення?"
    for entry in items:
        item_id = clean_text(str(entry.get("id", "")), max_len=20)
        if not item_id:
            return "Уточніть, будь ласка, яку позицію додати."
        qty = validate_quantity(entry.get("quantity", 1))
        if qty is None:
            return f"Некоректна кількість. Можна від 1 до {MAX_QUANTITY} штук."
        info = fake_api.get_item_details(item_id)
        if not info.get("success"):
            return "Такої позиції немає в меню. Показати, що є?"
        if not info.get("available"):
            return f"На жаль, «{info['name']}» зараз недоступна. Обрати щось інше?"
        cart.items[item_id] = cart.items.get(item_id, 0) + qty
    return "Додала. " + view_cart(cart)


def remove_from_cart(cart: CartData, item_id: str) -> str:
    item_id = clean_text(item_id, max_len=20)
    if item_id not in cart.items:
        return "Такої позиції немає в замовленні."
    info = fake_api.get_item_details(item_id)
    name = info["name"] if info.get("success") else item_id
    del cart.items[item_id]
    return f"Прибрала {name}. " + view_cart(cart)


def place_order(cart: CartData, customer_name: str, phone: str, address: str) -> str:
    if not cart.items:
        return "Кошик порожній. Що бажаєте замовити?"
    name = clean_text(customer_name, max_len=MAX_NAME_LEN)
    if not name:
        return "Підкажіть, будь ласка, ім'я для замовлення."
    norm_phone = normalize_phone(phone)
    if not norm_phone:
        return "Вкажіть, будь ласка, коректний номер телефону у форматі +380XXXXXXXXX."
    addr = clean_text(address, max_len=MAX_ADDRESS_LEN)
    if not addr:
        return "Назвіть, будь ласка, адресу доставки."

    order_items = [{"id": iid, "quantity": qty} for iid, qty in cart.items.items()]
    res = fake_api.create_order(order_items, name, norm_phone, addr)
    if not res.get("success"):
        reason = res.get("error", "Не вдалося оформити замовлення.")
        return f"{reason} Бажаєте змінити замовлення?"

    cart.items.clear()
    items_str = ", ".join(res["items"])
    # Speak the order number as plain digits (easier over voice); status lookup
    # re-normalizes a digits-only number back to ORD-NNN.
    order_num = str(res["order_id"]).replace("ORD-", "")
    return (
        f"Замовлення прийнято! Номер замовлення {order_num}. "
        f"Склад: {items_str}. Сума {res['total']} грн. "
        f"Орієнтовний час приготування — {res['estimated_minutes']} хвилин."
    )
