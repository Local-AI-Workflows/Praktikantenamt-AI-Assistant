# Dockerfile for Workday Calculator MCP Server
# Supports three modes:
# - REST API (HTTP): Default, port 8000
# - MCP SSE (HTTP): For Claude Desktop remote, port 8080
# - MCP stdio: For local Claude Desktop

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the package files
COPY pyproject.toml .
COPY workday_calculator/ ./workday_calculator/

# Install the package
RUN pip install --no-cache-dir -e .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose ports: 8000 for REST API, 8080 for MCP SSE
EXPOSE 8000 8080

# Default to MCP SSE mode (recommended for Docker)
# Override with:
# - REST API: ["uvicorn", "workday_calculator.api:app", "--host", "0.0.0.0", "--port", "8000"]
# - MCP stdio: ["workday-calc-mcp", "--transport", "stdio"]
CMD ["workday-calc-mcp", "--transport", "sse", "--host", "0.0.0.0", "--port", "8080"]
