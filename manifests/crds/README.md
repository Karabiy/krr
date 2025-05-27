# KRR Custom Resource Definitions

This directory contains the Custom Resource Definitions (CRDs) for KRR.

## CRDs Included

1. **ResourceRecommendation** (`resourcerecommendations.krr.robusta.dev`)
   - Represents recommendations for a single workload/container
   - Includes resource recommendations, analysis metadata, and impact assessment

2. **RecommendationReport** (`recommendationreports.krr.robusta.dev`)
   - Aggregates all recommendations from a single KRR scan
   - Provides summary statistics and references to individual recommendations

## Installation

### Quick Install

```bash
# Run the installation script
./install.sh

# Or install manually
kubectl apply -f resourcerecommendation-crd.yaml
kubectl apply -f recommendationreport-crd.yaml
```

### Install from URL

```bash
kubectl apply -f https://raw.githubusercontent.com/robusta-dev/krr/main/manifests/crds/resourcerecommendation-crd.yaml
kubectl apply -f https://raw.githubusercontent.com/robusta-dev/krr/main/manifests/crds/recommendationreport-crd.yaml
```

## Verification

```bash
# Check CRDs are installed
kubectl get crd | grep krr

# Expected output:
# recommendationreports.krr.robusta.dev       2024-01-28T10:00:00Z
# resourcerecommendations.krr.robusta.dev     2024-01-28T10:00:00Z
```

## Usage

After installing the CRDs, you can use KRR to generate recommendations as Custom Resources:

```bash
# Generate recommendations as CRDs
krr simple -f crd

# Save to file
krr simple -f crd --fileoutput recommendations.yaml

# Apply to cluster
krr simple -f crd | kubectl apply -f -
```

## Documentation

For detailed usage instructions, see [../../docs/crd-usage.md](../../docs/crd-usage.md)

## Uninstallation

```bash
# Remove all recommendations and reports
kubectl delete resourcerecommendations --all -A
kubectl delete recommendationreports --all -A

# Remove CRDs
kubectl delete crd resourcerecommendations.krr.robusta.dev
kubectl delete crd recommendationreports.krr.robusta.dev
``` 