FROM python:3.10.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Debug: Print directory structure and Python path
RUN echo "=== Directory Structure ===" && \
    ls -la && \
    echo "=== SRC Directory ===" && \
    ls -la src && \
    echo "=== PYTHONPATH ===" && \
    echo $PYTHONPATH

# Add src directory to Python path
ENV PYTHONPATH="/app"

# Debug: Print final Python path
RUN echo "=== Final PYTHONPATH ===" && \
    echo $PYTHONPATH && \
    python -c "import sys; print('=== Python Sys Path ==='); print('\n'.join(sys.path))"

CMD ["python", "-m", "src.main"]