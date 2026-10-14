FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --no-dev --no-install-project

COPY src ./src
RUN uv sync --no-dev

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uv run structnode api serve --host 0.0.0.0 --port ${PORT}"]
