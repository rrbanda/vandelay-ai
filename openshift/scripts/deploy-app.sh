#!/bin/bash
# =============================================================================
# GraphRAG Application Deployment Script for OpenShift
# =============================================================================

set -e

# Configuration
NAMESPACE="fsi-graphrag"
APP_NAME="graphrag"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "============================================================"
echo "FSI GraphRAG Application Deployment"
echo "============================================================"

# Check if logged in
if ! oc whoami &> /dev/null; then
    echo -e "${RED}Error: Not logged into OpenShift${NC}"
    echo "Run: oc login \$OPENSHIFT_API -u \$OPENSHIFT_USER -p \$OPENSHIFT_PASSWORD"
    exit 1
fi

# Switch to project
echo -e "${YELLOW}Switching to project: $NAMESPACE${NC}"
oc project "$NAMESPACE" || oc new-project "$NAMESPACE"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."

# Apply ConfigMap and other resources
echo -e "${YELLOW}Applying application manifests...${NC}"
oc apply -f "$PROJECT_DIR/openshift/graphrag-app.yaml"

# Build the application image using binary build
echo -e "${YELLOW}Starting binary build...${NC}"

# Create a temporary directory for the build context
BUILD_DIR=$(mktemp -d)
cp -r "$PROJECT_DIR/src" "$BUILD_DIR/"
cp -r "$PROJECT_DIR/examples" "$BUILD_DIR/"
cp "$PROJECT_DIR/requirements.txt" "$BUILD_DIR/"
cp "$PROJECT_DIR/Dockerfile" "$BUILD_DIR/"
cp "$PROJECT_DIR/config.yaml" "$BUILD_DIR/"

# Modify BuildConfig for binary build
cat << EOF | oc apply -f -
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  name: graphrag
  namespace: fsi-graphrag
spec:
  source:
    type: Binary
  strategy:
    type: Docker
    dockerStrategy:
      dockerfilePath: Dockerfile
  output:
    to:
      kind: ImageStreamTag
      name: graphrag:latest
EOF

# Start the build
echo -e "${YELLOW}Building application image...${NC}"
cd "$BUILD_DIR"
oc start-build graphrag --from-dir=. --follow

# Clean up
rm -rf "$BUILD_DIR"

# Wait for deployment
echo -e "${YELLOW}Waiting for deployment to be ready...${NC}"
oc rollout status deployment/graphrag -n "$NAMESPACE" --timeout=300s

# Get the route
ROUTE=$(oc get route graphrag -n "$NAMESPACE" -o jsonpath='{.spec.host}')

echo ""
echo "============================================================"
echo -e "${GREEN}Deployment Complete!${NC}"
echo "============================================================"
echo ""
echo "GraphRAG Application URL:"
echo "  https://$ROUTE"
echo ""
echo "To view logs:"
echo "  oc logs -f deployment/graphrag -n $NAMESPACE"
echo ""
echo "To restart the application:"
echo "  oc rollout restart deployment/graphrag -n $NAMESPACE"
echo ""
