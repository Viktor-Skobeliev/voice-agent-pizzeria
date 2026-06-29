"""Worker entrypoint — wires the OpenAI Realtime model + tools into a session.

Run modes (handled by LiveKit's CLI):
    python -m voice_agent_pizzeria.agent console   # talk locally in the terminal
    python -m voice_agent_pizzeria.agent dev       # connect to LiveKit (needs LIVEKIT_*)
"""

from __future__ import annotations

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    CloseEvent,
    ErrorEvent,
    JobContext,
    SessionUsageUpdatedEvent,
    WorkerOptions,
    cli,
)
from livekit.plugins import openai

from .config import get_settings
from .logging_setup import logger, setup_logging
from .prompts import GREETING_INSTRUCTION, SYSTEM_PROMPT
from .tools import ALL_TOOLS

# Bound tool-call loops so a confused model can't spin forever in one turn.
_MAX_TOOL_STEPS = 5


class PizzaAgent(Agent):
    """The pizzeria voice assistant: persona + the four backend tools."""

    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT, tools=ALL_TOOLS)

    async def on_enter(self) -> None:
        # Greet the caller as soon as the session connects.
        self.session.generate_reply(instructions=GREETING_INSTRUCTION)


async def entrypoint(ctx: JobContext) -> None:
    """Called by the LiveKit worker for each new room/session."""
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info(
        "starting pizza agent (model=%s, voice=%s)",
        settings.openai_realtime_model,
        settings.openai_realtime_voice,
    )

    session: AgentSession[None] = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model=settings.openai_realtime_model,
            voice=settings.openai_realtime_voice,
            api_key=settings.openai_api_key.get_secret_value(),
        ),
        max_tool_steps=_MAX_TOOL_STEPS,
    )

    # --- Observability + session-level error handling ---
    last_usage: list[object] = []  # holds the latest cumulative usage snapshot

    @session.on("session_usage_updated")
    def _on_usage(ev: SessionUsageUpdatedEvent) -> None:
        last_usage[:] = [ev.usage]

    @session.on("error")
    def _on_error(ev: ErrorEvent) -> None:
        # The Realtime/transport layers retry internally; we record the event
        # so a degrading session is visible rather than silent.
        logger.error("session error: %s", ev)

    @session.on("close")
    def _on_close(ev: CloseEvent) -> None:
        logger.info("session closed; usage: %s", last_usage[0] if last_usage else "n/a")

    await ctx.connect()
    await session.start(agent=PizzaAgent(), room=ctx.room)


def main() -> None:
    # Populate os.environ from .env so the LiveKit CLI (LIVEKIT_*) and the
    # OpenAI plugin pick the credentials up, then hand off to the CLI.
    load_dotenv()
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))


if __name__ == "__main__":
    main()
