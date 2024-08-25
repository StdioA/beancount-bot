FROM python:3.11-slim

RUN pip install --upgrade uv && mkdir -p /app
WORKDIR /app
ENV VIRTUAL_ENV=/packages/.venv
COPY requirements/full.txt requirements/optional.txt /app/
RUN mkdir -p $VIRTUAL_ENV && uv venv $VIRTUAL_ENV && \
    uv pip install --no-cache-dir -r full.txt && \
    (uv pip install --no-cache-dir -r optional.txt || true)
COPY . /app

VOLUME /data/ledger
WORKDIR /data/ledger
ENTRYPOINT ["/app/docker/entrypoint.sh", "python", "/app/main.py"]
CMD ["telegram"]
