# =============================================================================
# Vandelay Migration Agent - Dockerfile
# =============================================================================
# Builds a container for the Migration Agent with ADK Web UI
#
# IMPORTANT: This Dockerfile must be built from the REPOSITORY ROOT
# because it needs access to:
#   - vandelay_search/ (template sub-agents)
#   - vandelay_migration/ (this agent)
#   - mcp_servers/ (service request mock)
#
# Usage with Podman (from repository root):
#   Build:  podman build -t vandelay-migration:latest -f vandelay_migration/Dockerfile .
#   Run:    podman run -p 8000:8000 --env-file .env vandelay-migration:latest
#
# Environment variables required (via --env-file or -e):
#   - NEO4J_URI: Neo4j connection URI
#   - NEO4J_USERNAME: Neo4j username
#   - NEO4J_PASSWORD: Neo4j password
#   - OPENAI_API_BASE: LLM API endpoint
#   - OPENAI_API_KEY: LLM API key
#   - LLAMASTACK_BASE_URL: Vector store endpoint
#   - MIGRATION_VECTOR_STORE_ID: Vector store ID for migration docs
# =============================================================================

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN adduser --disabled-password --gecos "" adkuser

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    "google-adk>=0.1.0" \
    "litellm>=1.0.0" \
    "neo4j>=5.0.0" \
    "httpx>=0.24.0" \
    "pyyaml>=6.0" \
    "fastapi>=0.100.0" \
    "uvicorn>=0.20.0"

# Fix ADK web UI runtime config permissions
# The ADK web UI needs to write runtime-config.json at startup
RUN chmod -R a+w /usr/local/lib/python3.12/site-packages/google/adk/cli/browser/assets/config/ 2>/dev/null || true

# Create _lib directory for packages (underscore prefix hides from ADK scan)
RUN mkdir -p /app/_lib

# Copy supporting packages to _lib/ (not discovered by ADK)
COPY --chown=adkuser:adkuser vandelay_search/ ./_lib/vandelay_search/
COPY --chown=adkuser:adkuser mcp_servers/ ./_lib/mcp_servers/

# Copy the migration agent package
COPY --chown=adkuser:adkuser vandelay_migration/ ./vandelay_migration/

# IMPORTANT: Remove any .adk folders that may have been copied from local dev
# These folders cause ADK to incorrectly discover sub-directories as apps
RUN find /app -type d -name ".adk" -exec rm -rf {} + 2>/dev/null || true

# Ensure proper ownership
RUN chown -R adkuser:adkuser /app

# Switch to non-root user
USER adkuser

# Add local bin to PATH
ENV PATH="/home/adkuser/.local/bin:$PATH"

# Set Python path to include our app and _lib packages
ENV PYTHONPATH="/app:/app/_lib:$PYTHONPATH"

# Expose port for ADK web UI
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/list-apps || exit 1

# Run ADK Web UI
# IMPORTANT: --host 0.0.0.0 is required for containers!
# Run from /app which contains vandelay_migration/ folder
# ADK will discover vandelay_migration as an agent (has __init__.py with "from . import agent")
CMD ["adk", "web", "--host", "0.0.0.0", "--port", "8000"]
