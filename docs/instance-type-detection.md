# Instance Type Detection Guide

This guide explains how to detect which cloud instance types your Kubernetes nodes are running on, which is essential for accurate cost calculations in KRR.

## Quick Commands

### 1. Check Node Labels (Most Common Method)

```bash
# View all node labels
kubectl get nodes --show-labels

# Check specific instance type labels
kubectl get nodes -o json | jq '.items[] | {name: .metadata.name, instanceType: .metadata.labels["node.kubernetes.io/instance-type"]}'

# Alternative label locations
kubectl get nodes -o json | jq '.items[] | {
  name: .metadata.name,
  instanceType: (
    .metadata.labels["node.kubernetes.io/instance-type"] // 
    .metadata.labels["beta.kubernetes.io/instance-type"] //
    .metadata.labels["kops.k8s.io/instancegroup"] //
    "not found"
  )
}'
```

### 2. Check Node Provider ID

```bash
# Provider ID often contains instance information
kubectl get nodes -o json | jq '.items[] | {name: .metadata.name, providerID: .spec.providerID}'

# Example output:
# aws:///us-east-1a/i-0123456789abcdef0
```

### 3. Detailed Node Information

```bash
# Get comprehensive node details
kubectl describe nodes | grep -E "Name:|instance-type|ProviderID|node.kubernetes.io"
```

## Cloud-Specific Detection

### AWS (EKS, Self-managed)

```bash
# Method 1: Node labels
kubectl get nodes -o custom-columns=NAME:.metadata.name,INSTANCE:.metadata.labels.node\\.kubernetes\\.io/instance-type

# Method 2: From EC2 metadata (if you have node access)
aws ec2 describe-instances --instance-ids $(kubectl get nodes -o json | jq -r '.items[].spec.providerID' | cut -d'/' -f5) --query 'Reservations[*].Instances[*].[InstanceId,InstanceType]' --output table

# Method 3: Using node annotations
kubectl get nodes -o json | jq '.items[] | {
  name: .metadata.name,
  az: .metadata.labels["topology.kubernetes.io/zone"],
  instanceType: .metadata.labels["node.kubernetes.io/instance-type"],
  nodeGroup: .metadata.labels["eks.amazonaws.com/nodegroup"]
}'
```

### Azure (AKS)

```bash
# Azure uses different labels
kubectl get nodes -o json | jq '.items[] | {
  name: .metadata.name,
  vmSize: .metadata.labels["kubernetes.azure.com/agentpool"] // .metadata.labels["node.kubernetes.io/instance-type"],
  agentPool: .metadata.labels["agentpool"]
}'

# Get VM size from node labels
kubectl get nodes -o custom-columns=NAME:.metadata.name,SIZE:.metadata.labels.kubernetes\\.io/arch,AGENT:.metadata.labels.agentpool
```

### GCP (GKE)

```bash
# GCP instance types
kubectl get nodes -o json | jq '.items[] | {
  name: .metadata.name,
  machineType: .metadata.labels["beta.kubernetes.io/instance-type"] // .metadata.labels["cloud.google.com/machine-family"],
  zone: .metadata.labels["topology.kubernetes.io/zone"]
}'
```

## Common Label Patterns

### Standard Kubernetes Labels

```yaml
# Most common label for instance type
node.kubernetes.io/instance-type: m5.large

# Legacy label (still used in some clusters)
beta.kubernetes.io/instance-type: m5.large

# Region/Zone information
topology.kubernetes.io/region: us-east-1
topology.kubernetes.io/zone: us-east-1a
```

### Cloud Provider Labels

```yaml
# AWS/EKS specific
eks.amazonaws.com/nodegroup: my-nodegroup
eks.amazonaws.com/nodegroup-image: ami-12345678
kops.k8s.io/instancegroup: nodes-us-east-1a

# Azure/AKS specific
kubernetes.azure.com/agentpool: nodepool1
kubernetes.azure.com/cluster: my-aks-cluster

# GCP/GKE specific
cloud.google.com/gke-nodepool: default-pool
cloud.google.com/machine-family: n1
```

## Troubleshooting Missing Instance Types

### 1. Add Labels Manually

If instance type labels are missing, you can add them:

```bash
# Add instance type label to a node
kubectl label nodes <node-name> node.kubernetes.io/instance-type=m5.large

# Add to all nodes in a node group (be careful!)
kubectl label nodes -l eks.amazonaws.com/nodegroup=my-nodegroup node.kubernetes.io/instance-type=m5.large
```

### 2. Check Cloud Provider Console

Sometimes the easiest way is to check your cloud provider:

**AWS Console:**
1. Go to EC2 → Instances
2. Find instances with your cluster name
3. Check "Instance Type" column

**Azure Portal:**
1. Go to Virtual Machines
2. Filter by your AKS cluster
3. Check "Size" column

**GCP Console:**
1. Go to Compute Engine → VM instances
2. Filter by your GKE cluster
3. Check "Machine type" column

### 3. Use Cloud CLI Tools

```bash
# AWS - List all instances in cluster
aws ec2 describe-instances --filters "Name=tag:kubernetes.io/cluster/CLUSTER_NAME,Values=owned" --query 'Reservations[*].Instances[*].[InstanceId,InstanceType,Tags[?Key==`Name`].Value|[0]]' --output table

# Azure - List node pool VM sizes
az aks nodepool list --resource-group MY_RG --cluster-name MY_CLUSTER --query '[].{Name:name, VmSize:vmSize}' -o table

# GCP - List instance templates
gcloud compute instance-templates list --filter="name~'gke-CLUSTER_NAME'"
```

## Script to Detect All Instance Types

Save this as `detect-instance-types.sh`:

```bash
#!/bin/bash

echo "=== Kubernetes Node Instance Types ==="
echo ""

# Function to safely get label value
get_label() {
    local labels=$1
    local label=$2
    echo "$labels" | jq -r --arg l "$label" '.[$l] // "not found"'
}

# Get all nodes with their labels
kubectl get nodes -o json | jq -r '.items[] | @base64' | while read -r node; do
    # Decode node data
    _jq() {
        echo "$node" | base64 -d | jq -r "$@"
    }
    
    name=$(_jq '.metadata.name')
    labels=$(_jq '.metadata.labels')
    
    # Try different label patterns
    instance_type=$(get_label "$labels" "node.kubernetes.io/instance-type")
    if [ "$instance_type" = "not found" ]; then
        instance_type=$(get_label "$labels" "beta.kubernetes.io/instance-type")
    fi
    
    # Get additional info
    provider_id=$(_jq '.spec.providerID // "not found"')
    region=$(get_label "$labels" "topology.kubernetes.io/region")
    zone=$(get_label "$labels" "topology.kubernetes.io/zone")
    
    # Cloud-specific labels
    eks_nodegroup=$(get_label "$labels" "eks.amazonaws.com/nodegroup")
    aks_agentpool=$(get_label "$labels" "agentpool")
    gke_nodepool=$(get_label "$labels" "cloud.google.com/gke-nodepool")
    
    echo "Node: $name"
    echo "  Instance Type: $instance_type"
    echo "  Provider ID: $provider_id"
    echo "  Region/Zone: $region/$zone"
    
    [ "$eks_nodegroup" != "not found" ] && echo "  EKS Node Group: $eks_nodegroup"
    [ "$aks_agentpool" != "not found" ] && echo "  AKS Agent Pool: $aks_agentpool"
    [ "$gke_nodepool" != "not found" ] && echo "  GKE Node Pool: $gke_nodepool"
    
    echo ""
done
```

## Integration with KRR

KRR automatically looks for instance types in these locations:

1. `node.kubernetes.io/instance-type` label (primary)
2. `beta.kubernetes.io/instance-type` label (fallback)
3. Custom provider logic in `VantageCostProvider.map_node_to_instance_type()`

### Verify KRR Detection

Run KRR with verbose logging to see instance type detection:

```bash
# Check what KRR detects
krr simple --cost-provider vantage -v 2>&1 | grep -i "instance"
```

## Best Practices

1. **Standardize Labels**: Ensure all nodes have `node.kubernetes.io/instance-type`
2. **Automate Labeling**: Add instance type labeling to node provisioning
3. **Regular Audits**: Check for missing labels monthly
4. **Document Mapping**: Keep a mapping of node groups to instance types

## Example Output

Here's what properly labeled nodes look like:

```bash
$ kubectl get nodes -o custom-columns=NAME:.metadata.name,INSTANCE:.metadata.labels.node\\.kubernetes\\.io/instance-type,ZONE:.metadata.labels.topology\\.kubernetes\\.io/zone

NAME                          INSTANCE     ZONE
ip-10-0-1-100.ec2.internal   m5.large     us-east-1a
ip-10-0-2-200.ec2.internal   m5.large     us-east-1b
ip-10-0-3-300.ec2.internal   c5.xlarge    us-east-1c
```

## Common Issues

### Issue: No instance type labels

**Solution**: Check if you're using a managed service that uses different labels:
- EKS might use `eks.amazonaws.com/nodegroup`
- AKS might use `kubernetes.azure.com/agentpool`
- GKE might use `cloud.google.com/gke-nodepool`

### Issue: Mixed instance types in node group

**Solution**: KRR handles this by detecting instance type per node, not per group.

### Issue: Spot instances

**Solution**: Instance type is the same, but pricing model differs. Future KRR versions will detect spot instances.

## Summary

For KRR cost integration to work properly:
1. Nodes must have instance type information available
2. Most commonly in `node.kubernetes.io/instance-type` label
3. Can be added manually if missing
4. Cloud provider APIs can help identify correct types 