FROM python:3.9-slim as builder

# Based on:
# https://github.com/python-poetry/poetry/issues/1301#issuecomment-872663272
# https://pythonspeed.com/articles/alpine-docker-python/

ENV pbin /root/.local/bin/poetry

RUN apt update && \
    apt install curl --assume-yes
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ${pbin} config virtualenvs.in-project true

WORKDIR /app
COPY poetry.lock pyproject.toml ./
RUN ${pbin} install --no-dev --no-root

COPY . /app
RUN ${pbin} install --no-dev

FROM python:3.9-slim

COPY --from=builder /app /app
ENTRYPOINT ["/app/.venv/bin/gunicorn", "foremanlite.main:app"]
