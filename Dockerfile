FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CONTENT_ROOT=/content
ENV BRAIN_DB=/data/snowflake_brain.sqlite
ENV AUTO_INGEST=true
ENV ANTHROPIC_API_KEY=

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
COPY docs/ai-career-curriculum ./docs/ai-career-curriculum

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
