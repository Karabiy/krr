# KRR Testing Checklist

This document outlines what needs to be tested for the Sprint 1-2 and Sprint 3-4 implementations. Since you're on a Windows machine without a Kubernetes cluster, these tests should be performed when you have access to a proper environment.

## Prerequisites for Testing

- [ ] Python environment with KRR installed
- [ ] Access to a Kubernetes cluster (minikube, kind, or cloud)
- [ ] kubectl configured and working
- [ ] Prometheus instance with workload metrics (or demo data)
- [ ] Sample workloads deployed in the cluster

## Sprint 1-2: Quick Wins Testing

### 1. YAML Manifest Export Testing

**Test the new yaml-manifests formatter:**

```bash
# Basic test - output to console
krr simple -f yaml-manifests

# Test file output
krr simple -f yaml-manifests --fileoutput test-manifests.yaml

# Verify the output is valid Kubernetes YAML
kubectl apply -f test-manifests.yaml --dry-run=client

# Test with different resource types
krr simple -f yaml-manifests -r Deployment
krr simple -f yaml-manifests -r StatefulSet
krr simple -f yaml-manifests -r DaemonSet
```

**Expected Results:**
- [ ] Valid YAML output with proper Kubernetes resource structure
- [ ] Each workload separated by `---`
- [ ] Correct apiVersion, kind, metadata, and spec fields
- [ ] Resource values properly formatted (e.g., "100m" for CPU, "128Mi" for memory)
- [ ] KRR annotations present in metadata

### 2. Summary Statistics Testing

**Test the enhanced table formatter:**

```bash
# Default table output should show summary
krr simple

# Test with different namespaces
krr simple -n default
krr simple -n kube-system

# Test with no results
krr simple -n non-existent-namespace

# Test with file output
krr simple --fileoutput report.txt
```

**Expected Results:**
- [ ] Summary panel appears at the top of table output
- [ ] Correct total workloads and containers count
- [ ] Accurate severity breakdown (Critical, Warning, OK, Good)
- [ ] Correct CPU and Memory savings calculations
- [ ] Percentage reduction calculations are accurate
- [ ] Current vs recommended totals are correct
- [ ] Workload type breakdown is accurate

### 3. Configuration File Support Testing

**Test config file loading:**

```bash
# Create a test config file
cp .krr.yaml.example .krr.yaml

# Edit .krr.yaml with test values
# Set cpu_min_value: 50
# Set memory_min_value: 200
# Set format: json

# Test auto-discovery
cd /path/to/project
krr simple  # Should use .krr.yaml settings

# Test explicit config file
krr simple --config custom-config.yaml

# Test CLI override
krr simple --cpu-min 100  # Should override config file

# Test from subdirectory
mkdir subdir && cd subdir
krr simple  # Should find parent .krr.yaml
```

**Expected Results:**
- [ ] Config file is auto-discovered from current or parent directories
- [ ] Settings from config file are applied
- [ ] CLI arguments override config file settings
- [ ] Invalid config files show appropriate errors
- [ ] All KRR settings can be specified in config

### 4. Progress Indicators Testing

**Test progress bars:**

```bash
# Normal run - should show progress
krr simple

# Large cluster test
krr simple --all-clusters

# Quiet mode - no progress
krr simple -q

# Log to stderr - no progress
krr simple --logtostderr

# Test with multiple namespaces
krr simple -n default -n kube-system -n production
```

**Expected Results:**
- [ ] Progress bar appears during workload discovery
- [ ] Progress bar appears during recommendation calculation
- [ ] Progress shows current item and ETA
- [ ] Progress bars disappear after completion (transient)
- [ ] No progress in quiet mode or log-to-stderr mode
- [ ] Multi-cluster shows progress per cluster

## Sprint 3-4: CRD Phase 1 Testing

### 1. CRD Installation Testing

**Test CRD installation:**

```bash
# Install CRDs
cd manifests/crds
./install.sh

# Or manual install
kubectl apply -f resourcerecommendation-crd.yaml
kubectl apply -f recommendationreport-crd.yaml

# Verify installation
kubectl get crd | grep krr
kubectl describe crd resourcerecommendations.krr.robusta.dev
kubectl describe crd recommendationreports.krr.robusta.dev
```

**Expected Results:**
- [ ] Both CRDs install without errors
- [ ] CRDs show as "Established" and "NamesAccepted"
- [ ] Short names work: `rr`, `resrec`, `rrep`, `recreport`
- [ ] OpenAPI schema validation is present

### 2. CRD Formatter Testing

**Test the CRD formatter:**

```bash
# Basic test
krr simple -f crd

# File output
krr simple -f crd --fileoutput test-crds.yaml

# Validate output
kubectl apply -f test-crds.yaml --dry-run=client

# Apply to cluster
kubectl apply -f test-crds.yaml

# Test with specific namespaces
krr simple -n default -f crd

# Test with no workloads
krr simple -n empty-namespace -f crd
```

**Expected Results:**
- [ ] Valid CRD resources generated
- [ ] Unique names for each recommendation (no conflicts)
- [ ] Correct labels and annotations
- [ ] RecommendationReport references all ResourceRecommendations
- [ ] Cost calculations present and reasonable
- [ ] All required fields populated

### 3. CRD Querying Testing

**Test kubectl operations:**

```bash
# List recommendations
kubectl get resourcerecommendations -A
kubectl get rr -A -o wide

# List reports
kubectl get recommendationreports -A
kubectl get rrep -A -o wide

# Filter by labels
kubectl get rr -A -l krr.robusta.dev/severity=critical
kubectl get rr -A -l krr.robusta.dev/workload-kind=deployment
kubectl get rr -A -l krr.robusta.dev/scan-id=20240128-141523

# Describe resources
kubectl describe rr <name> -n <namespace>
kubectl describe rrep <name> -n default

# Export as YAML
kubectl get rr -n default -o yaml
```

**Expected Results:**
- [ ] All kubectl commands work as expected
- [ ] Custom printer columns show correct data
- [ ] Label filtering works correctly
- [ ] Resource descriptions show all fields
- [ ] YAML export maintains all data

### 4. Example Script Testing

**Test the demo script:**

```bash
cd examples
chmod +x crd-example.sh
./crd-example.sh
```

**Expected Results:**
- [ ] Script runs without errors
- [ ] Each step completes successfully
- [ ] User prompts work correctly
- [ ] CRDs are created and viewable
- [ ] Cleanup removes all demo resources

## Integration Testing

### 1. End-to-End Workflow

```bash
# Create config file
cat > .krr.yaml <<EOF
format: crd
cpu_min_value: 20
memory_min_value: 150
show_cluster_name: true
EOF

# Run with all features
krr simple  # Uses config, shows progress, outputs CRDs

# Apply and verify
krr simple | kubectl apply -f -
kubectl get rr -A
```

### 2. GitOps Workflow Simulation

```bash
# Create directory structure
mkdir -p k8s/recommendations

# Generate recommendations
krr simple -f crd --fileoutput k8s/recommendations/$(date +%Y%m%d).yaml

# Simulate Git workflow
git add k8s/recommendations/
git status  # Should show new files
```

### 3. Error Handling

**Test various error scenarios:**

- [ ] Run without CRDs installed (should fail gracefully)
- [ ] Invalid config file (should show clear error)
- [ ] No Prometheus available (should handle gracefully)
- [ ] No workloads found (should show appropriate message)
- [ ] Conflicting CRD names (should handle uniqueness)

## Performance Testing

### 1. Large Scale Testing

```bash
# Test with many workloads
krr simple --all-namespaces -f crd

# Monitor performance
time krr simple -f table
time krr simple -f crd
time krr simple -f yaml-manifests
```

**Expected Results:**
- [ ] Progress bars help with long operations
- [ ] CRD generation doesn't significantly slow down
- [ ] Memory usage remains reasonable
- [ ] All formatters complete successfully

## Regression Testing

### 1. Existing Features

Ensure all existing features still work:

- [ ] Original formatters: table, json, yaml, csv
- [ ] All CLI flags work as before
- [ ] Multi-cluster support unchanged
- [ ] Strategy options work correctly
- [ ] Prometheus integration unchanged

### 2. Backward Compatibility

- [ ] Existing scripts/automation continue to work
- [ ] No breaking changes in output format
- [ ] Default behavior unchanged (table format)

## Documentation Testing

### 1. Documentation Accuracy

- [ ] All code examples in docs work
- [ ] Installation instructions are correct
- [ ] CRD usage guide examples are valid
- [ ] Config file example has all options

### 2. Help Text

```bash
krr --help
krr simple --help
```

- [ ] New formatters listed in help
- [ ] Config file option documented
- [ ] All options have descriptions

## Notes for Windows Testing

When you get access to a proper environment, prioritize:

1. **Basic functionality**: Ensure formatters work
2. **CRD installation**: Critical for Sprint 3-4
3. **Config file**: Test path handling on different OS
4. **Progress bars**: May behave differently on Windows terminals

Consider using:
- WSL2 with a local Kubernetes (minikube/kind)
- A cloud-based Kubernetes cluster
- A Linux VM or container for testing

## Test Data Requirements

For comprehensive testing, you'll need:

1. A cluster with various workload types (Deployment, StatefulSet, DaemonSet)
2. Workloads with different resource patterns (over/under provisioned)
3. At least 14 days of Prometheus metrics
4. Multiple namespaces with different workloads
5. Some workloads without metrics (to test edge cases)

## Success Criteria

All tests pass when:
- [ ] No errors or exceptions during normal operation
- [ ] All new features work as documented
- [ ] No regressions in existing functionality
- [ ] Performance is acceptable for large clusters
- [ ] Documentation matches implementation
- [ ] Error messages are clear and helpful

## Sprint 5-6: Cost Integration Testing

### 1. Basic Cost Provider Testing

**Test without cost provider (default behavior):**

```bash
# Should work normally without any cost provider
krr simple

# Verify rough estimates are still shown
krr simple -f crd | grep monthlyCost
```

**Expected Results:**
- [ ] KRR works normally without cost provider
- [ ] Default cost estimates are shown (rough calculations)
- [ ] No errors about missing cost providers

### 2. Vantage Provider Testing

**Test with Vantage API:**

```bash
# Set API key
export VANTAGE_API_KEY=your_test_key

# Test basic functionality
krr simple --cost-provider vantage

# Test with invalid API key
krr simple --cost-provider vantage --vantage-api-key invalid_key

# Test different currencies
krr simple --cost-provider vantage --cost-currency EUR
krr simple --cost-provider vantage --cost-currency GBP

# Test cache behavior
krr simple --cost-provider vantage --cost-cache-hours 0  # No cache
krr simple --cost-provider vantage --cost-cache-hours 48  # 2 days
```

**Expected Results:**
- [ ] Valid API key shows accurate cost data
- [ ] Invalid API key falls back to estimates gracefully
- [ ] Currency conversion works correctly
- [ ] Cache prevents repeated API calls
- [ ] Cost data appears in all output formats

### 3. Configuration File Testing

**Test cost settings in config:**

```bash
# Create test config
cat > .krr.yaml <<EOF
cost_provider: vantage
vantage_api_key: ${VANTAGE_API_KEY}
cost_currency: EUR
cost_cache_hours: 12
EOF

# Run with config
krr simple

# Override with CLI
krr simple --cost-currency USD
```

**Expected Results:**
- [ ] Config file cost settings are loaded
- [ ] Environment variables in config work
- [ ] CLI overrides config settings
- [ ] No cost provider in config works fine

### 4. Output Format Testing

**Test cost data in different formats:**

```bash
# Table format with costs
krr simple --cost-provider vantage -f table

# CRD format with cost breakdown
krr simple --cost-provider vantage -f crd

# JSON format
krr simple --cost-provider vantage -f json | jq '.scans[0].object.allocations.cost_data'

# CSV format
krr simple --cost-provider vantage -f csv
```

**Expected Results:**
- [ ] Table shows cost savings in summary
- [ ] CRD includes detailed cost breakdown
- [ ] JSON contains cost_data field
- [ ] CSV includes cost columns
- [ ] YAML manifests show cost annotations

### 5. Error Handling Testing

**Test various error scenarios:**

```bash
# No API key
unset VANTAGE_API_KEY
krr simple --cost-provider vantage

# Network timeout (disconnect network)
krr simple --cost-provider vantage --vantage-api-key test_key

# Rate limiting (make many requests)
for i in {1..100}; do
  krr simple --cost-provider vantage -n default &
done

# Unknown instance types
# (Test with cluster that has custom node types)
```

**Expected Results:**
- [ ] Missing API key shows warning, uses estimates
- [ ] Network errors don't crash KRR
- [ ] Rate limits are handled with backoff
- [ ] Unknown instance types skip cost calculation
- [ ] Errors are logged but don't stop scan

### 6. Performance Testing

**Test performance impact:**

```bash
# Time without cost provider
time krr simple -q

# Time with cost provider
time krr simple --cost-provider vantage -q

# Large cluster test
time krr simple --cost-provider vantage --all-namespaces
```

**Expected Results:**
- [ ] Cost provider adds <100ms for small clusters
- [ ] Cache significantly improves performance
- [ ] Large clusters don't timeout
- [ ] Async loading doesn't block recommendations

### 7. Instance Type Detection

**Test node instance type mapping:**

```bash
# Check node labels
kubectl get nodes -o json | jq '.items[].metadata.labels | select(."node.kubernetes.io/instance-type")'

# Run KRR with verbose to see instance detection
krr simple --cost-provider vantage -v | grep "instance type"
```

**Expected Results:**
- [ ] Instance types correctly detected from labels
- [ ] EKS instance types detected
- [ ] Missing instance types handled gracefully
- [ ] Region correctly identified

### 8. Integration Testing

**Test with real AWS cluster:**

```bash
# Connect to EKS cluster
aws eks update-kubeconfig --name my-cluster

# Run full scan with costs
krr simple --cost-provider vantage \
  --vantage-api-key $VANTAGE_API_KEY \
  -f crd \
  --fileoutput cost-recommendations.yaml

# Verify costs match AWS pricing
kubectl get nodes -o json | jq '.items[].metadata.labels."node.kubernetes.io/instance-type"'
# Compare with AWS pricing for those instances
```

**Expected Results:**
- [ ] Costs match AWS pricing pages
- [ ] Multi-region clusters work correctly
- [ ] Mixed instance types handled
- [ ] Spot instances detected (if applicable)

## Cost Integration Success Criteria

The cost integration feature is successful when:
- [ ] Works seamlessly when disabled (default)
- [ ] Provides accurate costs when enabled
- [ ] Handles all error cases gracefully
- [ ] Minimal performance impact
- [ ] Clear documentation and examples
- [ ] Supports multiple currencies
- [ ] Easy to add new providers 