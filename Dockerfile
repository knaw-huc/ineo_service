FROM python:3.13-alpine
COPY --from=ghcr.io/astral-sh/uv:0.9.8 /uv /uvx /bin/
STOPSIGNAL SIGKILL

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apk add --no-cache \
    vim \
    bash \
    curl \
    git \
    wget

WORKDIR /app
ADD . /app
RUN uv sync --locked

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
