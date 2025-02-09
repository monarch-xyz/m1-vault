FROM python:3.10.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy entire project
COPY . .

# Set Python path to include src directory
ENV PYTHONPATH="${PYTHONPATH}:/app/src"

# Run directly without installation
CMD ["python", "src/main.py"]