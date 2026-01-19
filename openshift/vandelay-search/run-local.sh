#!/bin/bash
# =============================================================================
# Vandelay Search - Local Run Script for Podman Desktop
# =============================================================================
# This script builds and runs the agent locally with Podman.
#
# Prerequisites:
#   1. Podman Desktop installed and running
#   2. Neo4j running (locally or remote)
#   3. Copy env.template to .env and fill in your values
#
# Usage:
#   ./run-local.sh          # Build and run
#   ./run-local.sh stop     # Stop the pod
#   ./run-local.sh logs     # View logs
#   ./run-local.sh shell    # Enter container shell
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
IMAGE_NAME="vandelay-search:latest"
POD_NAME="vandelay-search-pod"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check for .env file
check_env() {
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        log_error ".env file not found!"
        log_info "Create it from the template:"
        echo "    cp $SCRIPT_DIR/env.template $SCRIPT_DIR/.env"
        echo "    # Edit .env with your actual values"
        exit 1
    fi
}

# Build the container image
build_image() {
    log_info "Building container image: $IMAGE_NAME"
    podman build -t "$IMAGE_NAME" \
        -f "$REPO_ROOT/vandelay_search/Dockerfile" \
        "$REPO_ROOT/vandelay_search/"
}

# Run the container
run_container() {
    check_env
    
    # Stop existing container if running
    podman rm -f "$POD_NAME" 2>/dev/null || true
    
    log_info "Starting container: $POD_NAME"
    log_info "Loading environment from: $SCRIPT_DIR/.env"
    
    podman run -d \
        --name "$POD_NAME" \
        --env-file "$SCRIPT_DIR/.env" \
        -p 8000:8000 \
        "$IMAGE_NAME"
    
    log_info "Container started!"
    echo ""
    log_info "ADK Web UI: http://localhost:8000"
    echo ""
    log_info "View logs:  $0 logs"
    log_info "Stop:       $0 stop"
}

# Stop the container
stop_container() {
    log_info "Stopping container: $POD_NAME"
    podman rm -f "$POD_NAME" 2>/dev/null || true
    log_info "Container stopped"
}

# View logs
view_logs() {
    log_info "Viewing logs for: $POD_NAME"
    podman logs -f "$POD_NAME"
}

# Enter shell
enter_shell() {
    log_info "Entering shell in: $POD_NAME"
    podman exec -it "$POD_NAME" /bin/bash
}

# Main
case "${1:-run}" in
    build)
        build_image
        ;;
    run|start)
        build_image
        run_container
        ;;
    stop)
        stop_container
        ;;
    logs)
        view_logs
        ;;
    shell)
        enter_shell
        ;;
    restart)
        stop_container
        build_image
        run_container
        ;;
    *)
        echo "Usage: $0 {build|run|stop|logs|shell|restart}"
        exit 1
        ;;
esac
