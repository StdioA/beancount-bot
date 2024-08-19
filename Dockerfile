FROM python:3.11

RUN apt-get update -q && apt-get install -y -q python3-lxml python3-numpy cmake sqlite3 && \
    pip install --upgrade pip uv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN mkdir -p /app
WORKDIR /app
ENV VIRTUAL_ENV=/packages/.venv
RUN mkdir -p $VIRTUAL_ENV && uv venv $VIRTUAL_ENV
COPY requirements-full.txt /app/
COPY requirements-optional.txt /app/
RUN uv pip install --no-cache-dir -r requirements-full.txt
RUN uv pip install --no-cache-dir -r requirements-optional.txt || true
COPY . /app

VOLUME /data/ledger
WORKDIR /data/ledger
ENTRYPOINT ["/app/entrypoint.sh", "python", "/app/main.py"]
CMD ["telegram"]
