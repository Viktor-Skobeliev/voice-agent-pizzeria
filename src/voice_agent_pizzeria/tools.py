"""LiveKit function-tools — thin, validated wrappers around ``fake_api``.

The model never calls ``fake_api`` directly. Each tool validates/normalizes
its arguments, calls the backend, maps backend errors to friendly Ukrainian
messages, logs the call (PII masked), and never raises into the session.

The real logic lives in plain ``*_text`` helpers so it can be unit-tested
without spinning up an LLM; the decorated wrappers are thin adapters.
"""

from __future__ import annotations

from typing import Annotated, Any

from livekit.agents import function_tool
from pydantic import BaseModel, Field

from . import fake_api
from .logging_setup import log_tool_call, logger, mask
from .validation import (
    MAX_ADDRESS_LEN,
    MAX_NAME_LEN,
    MAX_QUANTITY,
    clean_text,
    normalize_phone,
    validate_quantity,
)

_GENERIC_ERROR = "Вибачте, сталася технічна помилка. Спробуймо ще раз?"
_CATEGORY_LABELS = {"pizza": "Піца", "drinks": "Напої", "desserts": "Десерти"}


class OrderLine(BaseModel):
    """A single position in an order."""

    id: str = Field(description="ID позиції меню, напр. 'pz1'")
    quantity: int = Field(default=1, description="Кількість, ціле число від 1")


# --------------------------------------------------------------------------- #
# Pure logic (unit-tested directly, no LLM / no decorator)                     #
# --------------------------------------------------------------------------- #


def _format_menu(items: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    last_category: str | None = None
    for it in items:
        if it["category"] != last_category:
            label = _CATEGORY_LABELS.get(it["category"], it["category"])
            lines.append(f"\n{label}:")
            last_category = it["category"]
        suffix = "" if it["available"] else " (тимчасово недоступно)"
        lines.append(f"- {it['name']} ({it['id']}) — {it['price']} грн{suffix}")
    return "\n".join(lines).strip()


def menu_text(category: str | None) -> str:
    items = fake_api.get_menu(category)
    if not items:
        if category:
            return f"У категорії «{category}» зараз нічого немає."
        return "Меню зараз порожнє."
    return _format_menu(items)


def item_details_text(item_id: str) -> str:
    item_id = clean_text(item_id, max_len=20)
    if not item_id:
        return "Уточніть, будь ласка, яка саме страва вас цікавить."
    res = fake_api.get_item_details(item_id)
    if not res.get("success"):
        return "Не знайшла такої позиції в меню. Показати меню?"
    parts = [f"{res['name']} — {res['price']} грн."]
    if res.get("description"):
        parts.append(f"{res['description']}.")
    if res.get("size_cm"):
        parts.append(f"Розмір {res['size_cm']} см.")
    parts.append("В наявності." if res.get("available") else "Зараз недоступна.")
    return " ".join(parts)


def place_order_text(
    items: list[dict[str, Any]],
    customer_name: str,
    phone: str,
    address: str,
) -> str:
    if not items:
        return "Замовлення поки порожнє. Що бажаєте додати?"

    normalized: list[dict[str, Any]] = []
    for entry in items:
        item_id = clean_text(str(entry.get("id", "")), max_len=20)
        if not item_id:
            return "Уточніть, будь ласка, які саме позиції додати до замовлення."
        qty = validate_quantity(entry.get("quantity", 1))
        if qty is None:
            return f"Некоректна кількість. Можна замовити від 1 до {MAX_QUANTITY} штук."
        normalized.append({"id": item_id, "quantity": qty})

    name = clean_text(customer_name, max_len=MAX_NAME_LEN)
    if not name:
        return "Підкажіть, будь ласка, ім'я для замовлення."
    norm_phone = normalize_phone(phone)
    if not norm_phone:
        return "Вкажіть, будь ласка, коректний номер телефону у форматі +380XXXXXXXXX."
    addr = clean_text(address, max_len=MAX_ADDRESS_LEN)
    if not addr:
        return "Назвіть, будь ласка, адресу доставки."

    res = fake_api.create_order(normalized, name, norm_phone, addr)
    if not res.get("success"):
        reason = res.get("error", "Не вдалося оформити замовлення.")
        return f"{reason} Бажаєте змінити замовлення?"
    items_str = ", ".join(res["items"])
    return (
        f"Замовлення прийнято! Номер {res['order_id']}. "
        f"Склад: {items_str}. Сума {res['total']} грн. "
        f"Орієнтовний час приготування — {res['estimated_minutes']} хвилин."
    )


def order_status_text(order_id: str) -> str:
    oid = clean_text(order_id, max_len=20).upper().replace(" ", "")
    if not oid:
        return "Назвіть, будь ласка, номер замовлення (напр. ORD-101)."
    if not oid.startswith("ORD-"):
        digits = "".join(c for c in oid if c.isdigit())
        if digits:
            oid = f"ORD-{digits}"
    res = fake_api.get_order_status(oid)
    if not res.get("success"):
        return f"Замовлення з номером {oid} не знайдено. Перевірте номер, будь ласка."
    items_str = ", ".join(res["items"])
    return (
        f"Замовлення {oid}: статус «{res['status']}». "
        f"Склад: {items_str}. Сума {res['total']} грн."
    )


# --------------------------------------------------------------------------- #
# Function-tool wrappers (registered with the agent)                          #
# --------------------------------------------------------------------------- #


@function_tool()
async def show_menu(
    category: Annotated[
        str | None,
        Field(description="Категорія: 'pizza', 'drinks' або 'desserts'. Порожньо = все меню."),
    ] = None,
) -> str:
    """Показати меню піцерії або конкретну категорію (піца / напої / десерти)."""
    try:
        out = menu_text(category)
        log_tool_call("show_menu", ok=True, category=category)
        return out
    except Exception:
        logger.exception("show_menu failed")
        log_tool_call("show_menu", ok=False, category=category)
        return _GENERIC_ERROR


@function_tool()
async def get_item_details(
    item_id: Annotated[str, Field(description="ID позиції меню, напр. 'pz1'")],
) -> str:
    """Розповісти про конкретну страву: склад, ціну, розмір, наявність."""
    try:
        out = item_details_text(item_id)
        log_tool_call("get_item_details", ok=True, item_id=item_id)
        return out
    except Exception:
        logger.exception("get_item_details failed")
        log_tool_call("get_item_details", ok=False, item_id=item_id)
        return _GENERIC_ERROR


@function_tool()
async def place_order(
    items: Annotated[list[OrderLine], Field(description="Позиції замовлення (id + кількість)")],
    customer_name: Annotated[str, Field(description="Ім'я клієнта")],
    phone: Annotated[str, Field(description="Телефон, напр. +380XXXXXXXXX")],
    address: Annotated[str, Field(description="Адреса доставки")],
) -> str:
    """Оформити замовлення.

    Викликати ЛИШЕ після того, як клієнт підтвердив склад, суму та контактні дані.
    """
    try:
        dict_items: list[dict[str, Any]] = [
            {"id": li.id, "quantity": li.quantity} for li in items
        ]
        out = place_order_text(dict_items, customer_name, phone, address)
        log_tool_call(
            "place_order",
            ok=True,
            name=mask(customer_name),
            phone=mask(phone),
            lines=len(items),
        )
        return out
    except Exception:
        logger.exception("place_order failed")
        log_tool_call("place_order", ok=False)
        return _GENERIC_ERROR


@function_tool()
async def check_order_status(
    order_id: Annotated[str, Field(description="Номер замовлення, напр. 'ORD-101'")],
) -> str:
    """Перевірити статус замовлення за його номером."""
    try:
        out = order_status_text(order_id)
        log_tool_call("check_order_status", ok=True, order_id=order_id)
        return out
    except Exception:
        logger.exception("check_order_status failed")
        log_tool_call("check_order_status", ok=False, order_id=order_id)
        return _GENERIC_ERROR


ALL_TOOLS = [show_menu, get_item_details, place_order, check_order_status]
