FROM python:3.10-slim as builder

# Based on:
# https://github.com/python-poetry/poetry/issues/1301#issuecomment-872663272
# https://pythonspeed.com/articles/alpine-docker-python/

ENV pbin /root/.local/bin/poetry

RUN apt update && \
    apt install curl git golang --assume-yes

RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ${pbin} config virtualenvs.in-project true

WORKDIR /app

RUN git clone https://github.com/coreos/butane.git .butane && \
    cd .butane && \
    BIN_PATH=/app/etc/foremanlite/exec ./build

COPY poetry.lock pyproject.toml ./
RUN ${pbin} install --no-dev --no-root

COPY . /app
RUN ${pbin} install --no-dev

FROM python:3.10-slim
WORKDIR /app
RUN mkdir -p /var/log/foremanlite
COPY --from=builder /app /app
RUN mv /app/etc/foremanlite /etc/foremanlite/ && rm -r /app/etc
ENTRYPOINT [".venv/bin/python", "-m", "foremanlite.cli"]
