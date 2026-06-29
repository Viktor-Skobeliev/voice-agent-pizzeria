from __future__ import annotations

from typing import Any


MENU: list[dict[str, Any]] = [
    # Піци
    {"id": "pz1", "name": "Маргарита", "category": "pizza", "price": 189, "available": True,
     "description": "Томатний соус, моцарела, свіжий базилік", "size_cm": 30},
    {"id": "pz2", "name": "Пепероні", "category": "pizza", "price": 229, "available": True,
     "description": "Томатний соус, моцарела, пепероні", "size_cm": 30},
    {"id": "pz3", "name": "Чотири сири", "category": "pizza", "price": 259, "available": True,
     "description": "Моцарела, горгонзола, пармезан, чеддер", "size_cm": 30},
    {"id": "pz4", "name": "Гавайська", "category": "pizza", "price": 219, "available": False,
     "description": "Томатний соус, моцарела, шинка, ананас", "size_cm": 30},
    {"id": "pz5", "name": "Барбекю з куркою", "category": "pizza", "price": 249, "available": True,
     "description": "Соус BBQ, моцарела, куряче філе, червона цибуля", "size_cm": 30},
    # Напої
    {"id": "dr1", "name": "Coca-Cola 0.5л", "category": "drinks", "price": 49, "available": True,
     "description": "Класична Кока-Кола", "size_cm": None},
    {"id": "dr2", "name": "Сік яблучний 0.33л", "category": "drinks", "price": 39, "available": True,
     "description": "Натуральний яблучний сік", "size_cm": None},
    {"id": "dr3", "name": "Вода негазована 0.5л", "category": "drinks", "price": 29, "available": True,
     "description": "Мінеральна вода без газу", "size_cm": None},
    # Десерти
    {"id": "ds1", "name": "Тірамісу", "category": "desserts", "price": 89, "available": True,
     "description": "Класичний італійський десерт з маскарпоне та кавою", "size_cm": None},
    {"id": "ds2", "name": "Чізкейк", "category": "desserts", "price": 79, "available": True,
     "description": "Ніжний чізкейк з ягідним соусом", "size_cm": None},
]

ORDERS: dict[str, dict[str, Any]] = {
    "ORD-101": {
        "id": "ORD-101",
        "customer_name": "Дмитро Шевченко",
        "phone": "+380991234567",
        "address": "вул. Центральна, 12, кв. 5",
        "items": [
            {"id": "pz2", "name": "Пепероні", "quantity": 1, "price": 229},
            {"id": "dr1", "name": "Coca-Cola 0.5л", "quantity": 2, "price": 49},
        ],
        "total": 327,
        "status": "cooking",
        "status_label": "Готується",
    },
    "ORD-102": {
        "id": "ORD-102",
        "customer_name": "Олена Бондар",
        "phone": "+380671112233",
        "address": "просп. Миру, 7, кв. 18",
        "items": [
            {"id": "pz1", "name": "Маргарита", "quantity": 2, "price": 189},
        ],
        "total": 378,
        "status": "delivering",
        "status_label": "Їде до вас",
    },
}

_next_order_id = 103

_CATEGORY_ALIASES: dict[str, str] = {
    "піца": "pizza",
    "піци": "pizza",
    "пицца": "pizza",
    "напій": "drinks",
    "напої": "drinks",
    "десерт": "desserts",
    "десерти": "desserts",
}



def get_menu(category: str | None = None) -> list[dict[str, Any]]:
    """Повертає меню. Якщо передано category — фільтрує за категорією."""
    items = MENU
    if category:
        normalized = _CATEGORY_ALIASES.get(category.lower(), category.lower())
        items = [i for i in items if i["category"] == normalized]
    return [
        {"id": i["id"], "name": i["name"], "price": i["price"],
         "available": i["available"], "category": i["category"]}
        for i in items
    ]


def get_item_details(item_id: str) -> dict[str, Any]:
    """Повна інформація про позицію меню: склад, ціна, розмір, наявність."""
    item = next((i for i in MENU if i["id"] == item_id), None)
    if item is None:
        return {"success": False, "error": "Позицію не знайдено"}
    return {"success": True, **item}


def create_order(
    items: list[dict[str, Any]],  # [{"id": "pz1", "quantity": 2}, ...]
    customer_name: str,
    phone: str,
    address: str,
) -> dict[str, Any]:
    """Оформлює замовлення. items — список {id, quantity}."""
    global _next_order_id

    order_items = []
    total = 0

    for entry in items:
        item = next((m for m in MENU if m["id"] == entry["id"]), None)
        if item is None:
            return {"success": False, "error": f"Позицію {entry['id']} не знайдено"}
        if not item["available"]:
            return {"success": False, "error": f"«{item['name']}» зараз недоступна"}
        qty = entry.get("quantity", 1)
        order_items.append({"id": item["id"], "name": item["name"], "quantity": qty, "price": item["price"]})
        total += item["price"] * qty

    order_id = f"ORD-{_next_order_id}"
    _next_order_id += 1

    ORDERS[order_id] = {
        "id": order_id,
        "customer_name": customer_name,
        "phone": phone,
        "address": address,
        "items": order_items,
        "total": total,
        "status": "accepted",
        "status_label": "Прийнято",
    }

    return {
        "success": True,
        "order_id": order_id,
        "items": [f"{i['name']} x{i['quantity']}" for i in order_items],
        "total": total,
        "estimated_minutes": 40,
    }


def get_order_status(order_id: str) -> dict[str, Any]:
    """Перевірка статусу замовлення за номером."""
    order = ORDERS.get(order_id)
    if order is None:
        return {"success": False, "error": "Замовлення не знайдено"}
    return {
        "success": True,
        "order_id": order_id,
        "status": order["status_label"],
        "items": [f"{i['name']} x{i['quantity']}" for i in order["items"]],
        "total": order["total"],
    }
    
    