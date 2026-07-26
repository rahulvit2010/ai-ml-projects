FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=7860
EXPOSE 7860

# --workers 1 is important: this app loads a ~500-600MB in-memory dataset
# (movie database + actor index) at startup. Each extra worker duplicates
# that memory. --threads 4 lets one worker still handle concurrent requests.
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "1", "--threads", "4", "--timeout", "120", "app:app"]
