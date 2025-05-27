#!/bin/bash

# KRR CRD Example Script
# This script demonstrates how to use KRR with CRDs

echo "=== KRR CRD Example ==="
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "kubectl is required but not installed. Please install kubectl first."
    exit 1
fi

# Check if krr is available
if ! command -v krr &> /dev/null; then
    echo "krr is required but not installed. Please install krr first."
    exit 1
fi

# Function to wait for user input
wait_for_enter() {
    echo ""
    read -p "Press Enter to continue..."
    echo ""
}

echo "Step 1: Installing KRR CRDs"
echo "=========================="
echo "First, we need to install the CRD definitions in your cluster:"
echo ""
echo "kubectl apply -f ../manifests/crds/"
wait_for_enter

# Install CRDs
kubectl apply -f ../manifests/crds/

echo ""
echo "Step 2: Verify CRDs are installed"
echo "================================="
echo "kubectl get crd | grep krr"
echo ""
kubectl get crd | grep krr

wait_for_enter

echo "Step 3: Generate recommendations as CRDs"
echo "========================================"
echo "Now let's run KRR and output recommendations as CRDs:"
echo ""
echo "krr simple -f crd --fileoutput recommendations-demo.yaml"
wait_for_enter

# Generate recommendations
krr simple -f crd --fileoutput recommendations-demo.yaml

echo ""
echo "Step 4: Review the generated CRDs"
echo "================================="
echo "Let's look at the first 50 lines of the output:"
echo ""
head -n 50 recommendations-demo.yaml

wait_for_enter

echo "Step 5: Apply CRDs to cluster (dry-run)"
echo "========================================"
echo "Let's validate the CRDs without actually applying them:"
echo ""
echo "kubectl apply -f recommendations-demo.yaml --dry-run=client"
echo ""
kubectl apply -f recommendations-demo.yaml --dry-run=client

wait_for_enter

echo "Step 6: Apply CRDs to cluster"
echo "============================="
echo "Now let's actually apply the CRDs to the cluster:"
echo ""
echo "kubectl apply -f recommendations-demo.yaml"
read -p "Do you want to apply the CRDs? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    kubectl apply -f recommendations-demo.yaml
    echo ""
    echo "CRDs applied successfully!"
else
    echo "Skipping CRD application."
fi

wait_for_enter

echo "Step 7: View recommendations"
echo "==========================="
echo "List all recommendations:"
echo ""
echo "kubectl get resourcerecommendations -A"
kubectl get resourcerecommendations -A

echo ""
echo "List recommendation reports:"
echo ""
echo "kubectl get recommendationreports -A"
kubectl get recommendationreports -A

wait_for_enter

echo "Step 8: Filter recommendations"
echo "=============================="
echo "Find critical recommendations:"
echo ""
echo "kubectl get rr -A -l krr.robusta.dev/severity=critical"
kubectl get rr -A -l krr.robusta.dev/severity=critical

echo ""
echo "Find recommendations for deployments:"
echo ""
echo "kubectl get rr -A -l krr.robusta.dev/workload-kind=deployment"
kubectl get rr -A -l krr.robusta.dev/workload-kind=deployment

wait_for_enter

echo "Step 9: View detailed recommendation"
echo "===================================="
echo "Get the name of the first recommendation:"
REC_NAME=$(kubectl get rr -A -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
REC_NS=$(kubectl get rr -A -o jsonpath='{.items[0].metadata.namespace}' 2>/dev/null)

if [ -n "$REC_NAME" ]; then
    echo "Viewing recommendation: $REC_NAME in namespace: $REC_NS"
    echo ""
    echo "kubectl describe rr $REC_NAME -n $REC_NS"
    kubectl describe rr $REC_NAME -n $REC_NS
else
    echo "No recommendations found to display."
fi

wait_for_enter

echo "Step 10: Cleanup (Optional)"
echo "==========================="
echo "To clean up the demo CRDs:"
echo ""
echo "kubectl delete -f recommendations-demo.yaml"
read -p "Do you want to delete the demo CRDs? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    kubectl delete -f recommendations-demo.yaml
    echo "Demo CRDs deleted."
else
    echo "Keeping demo CRDs."
fi

echo ""
echo "=== Demo Complete ==="
echo ""
echo "You've learned how to:"
echo "1. Install KRR CRDs"
echo "2. Generate recommendations as CRDs"
echo "3. Apply CRDs to your cluster"
echo "4. View and filter recommendations"
echo "5. Use kubectl to manage recommendations"
echo ""
echo "For more information, see docs/crd-usage.md" 