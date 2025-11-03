FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ .

# Create non-root user
RUN useradd -m -u 1000 operator && \
    chown -R operator:operator /app

USER operator

# Default command (can be overridden)
CMD ["kopf", "run", "/app/operator.py", "--verbose"]
