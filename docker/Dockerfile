# Multi-stage build for Video Evidence analysis container
FROM python:3.10-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final minimal runner stage
FROM python:3.10-slim AS runner

WORKDIR /app

# Copy python libraries from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy project source code
COPY . .

# Bootstrap storage folders
RUN mkdir -p data/uploads data/processed data/logs

# Set configurations environment
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/').read()"

CMD ["python", "-m", "api.main"]
