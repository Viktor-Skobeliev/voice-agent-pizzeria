"""LiveKit function-tools — validated wrappers around fake_api + cart state.

Read-only tools (show_menu, get_item_details, check_order_status) wrap fake_api
directly. Cart tools (add_to_cart, view_cart, remove_from_cart, place_order)
operate on per-session CartData so items the customer named earlier in the
conversation can't be forgotten by the model.

Menu/status logic lives in plain ``*_text`` helpers here; cart logic lives in
cart.py — both unit-tested without an LLM. The decorated wrappers are thin
adapters that validate, log (PII masked) and never raise into the session.
"""

from __future__ import annotations

from typing import Annotated, Any

from livekit.agents import RunContext, function_tool
from livekit.agents.llm import Tool, Toolset
from pydantic import BaseModel, Field

from . import cart as cart_ops
from . import fake_api
from .cart import CartData
from .logging_setup import log_tool_call, logger, mask
from .validation import clean_text

_GENERIC_ERROR = "Вибачте, сталася технічна помилка. Спробуймо ще раз?"
_CATEGORY_LABELS = {"pizza": "Піца", "drinks": "Напої", "desserts": "Десерти"}


class OrderLine(BaseModel):
    """A single position the customer wants to add."""

    id: str = Field(description="ID позиції меню, напр. 'pz1'")
    quantity: int = Field(default=1, description="Кількість, ціле число від 1")


# --------------------------------------------------------------------------- #
# Read-only menu/status logic (unit-tested directly)                          #
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
    if category is not None:
        category = clean_text(category, max_len=20) or None
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
async def add_to_cart(
    ctx: RunContext[CartData],
    items: Annotated[list[OrderLine], Field(description="Позиції для додавання (id + кількість)")],
) -> str:
    """Додати позиції до замовлення. Викликай ОДРАЗУ, щойно клієнт їх назвав."""
    try:
        dict_items: list[dict[str, Any]] = [
            {"id": li.id, "quantity": li.quantity} for li in items
        ]
        out = cart_ops.add_to_cart(ctx.userdata, dict_items)
        log_tool_call("add_to_cart", ok=True, lines=len(items))
        return out
    except Exception:
        logger.exception("add_to_cart failed")
        log_tool_call("add_to_cart", ok=False)
        return _GENERIC_ERROR


@function_tool()
async def view_cart(ctx: RunContext[CartData]) -> str:
    """Показати поточний склад замовлення та суму."""
    try:
        out = cart_ops.view_cart(ctx.userdata)
        log_tool_call("view_cart", ok=True, lines=len(ctx.userdata.items))
        return out
    except Exception:
        logger.exception("view_cart failed")
        log_tool_call("view_cart", ok=False)
        return _GENERIC_ERROR


@function_tool()
async def remove_from_cart(
    ctx: RunContext[CartData],
    item_id: Annotated[str, Field(description="ID позиції, яку прибрати, напр. 'pz1'")],
) -> str:
    """Прибрати позицію із замовлення."""
    try:
        out = cart_ops.remove_from_cart(ctx.userdata, item_id)
        log_tool_call("remove_from_cart", ok=True, item_id=item_id)
        return out
    except Exception:
        logger.exception("remove_from_cart failed")
        log_tool_call("remove_from_cart", ok=False, item_id=item_id)
        return _GENERIC_ERROR


@function_tool()
async def place_order(
    ctx: RunContext[CartData],
    customer_name: Annotated[str, Field(description="Ім'я клієнта")],
    phone: Annotated[str, Field(description="Телефон, напр. +380XXXXXXXXX")],
    address: Annotated[str, Field(description="Адреса доставки")],
) -> str:
    """Оформити замовлення з поточного кошика.

    Викликати ЛИШЕ після того, як клієнт підтвердив склад і суму (див. view_cart).
    """
    try:
        out = cart_ops.place_order(ctx.userdata, customer_name, phone, address)
        log_tool_call(
            "place_order",
            ok=True,
            name=mask(customer_name),
            phone=mask(phone),
            lines=len(ctx.userdata.items),
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


ALL_TOOLS: list[Tool | Toolset] = [
    show_menu,
    get_item_details,
    add_to_cart,
    view_cart,
    remove_from_cart,
    place_order,
    check_order_status,
]
