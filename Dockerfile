FROM python:3.10.10-slim-bookworm

# Install system dependencies with updated SQLite
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    sqlite3 \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Force Python to use pysqlite3 instead of system sqlite3
ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libsqlite3.so.0

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH="/app:/app/src"

CMD ["python", "src/main.py"]