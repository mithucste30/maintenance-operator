FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ .

# Create non-root user (handle existing group gracefully)
RUN groupadd -g 1000 appuser || true && \
    useradd -m -u 1000 -g 1000 appuser && \
    chown -R appuser:1000 /app

USER appuser

# Default command (can be overridden)
CMD ["kopf", "run", "/app/operator.py", "--verbose"]
