# Worker image for the pizzeria voice agent.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# TLS roots for outbound calls to OpenAI / LiveKit.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install the package (hatchling builds from src/). README is referenced by
# pyproject's `readme`, so it must be present at build time.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install .

# Production worker mode. Credentials (OPENAI_API_KEY, LIVEKIT_*) are supplied
# at runtime via environment variables — never baked into the image.
CMD ["python", "-m", "voice_agent_pizzeria.agent", "start"]
