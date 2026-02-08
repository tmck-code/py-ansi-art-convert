FROM ghcr.io/astral-sh/uv:python3.12-alpine AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Omit development dependencies
ENV UV_NO_DEV=1

ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY ansi_art_convert LICENSE README.md /app/
COPY pyproject.toml uv.lock /app/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

FROM builder AS builder-dev

# Include development dependencies
ENV UV_NO_DEV=0

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --only-dev

FROM python:3.12-alpine AS prod

RUN addgroup -S nonroot \
 && adduser -S -G nonroot nonroot
COPY --from=builder --chown=nonroot:nonroot /app /app

ENV PATH="/app/.venv/bin:$PATH"
USER nonroot
WORKDIR /app

FROM python:3.12-alpine AS dev

RUN addgroup -S nonroot \
 && adduser -S -G nonroot nonroot
COPY --from=builder-dev --chown=nonroot:nonroot /app /app

ENV PATH="/app/.venv/bin:$PATH"
USER nonroot
WORKDIR /app
