# ---------------------------------------------------------------------------
# Stage 1: Dependencies
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS deps

WORKDIR /app

# Install system build deps (only needed for compiled packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Pre-install pip tools to benefit from layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir pip==24.0
RUN pip install --no-cache-dir -r requirements.txt

# Install Composio for agent tools
RUN pip install --no-cache-dir composio-core composio-langchain

RUN pip install --no-cache-dir "pydantic[email]>=2.6.1"
# Re-pin langchain dependencies that composio overwrote
RUN pip install --no-cache-dir 'langchain-core>=0.2.27,<0.3.0' 'langchain-openai>=0.1.7' 'langchain-anthropic>=0.1.15'


# ---------------------------------------------------------------------------
# Stage 2: Builder (for any additional wheel-based builds)
# ---------------------------------------------------------------------------
FROM deps AS builder

# No additional build steps needed for this project, but the stage exists
# to allow extension if native dependencies are added later.
WORKDIR /app


# ---------------------------------------------------------------------------
# Stage 3: Production image
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS production

LABEL maintainer="Multi-Agent Orchestrator"
LABEL description="FastAPI backend for Multi-Agent Orchestrator"

WORKDIR /app

# Create non-root user for security
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Install curl (needed for healthchecks) in prod image only
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-installed dependencies from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appgroup . .

# Create data directory with correct permissions for SQLite
RUN mkdir -p /app/data && chown appuser:appgroup /app/data

# Switch to non-root user
USER appuser

# Disable Python UCF for deterministic output
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random

# Health check – curl is available in this stage
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

ENTRYPOINT ["tini", "--"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
