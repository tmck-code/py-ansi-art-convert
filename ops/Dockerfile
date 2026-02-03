FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN python3 -m pip install \
        build twine