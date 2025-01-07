FROM python:3.13-alpine
STOPSIGNAL SIGKILL

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apk add --no-cache vim curl bash

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
