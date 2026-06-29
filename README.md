# 🍕 Voice Agent для піцерії

Голосовий AI-агент, що приймає замовлення піцерії по голосу: показує меню,
розповідає про страви, оформлює та відстежує замовлення.

`Python 3.12` · `LiveKit Agents 1.6.4` · `OpenAI Realtime API (gpt-realtime-mini)` ·
`ruff + mypy(strict)` · `48 unit-тестів + 6 eval-сценаріїв`

> Тестове завдання на позицію AI Engineer. Бекенд-функції (`fake_api.py`) надані
> в завданні та підключені до агента через function calling без змін.

---

## Можливості (відповідність ТЗ)

| Агент уміє | Інструмент агента | Бекенд-функція (`fake_api`) |
|------------|-------------------|------------------------------|
| показати меню або категорію | `show_menu` | `get_menu` |
| розповісти про страву (склад/ціна/наявність) | `get_item_details` | `get_item_details` |
| прийняти замовлення (позиції, ім'я, телефон, адреса) | `place_order` | `create_order` |
| перевірити статус замовлення | `check_order_status` | `get_order_status` |

Усе спілкування — голосом українською через OpenAI Realtime API.

---

## Архітектура

```
 Користувач (голос)
        │  WebRTC
        ▼
 LiveKit Server (Cloud) ──connects── Agent Worker (цей репозиторій, Python)
                                          │
                                          ├─ AgentSession + PizzaAgent(instructions)
                                          │     └─ llm = OpenAI Realtime (gpt-realtime-mini)
                                          │
                                          ├─ CartData (стан замовлення сесії)
                                          └─ Tools (function calling):
                                               show_menu · get_item_details
                                               add_to_cart · view_cart · remove_from_cart
                                               place_order · check_order_status
                                                     │ обгортки з валідацією
                                                     ▼
                                               fake_api.py (надано в завданні, без змін)
```

**Ключові рішення:** `fake_api.py` не редагується і не віддається моделі напряму —
він обгорнутий тонким шаром `tools.py`, який додає валідацію аргументів,
нормалізацію та дружні до людини повідомлення про помилки. Склад замовлення
зберігається в кошику сесії (`CartData`), а не в пам'яті моделі — тож позиції,
названі раніше, не губляться.

---

## Швидкий старт

### 1. Залежності
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -e ".[dev]"
```
(або просто `make install`)

### 2. Конфігурація
```bash
cp .env.example .env
# заповнити OPENAI_API_KEY; для живого запуску ще LIVEKIT_URL / _API_KEY / _API_SECRET
# (безкоштовний проєкт: https://cloud.livekit.io)
```

### 3. Тести (без живих викликів — безкоштовно)
```bash
make test          # 48 юніт-тестів логіки інструментів
make lint type     # ruff + mypy(strict)
```

### 4. Поведінкові eval-и (LLM-as-judge, платні виклики)
```bash
make eval          # RUN_LIVE_EVALS=1 pytest tests/test_evals.py
```

### 5. Живий голосовий запуск
```bash
make console       # поговорити з агентом локально в терміналі
make dev           # підключитися до LiveKit (потрібні LIVEKIT_*) + Agents Playground
```

### Docker
```bash
docker build -t voice-agent-pizzeria .
docker run --env-file .env voice-agent-pizzeria   # production worker (start mode)
```

---

## Обробка помилок (4 рівні)

| Рівень | Що ловимо | Як |
|--------|-----------|-----|
| **Інструмент** | бізнес-помилки, биті/зловмисні аргументи | валідація (телефон, кількість 1–50, довжини, невідомі id) + дружні укр. повідомлення; `try/except` — ніколи не падаємо в сесію |
| **Сесія** | зациклення викликів інструментів | `max_tool_steps=5` |
| **Модель/API** | збій OpenAI Realtime | подія `error` → лог; плагін ретраїть всередині |
| **Транспорт** | обрив WebRTC | LiveKit автоматично реконектить; логуємо |

Принцип: агент ніколи не «мовчить у порожнечу» і ніколи не зачитує технічні
помилки вголос.

---

## Тести та eval-и

- **Юніт-тести** (`tests/test_tools.py`, `test_agent.py`) — 48 детермінованих
  кейсів логіки інструментів, валідації, нормалізації. Без LLM, без мережі.
- **Eval-и** (`tests/test_evals.py`) — 6 поведінкових сценаріїв через
  **LLM-as-judge** на реальному агенті в text-режимі (RealtimeModel замінено на
  дешевий `openai.LLM`): привітання, меню, недоступна позиція, підтвердження
  перед замовленням + оформлення, статус, утримання теми. Гейтнуті за
  `RUN_LIVE_EVALS=1`, щоб звичайний прогін був безкоштовним; повністю типізовані,
  тож mypy валідує використання testing-API.
- **CI** (`.github/workflows/ci.yml`) — ruff + mypy(strict) + pytest на кожен push/PR.

---

## Рішення та компроміси

- **Один агент, а не multi-agent граф** (як в офіційному прикладі LiveKit) — для
  чотирьох функцій граф зайвий: додає латентність і складність без користі.
- **Eval-и в text-режимі** — перевіряють поведінку промпту + інструментів дешево
  й детерміновано, не торкаючись аудіо-пайплайну.
- **Імена інструментів дієслівні** (`show_menu`, `check_order_status`) — зрозуміліші
  для LLM, ніж бекендові `get_menu`/`get_order_status`.
- **Помилки `fake_api` пробрасуються у відповідь** — вони вже дружні й конкретні
  («Гавайська недоступна»). Для реального бекенда їх варто мапити на фіксовані рядки.
- **Версії залежностей запінено** — API LiveKit Agents швидко змінюється
  (свіжий `main` уже використовує `AgentServer`); код написано під стабільний 1.6.4.
- **Номер замовлення озвучується цифрами** (без префікса `ORD-`) — зручніше для
  голосу; `check_order_status` нормалізує цифри назад у `ORD-NNN`.
- **Кошик на стороні сервера** (`CartData` в `userdata`) з інструментами
  `add_to_cart` / `view_cart` / `remove_from_cart` — модель не мусить тримати
  склад замовлення в пам'яті, тож нічого не «забуває» між репліками.

---

## Безпека

- Секрети лише в `.env` (у git не потрапляють — `.gitignore` + `.dockerignore`);
  `OPENAI_API_KEY` зберігається як `pydantic.SecretStr`.
- PII (ім'я/телефон) маскується в логах.
- Стійкість до prompt-injection: правила в системному промпті + санітизація всіх
  рядкових аргументів (зрізання керівних символів, обмеження довжини).
- Інструменти ніколи не зачитують сирі технічні помилки користувачу.

---

## Структура проєкту

| Файл | Призначення |
|------|-------------|
| `src/voice_agent_pizzeria/agent.py` | entrypoint, AgentSession, RealtimeModel, події сесії |
| `src/voice_agent_pizzeria/tools.py` | function-tools — меню, статус і операції з кошиком |
| `src/voice_agent_pizzeria/cart.py` | стан замовлення сесії (`CartData`) + його логіка |
| `src/voice_agent_pizzeria/validation.py` | нормалізація телефону/кількості/тексту |
| `src/voice_agent_pizzeria/prompts.py` | system prompt / persona агента |
| `src/voice_agent_pizzeria/config.py` | типізована конфігурація з `.env` |
| `src/voice_agent_pizzeria/logging_setup.py` | структуроване логування + маскування PII |
| `src/voice_agent_pizzeria/fake_api.py` | бекенд із завдання (без змін) |
| `tests/` | юніт-тести + eval-сценарії |
