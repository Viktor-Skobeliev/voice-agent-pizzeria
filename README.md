# 🍕 Pizzeria Voice Agent

[![CI](https://github.com/Viktor-Skobeliev/voice-agent-pizzeria/actions/workflows/ci.yml/badge.svg)](https://github.com/Viktor-Skobeliev/voice-agent-pizzeria/actions/workflows/ci.yml)

A voice AI agent that takes pizzeria orders by voice: shows the menu, describes
dishes, places and tracks orders.

`Python 3.12` · `LiveKit Agents 1.6.4` · `OpenAI Realtime API (gpt-realtime-mini)` ·
`ruff + mypy(strict)` · `54 unit tests + 7 eval scenarios`

> Test assignment for an AI Engineer position. The backend functions
> (`fake_api.py`) are provided with the assignment and connected to the agent
> via function calling without modification.

---

## Capabilities (assignment coverage)

| The agent can | Agent tool | Backend function (`fake_api`) |
|---------------|------------|--------------------------------|
| show the menu or a category | `show_menu` | `get_menu` |
| describe a dish (ingredients/price/availability) | `get_item_details` | `get_item_details` |
| take an order (items, name, phone, address) | `place_order` | `create_order` |
| check an order's status | `check_order_status` | `get_order_status` |

All interaction happens by voice, in Ukrainian, via the OpenAI Realtime API.

---

## Architecture

```
 User (voice)
        │  WebRTC
        ▼
 LiveKit Server (Cloud) ──connects── Agent Worker (this repo, Python)
                                          │
                                          ├─ AgentSession + PizzaAgent(instructions)
                                          │     └─ llm = OpenAI Realtime (gpt-realtime-mini)
                                          │
                                          ├─ CartData (per-session order state)
                                          └─ Tools (function calling):
                                               show_menu · get_item_details
                                               add_to_cart · view_cart · remove_from_cart
                                               place_order · check_order_status
                                                     │ wrappers with validation
                                                     ▼
                                               fake_api.py (provided, unmodified)
```

**Key decisions:** `fake_api.py` is never edited and never exposed to the model
directly — it is wrapped by a thin `tools.py` layer that adds argument
validation, normalization, and human-friendly error messages. The order is kept
in per-session cart state (`CartData`), not in the model's memory — so items
mentioned earlier can't be dropped.

---

## 🎬 Sample dialogue

A real voice session. The agent speaks **Ukrainian**; parentheses show the tools
it invokes via function calling.

> **Sofia:** Вітаю! Піцерія «Своя піца», мене звати Софія. Чим можу допомогти?
> **Customer:** Які піци у вас є?
> **Sofia:** *(show_menu)* Є класика — Маргарита й Пепероні, і щось ситніше: Чотири сири чи Барбекю з куркою. Що більше смакує?
> **Customer:** Розкажи про Чотири сири.
> **Sofia:** *(get_item_details)* Чотири сири — 259 гривень: моцарела, горгонзола, пармезан і чеддер. У наявності. Додати?
> **Customer:** Так, одну. І ще воду.
> **Sofia:** *(add_to_cart)* Додала Чотири сири й воду. Щось іще?
> **Customer:** Ні, оформлюй. Іван, 099 111 22 33, вулиця Тестова 1.
> **Sofia:** *(view_cart)* Перевіримо: Чотири сири і вода негазована, разом 288 гривень, доставка на Тестову, 1. Усе так, оформлюю?
> **Customer:** Так, підтверджую.
> **Sofia:** *(place_order)* Замовлення прийнято! Номер сто третє, орієнтовно сорок хвилин. Дякую!
> **Customer:** А який статус замовлення сто один?
> **Sofia:** *(check_order_status)* Замовлення сто один зараз готується.

---

## Quick start

### 1. Dependencies
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -e ".[dev]"
```
(or simply `make install`)

### 2. Configuration
```bash
cp .env.example .env
# fill in OPENAI_API_KEY; for a live run also LIVEKIT_URL / _API_KEY / _API_SECRET
# (free project: https://cloud.livekit.io)
```

### 3. Tests (no live calls — free)
```bash
make test          # 54 unit tests of the tool logic
make lint type     # ruff + mypy(strict)
```

### 4. Behavioural evals (LLM-as-judge, paid calls)
```bash
make eval          # RUN_LIVE_EVALS=1 pytest tests/test_evals.py
```

### 5. Live voice run
```bash
make console       # talk to the agent locally in the terminal
make dev           # connect to LiveKit (needs LIVEKIT_*) + Agents Playground
```

### Docker
```bash
docker build -t voice-agent-pizzeria .
docker run --env-file .env voice-agent-pizzeria   # production worker (start mode)
```

---

## Error handling (4 layers)

| Layer | What we catch | How |
|-------|---------------|-----|
| **Tool** | business errors, malformed/abusive arguments | validation (phone, quantity 1–50, lengths, unknown ids) + friendly Ukrainian messages; `try/except` — we never crash into the session |
| **Session** | runaway tool-call loops | `max_tool_steps=5` |
| **Model/API** | OpenAI Realtime failure | `error` event → log; the plugin retries internally |
| **Transport** | WebRTC drop | LiveKit reconnects automatically; we log it |

Principle: the agent never "goes silent into the void" and never reads raw
technical errors aloud.

---

## Tests & evals

- **Unit tests** (`tests/test_tools.py`, `test_cart.py`, `test_agent.py`) — 54
  deterministic cases for tool logic, the cart, validation and normalization.
  No LLM, no network.
- **Evals** (`tests/test_evals.py`) — 7 behavioural scenarios via
  **LLM-as-judge** against the real agent in text mode (the RealtimeModel is
  swapped for a cheap `openai.LLM`): greeting, menu, unavailable item,
  confirmation before ordering + placement, status, on-topic guardrail, and a
  regression for "doesn't forget earlier cart items". Gated behind
  `RUN_LIVE_EVALS=1` so the default run stays free; fully typed, so mypy
  validates our use of the testing API.
- **Realtime smoke** (`tests/test_realtime_smoke.py`) — exercises the real
  `gpt-realtime-mini` model end-to-end (minus audio I/O), gated behind
  `RUN_REALTIME_SMOKE=1`.
- **CI** (`.github/workflows/ci.yml`) — ruff + mypy(strict) + pytest, plus a
  Docker image build, on every push/PR.

---

## Decisions & trade-offs

- **Single agent, not a multi-agent graph** (as in the official LiveKit example)
  — for four functions a graph is overkill: it adds latency and complexity for
  no benefit.
- **Text-mode evals** — they check the prompt + tool behaviour cheaply and
  deterministically, without touching the audio pipeline.
- **Verb-style tool names** (`show_menu`, `check_order_status`) — clearer for the
  LLM than the backend names `get_menu`/`get_order_status`.
- **`fake_api` errors are forwarded to the reply** — they are already friendly
  and specific ("Hawaiian is unavailable"). For a real backend they should be
  mapped to fixed strings.
- **Pinned dependency versions** — the LiveKit Agents API moves fast (recent
  `main` already uses `AgentServer`); the code targets the stable 1.6.4.
- **Order number spoken as digits** (without the `ORD-` prefix) — easier over
  voice; `check_order_status` normalizes digits back to `ORD-NNN`.
- **Server-side cart** (`CartData` in `userdata`) with `add_to_cart` /
  `view_cart` / `remove_from_cart` tools — the model doesn't have to hold the
  order in memory, so nothing is "forgotten" between turns.

---

## Security

- Secrets live only in `.env` (never committed — `.gitignore` + `.dockerignore`);
  `OPENAI_API_KEY` is stored as a `pydantic.SecretStr`.
- PII (name/phone) is masked in logs.
- Prompt-injection resistance: rules in the system prompt + sanitization of every
  string argument (stripping control characters, length limits).
- Tools never read raw technical errors back to the user.

---

## Project layout

| File | Purpose |
|------|---------|
| `src/voice_agent_pizzeria/agent.py` | entrypoint, AgentSession, RealtimeModel, session events |
| `src/voice_agent_pizzeria/tools.py` | function-tools — menu, status and cart operations |
| `src/voice_agent_pizzeria/cart.py` | per-session order state (`CartData`) + its logic |
| `src/voice_agent_pizzeria/validation.py` | phone/quantity/text normalization |
| `src/voice_agent_pizzeria/prompts.py` | system prompt / agent persona |
| `src/voice_agent_pizzeria/config.py` | typed configuration from `.env` |
| `src/voice_agent_pizzeria/logging_setup.py` | structured logging + PII masking |
| `src/voice_agent_pizzeria/fake_api.py` | backend from the assignment (unmodified) |
| `tests/` | unit tests + eval scenarios |
