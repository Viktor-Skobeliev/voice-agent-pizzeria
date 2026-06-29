"""Worker entrypoint — wires the OpenAI Realtime model + tools into a session.

Run modes (handled by LiveKit's CLI):
    python -m voice_agent_pizzeria.agent console   # talk locally in the terminal
    python -m voice_agent_pizzeria.agent dev       # connect to LiveKit (needs LIVEKIT_*)
"""

from __future__ import annotations

from dotenv import load_dotenv
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.plugins import openai

from .config import get_settings
from .logging_setup import logger, setup_logging
from .prompts import GREETING_INSTRUCTION, SYSTEM_PROMPT
from .tools import ALL_TOOLS


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
            api_key=settings.openai_api_key,
        ),
    )

    await ctx.connect()
    await session.start(agent=PizzaAgent(), room=ctx.room)


def main() -> None:
    # Populate os.environ from .env so the LiveKit CLI (LIVEKIT_*) and the
    # OpenAI plugin pick the credentials up, then hand off to the CLI.
    load_dotenv()
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))


if __name__ == "__main__":
    main()
