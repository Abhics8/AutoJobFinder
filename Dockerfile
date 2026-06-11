FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/embeddings && chmod -R 777 /app

ENV PORT=7860 AUTO_CYCLE=1 HF_HOME=/app/.hf_cache
EXPOSE 7860
CMD ["python", "web.py"]
