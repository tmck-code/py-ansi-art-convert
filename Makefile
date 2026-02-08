ARCHITECTURE ?= "linux/amd64"
FIX_ARG ?=

ifeq ($(FIX), 1)
	FIX_ARG := --fix
endif

uv/update:
	docker run -it --rm \
		-v ./pyproject.toml:/code/pyproject.toml \
		-v ./uv.lock:/code/uv.lock \
		ghcr.io/astral-sh/uv:bookworm-slim \
		bash -c "apt update && apt install -y --no-install-recommends git && cd /code && uv sync -U"

pypi/build:
	python3 -m build --sdist --wheel
	twine check dist/*

pypi/upload:
	twine upload dist/*

docker/build:
	docker build \
		--platform $(ARCHITECTURE) \
		-t ghcr.io/tmck-code/py-ansi-art-convert:latest \
		-f ops/Dockerfile \
		--target prod \
		.

docker/build-dev:
	docker build \
		--platform $(ARCHITECTURE) \
		--build-arg UID=$(shell id -u) \
		--build-arg GID=$(shell id -g) \
		-t ghcr.io/tmck-code/py-ansi-art-convert:dev \
		-f ops/Dockerfile \
		--target dev \
		.

lint:
	docker run --rm -it \
		-v $(PWD)/ansi_art_convert:/app/ansi_art_convert \
		-v $(PWD)/pyproject.toml:/app/pyproject.toml \
		-u $(shell id -u):$(shell id -g) \
		ghcr.io/tmck-code/py-ansi-art-convert:dev \
		ruff check $(value FIX_ARG)

typecheck:
	docker run --rm -it \
		-v $(PWD)/ansi_art_convert:/app/ansi_art_convert \
		-v $(PWD)/pyproject.toml:/app/pyproject.toml \
		-v $(PWD)/uv.lock:/app/uv.lock \
		ghcr.io/tmck-code/py-ansi-art-convert:dev \
		mypy -p ansi_art_convert

docker/shell:
	docker run --rm -it \
		-v $(PWD)/ansi_art_convert:/app/ansi_art_convert \
		-v $(PWD)/pyproject.toml:/app/pyproject.toml \
		-v $(PWD)/uv.lock:/app/uv.lock \
		ghcr.io/tmck-code/py-ansi-art-convert:dev \
		sh

.PHONY: pypi/build pypi/upload
.PHONY: docker/build docker/build-dev lint typecheck uv/update docker/shell