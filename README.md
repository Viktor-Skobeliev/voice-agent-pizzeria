# 🍕 Voice Agent для піцерії

Голосовий AI-агент, що приймає замовлення піцерії по голосу: показує меню,
розповідає про страви, оформлює та відстежує замовлення.

**Стек:** [LiveKit Agents](https://docs.livekit.io/agents/) (Worker + AgentSession) ·
OpenAI Realtime API (`gpt-realtime-mini`) · Python 3.12.

> Тестове завдання на позицію AI Engineer. Бекенд-функції (`fake_api.py`) надані
> в завданні та підключені до агента через function calling.

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
                                          └─ Tools (function calling):
                                               show_menu · get_item_details
                                               place_order · check_order_status
                                                     │ обгортки з валідацією
                                                     ▼
                                               fake_api.py (надано в завданні)
```

Ключове рішення: `fake_api.py` **не редагується** і не віддається моделі напряму —
він обгорнутий тонким шаром `tools.py`, який додає валідацію аргументів,
нормалізацію та дружні до людини повідомлення про помилки.

---

## Запуск

### 1. Залежності
```bash
python -m venv .venv
.venv/Scripts/activate        # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -e ".[dev]"
```

### 2. Конфігурація
```bash
cp .env.example .env
# заповнити OPENAI_API_KEY та (для живого запуску) LIVEKIT_*
```

### 3. Тести (без живих викликів — безкоштовно)
```bash
pytest          # юніт-тести логіки інструментів
make eval       # поведінкові eval-и (LLM-as-judge)
```

### 4. Живий голосовий запуск
```bash
python -m voice_agent_pizzeria.agent console   # текстовий/голосовий прогін у терміналі
# або підключитися через LiveKit Agents Playground
```

---

## Що всередині

| Файл | Призначення |
|------|-------------|
| `src/voice_agent_pizzeria/agent.py` | entrypoint, AgentSession, RealtimeModel |
| `src/voice_agent_pizzeria/tools.py` | function-tools — обгортки над `fake_api` |
| `src/voice_agent_pizzeria/prompts.py` | system prompt / persona агента |
| `src/voice_agent_pizzeria/config.py` | типізована конфігурація з `.env` |
| `src/voice_agent_pizzeria/fake_api.py` | бекенд із завдання (без змін) |
| `tests/` | юніт-тести + eval-сценарії |

> Детальніше про обробку помилок, eval-и та трейд-офи — у розділах нижче (доповнюється).
