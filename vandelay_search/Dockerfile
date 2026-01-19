# =============================================================================
# Vandelay Search Agent - Dockerfile
# =============================================================================
# Builds a container for the FSI GraphRAG Agent with ADK Web UI
#
# Usage with Podman (from repository root):
#   Build:  podman build -t vandelay-search:latest -f vandelay_search/Dockerfile vandelay_search/
#   Run:    podman run -p 8000:8000 --env-file .env vandelay-search:latest
#
# Usage with Podman Kube:
#   podman kube play openshift/vandelay-search/pod.yaml
#
# Environment variables required (via --env-file or -e):
#   - NEO4J_URI: Neo4j connection URI (e.g., bolt://host.containers.internal:7687)
#   - NEO4J_USERNAME: Neo4j username
#   - NEO4J_PASSWORD: Neo4j password
#   - OPENAI_API_BASE: LLM API endpoint
#   - OPENAI_API_KEY: LLM API key (or "not-needed" for some providers)
#
# Reference: https://google.github.io/adk-docs/deploy/cloud-run/
# =============================================================================

FROM python:3.12-slim

# Set working directory - ADK expects agent code in a discoverable location
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security (recommended by Google ADK docs)
RUN adduser --disabled-password --gecos "" adkuser

# Copy pyproject.toml first for better layer caching
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    "google-adk>=0.1.0" \
    "litellm>=1.0.0" \
    "neo4j>=5.0.0" \
    "httpx>=0.24.0" \
    "pyyaml>=6.0"

# Copy application code
# The directory structure matters for ADK discovery
COPY --chown=adkuser:adkuser . ./vandelay_search/

# Also copy to root for adk web to find the agent
COPY --chown=adkuser:adkuser __init__.py agent.py config.yaml ./vandelay_search/
COPY --chown=adkuser:adkuser . .

# Ensure proper ownership of everything
RUN chown -R adkuser:adkuser /app

# Switch to non-root user
USER adkuser

# Add local bin to PATH for user-installed packages
ENV PATH="/home/adkuser/.local/bin:$PATH"

# Set Python path to include our app
ENV PYTHONPATH="/app:$PYTHONPATH"

# Expose port for ADK web UI
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/list-apps || exit 1

# =============================================================================
# Entrypoint Options
# =============================================================================
# ADK Web UI: Uses adk web command
#   IMPORTANT: --host 0.0.0.0 is required for containers!
#   ADK binds to 127.0.0.1 by default since v1.0.0+
#   See: https://www.reddit.com/r/agentdevelopmentkit/comments/1l9ifkt
# =============================================================================

# Default: Run ADK Web UI
# The --host 0.0.0.0 is CRITICAL - without it, the web UI won't be accessible
# from outside the container (binds to 127.0.0.1 by default)
CMD ["adk", "web", "--host", "0.0.0.0", "--port", "8000"]
