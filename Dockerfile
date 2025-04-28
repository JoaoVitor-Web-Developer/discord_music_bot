FROM ubuntu:latest
LABEL authors="Joao"

ENTRYPOINT ["top", "-b"]

FROM python:3.9-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ffmpeg \
      libopus-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

CMD ["python", "bot.py"]
