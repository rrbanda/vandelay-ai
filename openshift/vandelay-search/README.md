# Vandelay Search - OpenShift/Podman Deployment

This directory contains Kubernetes-style YAML manifests for deploying the Vandelay Search FSI GraphRAG Agent.

- **Local Development**: Use with Podman Desktop
- **Production**: Deploy to OpenShift

## Prerequisites

1. **Podman Desktop** installed (for local testing)
2. **OpenShift CLI (`oc`)** installed (for OpenShift deployment)
3. **Neo4j** database running
4. **LlamaStack** vector store accessible

---

## Quick Start: Podman Desktop (Local)

### 1. Create Environment File (REQUIRED - secrets not in git!)

```bash
# Copy template and edit with your values
cp env.template .env

# Edit .env with your actual credentials:
# - NEO4J_PASSWORD
# - OPENAI_API_KEY (if needed)
# - etc.
```

### 2. Build and Run with Script

```bash
# Make script executable (first time only)
chmod +x run-local.sh

# Build and run
./run-local.sh

# Other commands:
./run-local.sh logs    # View logs
./run-local.sh stop    # Stop container
./run-local.sh shell   # Enter container
./run-local.sh restart # Rebuild and restart
```

### 3. Or Run Manually

```bash
# From repository root
cd /path/to/vandelay-ai

# Build image
podman build -t vandelay-search:latest -f vandelay_search/Dockerfile vandelay_search/

# Run with env file
podman run -d \
  --name vandelay-search-pod \
  --env-file openshift/vandelay-search/.env \
  -p 8000:8000 \
  vandelay-search:latest

# Access at http://localhost:8000
```

### 4. Using Podman Kube Play

```bash
# Start the pod (uses hardcoded env in pod.yaml - update values first!)
podman kube play openshift/vandelay-search/pod.yaml

# View logs
podman logs -f vandelay-search-pod-vandelay-search

# Stop the pod
podman kube down openshift/vandelay-search/pod.yaml
```

---

## OpenShift Deployment (Production)

### 1. Login to OpenShift

```bash
oc login --server=https://api.your-cluster.example.com:6443
```

### 2. Create Project/Namespace

```bash
oc new-project vandelay-search
# Or apply the namespace manifest:
oc apply -f openshift/vandelay-search/namespace.yaml
```

### 3. Create Secrets (Do this FIRST - don't commit real values!)

```bash
oc create secret generic vandelay-search-secrets \
  --from-literal=NEO4J_PASSWORD='your-actual-password' \
  --from-literal=OPENAI_API_KEY='your-actual-key' \
  -n vandelay-search
```

### 4. Build and Push Image

```bash
# Option A: Build locally and push to OpenShift internal registry
podman build -t vandelay-search:latest -f vandelay_search/Dockerfile vandelay_search/
podman tag vandelay-search:latest default-route-openshift-image-registry.apps.your-cluster.example.com/vandelay-search/vandelay-search:latest
podman push default-route-openshift-image-registry.apps.your-cluster.example.com/vandelay-search/vandelay-search:latest

# Option B: Use OpenShift BuildConfig (recommended)
oc new-build --binary --name=vandelay-search -n vandelay-search
oc start-build vandelay-search --from-dir=vandelay_search --follow -n vandelay-search
```

### 5. Deploy Application

```bash
# Apply all resources with kustomize
oc apply -k openshift/vandelay-search/

# Or apply individually:
oc apply -f openshift/vandelay-search/configmap.yaml
oc apply -f openshift/vandelay-search/deployment.yaml
oc apply -f openshift/vandelay-search/service.yaml
oc apply -f openshift/vandelay-search/route.yaml
```

### 6. Get the Route URL

```bash
oc get route vandelay-search -n vandelay-search -o jsonpath='{.spec.host}'
```

---

## File Descriptions

| File | Description | Podman | OpenShift |
|------|-------------|--------|-----------|
| `namespace.yaml` | Creates the namespace/project | ✓ | ✓ |
| `configmap.yaml` | Non-sensitive configuration | ✓ | ✓ |
| `secret.yaml` | Secrets template (change values!) | ✓ | ✓ |
| `deployment.yaml` | Deployment with health checks | ✓ | ✓ |
| `service.yaml` | Service (NodePort/ClusterIP) | ✓ | ✓ |
| `route.yaml` | External route | ✗ | ✓ |
| `pod.yaml` | Simple pod for quick testing | ✓ | ✗ |
| `kustomization.yaml` | Kustomize configuration | ✓ | ✓ |

---

## Configuration

### Environment Variables

| Variable | Description | Where to Set |
|----------|-------------|--------------|
| `NEO4J_URI` | Neo4j connection URI | ConfigMap |
| `NEO4J_USERNAME` | Neo4j username | ConfigMap |
| `NEO4J_PASSWORD` | Neo4j password | **Secret** |
| `OPENAI_API_BASE` | LLM API endpoint | ConfigMap |
| `OPENAI_API_KEY` | LLM API key | **Secret** |
| `ADK_MODEL` | Model identifier | ConfigMap |
| `LLAMASTACK_BASE_URL` | Vector store URL | ConfigMap |
| `VECTOR_STORE_ID` | Vector store ID | ConfigMap |
| `VECTOR_STORE_VERIFY_SSL` | SSL verification | ConfigMap |

### Connecting to Services

| Environment | Neo4j Host |
|-------------|------------|
| Podman Desktop | `host.containers.internal:7687` |
| OpenShift (same namespace) | `neo4j-service:7687` |
| OpenShift (different namespace) | `neo4j-service.other-namespace.svc:7687` |

---

## Updating for OpenShift

When moving from Podman Desktop to OpenShift:

1. **Update image reference** in `deployment.yaml`:
   ```yaml
   image: image-registry.openshift-image-registry.svc:5000/vandelay-search/vandelay-search:latest
   ```

2. **Change service type** in `service.yaml` (optional):
   ```yaml
   type: ClusterIP  # Use with Route instead of NodePort
   ```

3. **Enable Route** in `kustomization.yaml`:
   ```yaml
   resources:
     - route.yaml  # Uncomment this line
   ```

4. **Create real secrets** via CLI (don't use secret.yaml with real values)

---

## Troubleshooting

### Podman Desktop

```bash
# Check pod status
podman pod ps
podman ps -a

# View logs
podman logs vandelay-search-pod-vandelay-search

# Enter container shell
podman exec -it vandelay-search-pod-vandelay-search /bin/bash

# Network issues - use host.containers.internal for host services
```

### OpenShift

```bash
# Check pod status
oc get pods -n vandelay-search
oc describe pod <pod-name> -n vandelay-search

# View logs
oc logs -f deployment/vandelay-search -n vandelay-search

# Check events
oc get events -n vandelay-search --sort-by='.lastTimestamp'

# Debug container
oc debug deployment/vandelay-search -n vandelay-search
```

---

## References

- [ADK Deployment Docs](https://google.github.io/adk-docs/deploy/)
- [ADK Cloud Run Guide](https://google.github.io/adk-docs/deploy/cloud-run/)
- [OpenShift Documentation](https://docs.openshift.com/)
- [Podman Kube Play](https://docs.podman.io/en/latest/markdown/podman-kube-play.1.html)
- [ADK Samples Repository](https://github.com/google/adk-samples)
