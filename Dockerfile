# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# mysqlclient needs these to build against libmysqlclient at pip-install time
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x docker-entrypoint.sh

# Most Docker-based PaaS platforms (Runflare included, as far as could be
# confirmed) inject a $PORT env var and route traffic to whatever port the
# container actually listens on - default to 8000 for local `docker run`.
ENV PORT=8000
EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
