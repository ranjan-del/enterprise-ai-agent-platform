# Backend image — FastAPI + LangGraph.
# TODO: checklist "docker compose up brings up full stack".
# NOTE: scaffolding only — not built by the setup step.
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY . .

EXPOSE 8000

# TODO: run DB migrations on startup before launching the server.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
