FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NEWS_OPEN_BROWSER=0

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src
COPY config /app/config
COPY .env.example /app/.env.example

EXPOSE 8787
CMD ["python", "src/run_embedded_webapp.py"]
