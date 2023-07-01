# syntax=docker/dockerfile:1.2.1
# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
#                                       Base Layer
# Install system-level dependencies here.

ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim AS base

ENV \
    # install poetry here
    POETRY_HOME="/opt/poetry" \
    # disable virtual environment creation (installing to the system level instead)
    POETRY_VIRTUALENVS_CREATE=false \
    # prevent Python from generating *.pyc files
    PYTHONDONTWRITEBYTECODE=1 \
    # always print tracebacks on crash
    # ref https://docs.python.org/3/using/cmdline.html#envvar-PYTHONFAULTHANDLER
    PYTHONFAULTHANDLER=1 \
    # stream python output directly to stdout / stderr instead of buffering it
    # ref https://docs.python.org/3/using/cmdline.html#envvar-PYTHONUNBUFFERED
    PYTHONUNBUFFERED=1

ENV PATH="${POETRY_HOME}/bin:/root/.cargo/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# ref https://github.com/hadolint/hadolint/wiki/DL4006
SHELL ["/bin/bash", "-eo", "pipefail", "-c"]

# note: projects using this template can pin system dependencies after the project has been created
# hadolint ignore=DL3008
RUN --mount=type=cache,sharing=private,target=/var/cache/apt \
    echo "⚙️  installing system dependencies" && \
    apt-get update && apt-get install --no-install-recommends -y build-essential curl git && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s - -y && \
    rm -rf /var/lib/apt/lists/*

# install poetry
RUN echo "⚙️  installing poetry" && \
    curl -sSL https://install.python-poetry.org | python3 - && poetry --version

# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
#                                  Minimal Dependencies
# This layer contains the project's set of minimal Python dependencies, installed using
#   pyproject.toml and poetry.lock.
FROM base AS minimal-deps

WORKDIR /usr/local/src/pyspry

COPY ./pyproject.toml ./poetry.lock ./

RUN --mount=type=cache,sharing=private,target=/root/.cache/ \
    echo "🛠  installing minimal dependencies" && \
    poetry install --only main --no-root --no-interaction

# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
#                                  Development Dependencies
# This layer contains the project's development dependencies, including packages used
#   for developing the project but not necessarily shipped in production.
FROM minimal-deps AS dev-deps

RUN --mount=type=cache,sharing=private,target=/root/.cache \
    echo "🧰  installing dev dependencies" && \
    poetry install --no-root --no-interaction

# note: projects using this template can pin `git` after the project has been created
# hadolint ignore=DL3008
RUN --mount=type=cache,sharing=private,target=/var/cache/apt \
    echo "⚙️  installing git for 'pre-commit'" && \
    apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

COPY ./.pre-commit-config.yaml ./

# note: projects using this template can pin pre-commit after the project has been created
# hadolint ignore=DL3013,DL3042
RUN --mount=type=cache,sharing=private,target=/root/.cache \
    echo "🧰  installing pre-commit" && \
    pip3 install pre-commit

# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
#                                       Target: dev
# This layer is the final target for dev image builds.
FROM dev-deps AS dev

COPY . .

RUN --mount=type=cache,sharing=private,target=/root/.cache \
    echo "🔬  installing pre-commit hooks and project package(s)" \
    pre-commit install --install-hooks && \
    poetry install --no-interaction

# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
#                                     Build Package
# Use poetry to build the package's wheel and source distribution.
FROM dev AS build

RUN echo "🏗  building package with poetry" && \
    poetry build

# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
#                                      Target: prod
# This final layer includes only the minimal dependencies and the installed wheel.
FROM minimal-deps AS prod

COPY --from=build /usr/local/src/pyspry/dist/*.whl ./

# hadolint ignore=DL3042
RUN --mount=type=cache,sharing=private,target=/root/.cache \
    echo "🔨  installing package" && \
    pip3 install ./*.whl
