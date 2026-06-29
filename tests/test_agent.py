"""Smoke tests for agent wiring (no LiveKit connection, no LLM)."""

from __future__ import annotations

from livekit.agents import Agent

from voice_agent_pizzeria.agent import PizzaAgent
from voice_agent_pizzeria.prompts import SYSTEM_PROMPT
from voice_agent_pizzeria.tools import ALL_TOOLS


def test_agent_constructs() -> None:
    agent = PizzaAgent()
    assert isinstance(agent, Agent)


def test_exactly_four_tools_registered() -> None:
    assert len(ALL_TOOLS) == 4


def test_prompt_encodes_confirmation_rule() -> None:
    # The order-confirmation guarantee must live in the prompt.
    assert "підтверд" in SYSTEM_PROMPT.lower()


def test_prompt_forbids_hallucinating_data() -> None:
    assert "вигад" in SYSTEM_PROMPT.lower()
