FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/
COPY init_sql/ ./init_sql/
COPY run_pipeline.py .
COPY run_validation.py .

RUN mkdir -p output

CMD ["python", "run_pipeline.py"]
