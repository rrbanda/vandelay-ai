#!/bin/bash
# =============================================================================
# Run Migration Graph Ingestion on OpenShift
# =============================================================================
# This script sets up ConfigMaps, Secrets, and runs the ingestion Job.
#
# Usage:
#   ./run-ingest.sh [NEO4J_SERVICE_NAME] [NEO4J_PASSWORD]
#
# Examples:
#   ./run-ingest.sh neo4j mypassword
#   ./run-ingest.sh neo4j-service.my-namespace.svc.cluster.local mypassword
# =============================================================================

set -e

# Defaults
NEO4J_SERVICE="${1:-neo4j}"
NEO4J_PASSWORD="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSV_DIR="${SCRIPT_DIR}/../data/migration_csv"

echo "=============================================="
echo "Migration Graph Ingestion - OpenShift"
echo "=============================================="
echo "Neo4j Service: $NEO4J_SERVICE"
echo "CSV Directory: $CSV_DIR"
echo ""

# Check if password provided
if [ -z "$NEO4J_PASSWORD" ]; then
    echo "Usage: $0 [NEO4J_SERVICE] [NEO4J_PASSWORD]"
    echo ""
    echo "Or set NEO4J_PASSWORD environment variable"
    exit 1
fi

# Check CSV files exist
if [ ! -f "$CSV_DIR/namespaces.csv" ]; then
    echo "ERROR: namespaces.csv not found in $CSV_DIR"
    exit 1
fi

echo "Step 1: Creating ConfigMap with CSV data..."
oc delete configmap migration-csv-data --ignore-not-found=true
oc create configmap migration-csv-data \
    --from-file=namespaces.csv="$CSV_DIR/namespaces.csv" \
    --from-file=cluster_mappings.csv="$CSV_DIR/cluster_mappings.csv" \
    --from-file=cluster_configs.csv="$CSV_DIR/cluster_configs.csv" \
    --from-file=migration_phases.csv="$CSV_DIR/migration_phases.csv" \
    --from-file=storage_classes.csv="$CSV_DIR/storage_classes.csv"
echo "  [OK] ConfigMap created"

echo ""
echo "Step 2: Creating ConfigMap with Python script..."
oc delete configmap migration-ingest-script --ignore-not-found=true
oc create configmap migration-ingest-script \
    --from-file=standalone_ingest.py="$SCRIPT_DIR/../standalone_ingest.py"
echo "  [OK] Script ConfigMap created"

echo ""
echo "Step 3: Creating Secret with Neo4j credentials..."
oc delete secret neo4j-credentials --ignore-not-found=true
oc create secret generic neo4j-credentials \
    --from-literal=NEO4J_PASSWORD="$NEO4J_PASSWORD"
echo "  [OK] Secret created"

echo ""
echo "Step 4: Updating Job with Neo4j service name..."
# Create a temp file with updated NEO4J_URI
sed "s|bolt://neo4j:7687|bolt://${NEO4J_SERVICE}:7687|g" \
    "$SCRIPT_DIR/migration-ingest-job.yaml" > /tmp/migration-ingest-job.yaml

echo ""
echo "Step 5: Deleting old job if exists..."
oc delete job migration-graph-ingest --ignore-not-found=true

echo ""
echo "Step 6: Running ingestion job..."
oc apply -f /tmp/migration-ingest-job.yaml
echo "  [OK] Job created"

echo ""
echo "Step 7: Waiting for job to start..."
sleep 3

echo ""
echo "=============================================="
echo "Streaming job logs (Ctrl+C to exit)..."
echo "=============================================="
oc logs -f job/migration-graph-ingest || true

echo ""
echo "=============================================="
echo "Job Status:"
oc get job migration-graph-ingest -o wide
echo "=============================================="
