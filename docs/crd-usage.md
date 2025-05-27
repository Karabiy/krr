# KRR CRD Usage Guide

This guide explains how to use KRR's Custom Resource Definition (CRD) output format to manage recommendations as Kubernetes resources.

## Overview

KRR can output recommendations as Kubernetes Custom Resources (CRDs), enabling:
- GitOps workflows for recommendation management
- Audit trails of all recommendations
- Integration with Kubernetes tooling
- Future automation capabilities

## Installation

### 1. Install the CRDs

First, install the KRR CRDs in your cluster:

```bash
# Install both CRDs
kubectl apply -f https://raw.githubusercontent.com/robusta-dev/krr/main/manifests/crds/resourcerecommendation-crd.yaml
kubectl apply -f https://raw.githubusercontent.com/robusta-dev/krr/main/manifests/crds/recommendationreport-crd.yaml

# Or install from local files
kubectl apply -f manifests/crds/
```

Verify the CRDs are installed:

```bash
kubectl get crd | grep krr
# Should show:
# recommendationreports.krr.robusta.dev
# resourcerecommendations.krr.robusta.dev
```

### 2. Required RBAC Permissions

If running KRR in-cluster, ensure it has permissions to create CRDs:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: krr-crd-writer
rules:
- apiGroups: ["krr.robusta.dev"]
  resources: ["resourcerecommendations", "recommendationreports"]
  verbs: ["create", "update", "patch", "get", "list"]
```

## Usage

### Basic Usage

Generate recommendations as CRDs:

```bash
# Output CRDs to stdout
krr simple -f crd

# Save CRDs to a file
krr simple -f crd --fileoutput recommendations.yaml

# Apply directly to cluster (be careful!)
krr simple -f crd | kubectl apply -f -
```

### GitOps Workflow

1. Generate recommendations and save to Git:

```bash
# Create a directory for recommendations
mkdir -p k8s/recommendations/$(date +%Y%m%d)

# Generate CRDs
krr simple -f crd --fileoutput k8s/recommendations/$(date +%Y%m%d)/recommendations.yaml

# Commit to Git
git add k8s/recommendations/
git commit -m "KRR recommendations - $(date)"
git push
```

2. Review the recommendations in your Git repository

3. Apply through your GitOps tool (ArgoCD, Flux, etc.)

### Viewing Recommendations

```bash
# List all recommendations
kubectl get resourcerecommendations -A

# List recommendations with details
kubectl get rr -A -o wide

# View a specific recommendation
kubectl describe rr nginx-deployment-20240128-141523 -n default

# List all reports
kubectl get recommendationreports -A

# View report summary
kubectl get rrep -A -o wide
```

### Filtering and Querying

```bash
# Find critical recommendations
kubectl get rr -A -l krr.robusta.dev/severity=critical

# Find recommendations for specific workload type
kubectl get rr -A -l krr.robusta.dev/workload-kind=deployment

# Find recommendations from a specific scan
kubectl get rr -A -l krr.robusta.dev/scan-id=20240128-141523

# Export recommendations for a namespace
kubectl get rr -n production -o yaml > production-recommendations.yaml
```

## Understanding the CRDs

### ResourceRecommendation

Each `ResourceRecommendation` represents recommendations for a single workload/container:

```yaml
apiVersion: krr.robusta.dev/v1alpha1
kind: ResourceRecommendation
metadata:
  name: nginx-deployment-nginx-20240128-141523
  namespace: default
  labels:
    krr.robusta.dev/workload-name: nginx-deployment
    krr.robusta.dev/workload-kind: deployment
    krr.robusta.dev/severity: warning
spec:
  targetRef:
    kind: Deployment
    name: nginx-deployment
    namespace: default
  recommendations:
    containers:
    - name: nginx
      resources:
        cpu:
          request: "100m"
          limit: "500m"
        memory:
          request: "128Mi"
          limit: "512Mi"
  analysis:
    strategy: simple
    historyDuration: "336h"
    dataPoints: 50
    confidence: 0.95
  impact:
    estimatedSavings:
      cpu: "400m"
      memory: "384Mi"
    severity: warning
status:
  phase: pending
```

### RecommendationReport

Each scan creates one `RecommendationReport` that aggregates all recommendations:

```yaml
apiVersion: krr.robusta.dev/v1alpha1
kind: RecommendationReport
metadata:
  name: krr-report-20240128-141523
  namespace: default
spec:
  scanTime: "2024-01-28T14:15:23Z"
  scope:
    clusters: ["production"]
    namespaces: ["default", "webapp"]
  summary:
    totalWorkloads: 15
    totalRecommendations: 23
    estimatedMonthlySavings: "245.50"
    bySeverity:
      critical: 3
      warning: 12
      ok: 5
      good: 3
status:
  phase: completed
  recommendationsCreated: 23
```

## Advanced Usage

### Approval Workflow

Mark recommendations as approved:

```bash
# Approve a specific recommendation
kubectl annotate rr nginx-deployment-20240128-141523 \
  krr.robusta.dev/approved="true" \
  krr.robusta.dev/approved-by="platform-team" \
  krr.robusta.dev/approved-at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### Exporting Applied Recommendations

Generate YAML patches from approved recommendations:

```bash
# Export approved recommendations as patches
kubectl get rr -A \
  -l krr.robusta.dev/approved=true \
  -o jsonpath='{range .items[*]}{.spec.targetRef.namespace}/{.spec.targetRef.name}{"\n"}{end}' | \
  while read workload; do
    # Generate patch commands
    echo "kubectl patch deployment $workload --patch '...'"
  done
```

### Cleanup Old Recommendations

```bash
# Delete recommendations older than 30 days
kubectl delete rr -A --field-selector metadata.creationTimestamp<$(date -d '30 days ago' --iso-8601)

# Delete all recommendations from a specific scan
kubectl delete rr -A -l krr.robusta.dev/scan-id=20240128-141523
```

## Best Practices

1. **Review Before Applying**: Always review CRD recommendations before applying to production
2. **Use Git for History**: Store CRDs in Git for versioning and audit trails
3. **Label Consistently**: Use labels to organize and filter recommendations
4. **Regular Cleanup**: Delete old recommendations to avoid clutter
5. **Monitor Applied Changes**: Track the actual impact of applied recommendations

## Troubleshooting

### CRDs Not Creating

```bash
# Check if CRDs are installed
kubectl get crd | grep krr

# Check for RBAC issues
kubectl auth can-i create resourcerecommendations

# Check KRR logs
krr simple -f crd -v
```

### Invalid CRD Output

```bash
# Validate the output
krr simple -f crd | kubectl apply --dry-run=client -f -

# Check for naming conflicts
kubectl get rr -A | grep <workload-name>
```

## Future Enhancements

The CRD format enables future features like:
- Automated recommendation application with controllers
- Policy-based approval workflows
- Integration with cost management tools
- A/B testing of recommendations
- Rollback capabilities

## Examples

### Example 1: Namespace-Specific Scan

```bash
# Scan only production namespace and output as CRDs
krr simple -n production -f crd --fileoutput prod-recommendations.yaml

# Review the file
cat prod-recommendations.yaml

# Apply to a test cluster first
kubectl apply -f prod-recommendations.yaml --context=test-cluster
```

### Example 2: Integration with CI/CD

```yaml
# .gitlab-ci.yml example
krr-scan:
  stage: analyze
  script:
    - krr simple -f crd --fileoutput recommendations-$CI_COMMIT_SHA.yaml
    - git add recommendations-$CI_COMMIT_SHA.yaml
    - git commit -m "KRR recommendations for $CI_COMMIT_SHA"
    - git push origin krr-recommendations-$CI_COMMIT_SHA
  only:
    - schedules
```

### Example 3: Monitoring with Prometheus

```yaml
# Create metrics from CRDs
apiVersion: v1
kind: ConfigMap
metadata:
  name: krr-metrics-query
data:
  query: |
    # Count recommendations by severity
    count by (severity) (
      kube_customresource_resourcerecommendation_info{severity=~"critical|warning"}
    )
``` 