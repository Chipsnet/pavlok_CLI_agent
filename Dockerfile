FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_PYTHON_PREFERENCE=only-system

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        curl \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv \
    && npm i -g @openai/codex

WORKDIR /app
COPY . .

RUN uv sync --frozen

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:${PATH}"

CMD ["uv", "run", "python", "main.py"]
