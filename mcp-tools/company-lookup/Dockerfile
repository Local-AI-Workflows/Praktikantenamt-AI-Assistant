# Company Lookup MCP Tool
# Multi-mode Docker image supporting MCP (SSE/stdio) and REST API

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install the package
RUN pip install --no-cache-dir -e .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Create data directory for Excel files
RUN mkdir -p /app/data /app/results

# Expose ports
# 8001: REST API (8000 used by workday-calculator)
# 8081: MCP SSE (8080 used by workday-calculator)
EXPOSE 8001 8081

# Health check for SSE mode
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8081/sse || exit 1

# Default command: MCP SSE transport
CMD ["company-lookup-mcp", "--transport", "sse", "--host", "0.0.0.0", "--port", "8081"]
