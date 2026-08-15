FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV BRAIN_DB=/data/snowflake_certification.sqlite

WORKDIR /app

COPY requirements.txt .
RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates \
  && update-ca-certificates \
  && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir \
  --trusted-host pypi.org \
  --trusted-host files.pythonhosted.org \
  --trusted-host pypi.python.org \
  -r requirements.txt

COPY app ./app
COPY config ./config
COPY frontend ./frontend
COPY scripts/set_membership.py ./scripts/set_membership.py

RUN mkdir -p /data

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).read()"]

# The application emits its own structured, redacted request-completion event.
# Disable Uvicorn's raw access log so query strings or user-supplied request
# targets cannot bypass that redaction boundary.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
