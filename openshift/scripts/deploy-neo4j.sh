#!/bin/bash
# =============================================================================
# Neo4j Deployment Script for OpenShift
# FSI GraphRAG Demo
# =============================================================================
# Required environment variables:
#   OPENSHIFT_API      - OpenShift API URL
#   OPENSHIFT_USER     - OpenShift username
#   OPENSHIFT_PASSWORD - OpenShift password
#   NEO4J_PASSWORD     - Password for Neo4j database
# =============================================================================

set -e

# Configuration from environment variables
OPENSHIFT_API="${OPENSHIFT_API:?Error: OPENSHIFT_API not set}"
OPENSHIFT_USER="${OPENSHIFT_USER:?Error: OPENSHIFT_USER not set}"
OPENSHIFT_PASSWORD="${OPENSHIFT_PASSWORD:?Error: OPENSHIFT_PASSWORD not set}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-fsi-graphrag-2024}"
NAMESPACE="${NAMESPACE:-fsi-graphrag}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================================"
echo "Neo4j Deployment for FSI GraphRAG"
echo "============================================================"

# Check if oc is installed
if ! command -v oc &> /dev/null; then
    echo -e "${RED}Error: oc client not found${NC}"
    echo "Download from: http://mirror.openshift.com/pub/openshift-v4/clients/ocp/4.18.20/openshift-client-linux-4.18.20.tar.gz"
    exit 1
fi

# Login to OpenShift
echo -e "${YELLOW}Logging into OpenShift...${NC}"
oc login "$OPENSHIFT_API" -u "$OPENSHIFT_USER" -p "$OPENSHIFT_PASSWORD" --insecure-skip-tls-verify

# Create namespace if it doesn't exist
echo -e "${YELLOW}Creating namespace: $NAMESPACE${NC}"
oc new-project "$NAMESPACE" 2>/dev/null || oc project "$NAMESPACE"

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENSHIFT_DIR="$SCRIPT_DIR/../openshift"

# Apply resources in order
echo -e "${YELLOW}Creating Neo4j secret...${NC}"
oc apply -f "$OPENSHIFT_DIR/neo4j-secret.yaml"

echo -e "${YELLOW}Creating persistent volume claims...${NC}"
oc apply -f "$OPENSHIFT_DIR/neo4j-pvc.yaml"

echo -e "${YELLOW}Deploying Neo4j...${NC}"
oc apply -f "$OPENSHIFT_DIR/neo4j-deployment.yaml"

# Wait for Neo4j to be ready
echo -e "${YELLOW}Waiting for Neo4j to be ready...${NC}"
oc rollout status deployment/neo4j -n "$NAMESPACE" --timeout=300s

echo -e "${GREEN}Neo4j deployment complete!${NC}"

# Display connection information
echo ""
echo "============================================================"
echo "Neo4j Connection Information"
echo "============================================================"
echo ""
echo "Neo4j Browser URL:"
NEO4J_BROWSER=$(oc get route neo4j-browser -n "$NAMESPACE" -o jsonpath='{.spec.host}' 2>/dev/null || echo "Not available")
echo "  https://$NEO4J_BROWSER"
echo ""
echo "Neo4j Bolt URL (for applications):"
NEO4J_BOLT=$(oc get route neo4j-bolt -n "$NAMESPACE" -o jsonpath='{.spec.host}' 2>/dev/null || echo "Not available")
echo "  bolt+s://$NEO4J_BOLT:443"
echo ""
echo "Credentials:"
echo "  Username: neo4j"
echo "  Password: (set via NEO4J_PASSWORD environment variable)"
echo ""

# Ask if user wants to load sample data
read -p "Would you like to load the FSI sample data? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Loading FSI sample data...${NC}"
    oc apply -f "$OPENSHIFT_DIR/fsi-data-loader.yaml"
    
    echo "Waiting for data loader job to complete..."
    oc wait --for=condition=complete job/fsi-data-loader -n "$NAMESPACE" --timeout=120s || true
    
    echo -e "${GREEN}Sample data loaded!${NC}"
fi

echo ""
echo "============================================================"
echo -e "${GREEN}Deployment Complete!${NC}"
echo "============================================================"
echo ""
echo "Next steps:"
echo "1. Update config.yaml with the Neo4j connection details"
echo "2. Run the FSI demo: python examples/fsi_demo.py"
echo ""
