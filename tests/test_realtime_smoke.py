"""Realtime connectivity smoke — exercises the REAL gpt-realtime-mini model
end-to-end except for audio I/O: user text -> realtime model -> tool call -> reply.

Makes a real OpenAI Realtime call, so it is GATED behind RUN_REALTIME_SMOKE=1:

    RUN_REALTIME_SMOKE=1 pytest tests/test_realtime_smoke.py

What this proves: the configured realtime model connects, performs function
calling against our tools, and produces a reply — i.e. the whole agent wiring
works against the real model. The only thing it does NOT cover is the audio
transport (microphone <-> WebRTC via LiveKit), which needs a human speaker.
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from livekit.agents import AgentSession
from livekit.agents.voice.run_result import RunResult
from livekit.plugins import openai

from voice_agent_pizzeria.agent import PizzaAgent
from voice_agent_pizzeria.cart import CartData
from voice_agent_pizzeria.config import get_settings

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_REALTIME_SMOKE") != "1",
    reason="realtime smoke disabled (set RUN_REALTIME_SMOKE=1 to run)",
)


async def test_realtime_model_calls_tool_and_replies() -> None:
    settings = get_settings()
    llm = openai.realtime.RealtimeModel(
        model=settings.openai_realtime_model,
        voice=settings.openai_realtime_voice,
        api_key=settings.openai_api_key.get_secret_value(),
    )
    async with AgentSession[CartData](llm=llm, userdata=CartData()) as session:
        await session.start(PizzaAgent())
        result: RunResult[Any] = await session.run(user_input="Які піци у вас є?")
        result.expect.contains_function_call(name="show_menu")
        result.expect.contains_message(role="assistant")
