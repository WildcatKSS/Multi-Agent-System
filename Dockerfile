# Multi-Agent System: Container image
# Version: 2.0.0
# Python 3.12-slim base for minimal image size and security footprint

FROM python:3.12-slim

LABEL version="2.0.0"
LABEL description="Multi-Agent System: Generic autonomous agent orchestration framework"
LABEL maintainer="WildcatKSS"

# Set environment variables for non-interactive builds
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    LOG_LEVEL=INFO

# Create non-root user for security
RUN groupadd -r mas && useradd -r -g mas mas

# Set working directory
WORKDIR /app

# Copy project files
COPY --chown=mas:mas . .

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (include the optional Redis extra for the
# Redis-backed working memory; drop "[redis]" for the zero-dependency core).
RUN pip install --upgrade pip setuptools && \
    pip install -e ".[redis]"

# Switch to non-root user
USER mas

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import mas; print('OK')" || exit 1

# Default command: show version and exit
CMD ["python", "-c", "from mas import __version__; print(f'Multi-Agent System v{__version__}')"]

# Alternative entry points:
# - Run CLI: docker run mas:2.0.0 mas --help
# - Run tests: docker run mas:2.0.0 pytest -v
# - Run REPL: docker run -it mas:2.0.0 python
