#!/bin/bash

# KRR CRD Installation Script

echo "Installing KRR Custom Resource Definitions..."
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is required but not installed."
    echo "Please install kubectl: https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

# Check if we can connect to a cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "Error: Cannot connect to Kubernetes cluster."
    echo "Please ensure kubectl is configured correctly."
    exit 1
fi

# Install CRDs
echo "Installing ResourceRecommendation CRD..."
kubectl apply -f resourcerecommendation-crd.yaml

echo "Installing RecommendationReport CRD..."
kubectl apply -f recommendationreport-crd.yaml

echo ""
echo "Verifying installation..."
kubectl get crd | grep krr.robusta.dev

echo ""
echo "Installation complete!"
echo ""
echo "You can now use 'krr simple -f crd' to generate recommendations as CRDs."
echo "See ../../docs/crd-usage.md for detailed usage instructions." 