# How KRR Determines Instance Types for Cost Queries

## Short Answer

**Currently, KRR doesn't query Vantage API with instance types because the integration is incomplete.** The infrastructure exists but the connection between workload scanning and cost querying is missing.

## What's Implemented vs What's Missing

### ✅ Implemented:
- Cost provider infrastructure
- Vantage API client that accepts instance types
- CLI options for cost configuration

### ❌ Missing - The Critical Link:
The code to:
1. Extract instance types from Kubernetes nodes
2. Map workloads to their nodes
3. Pass instance types to the cost provider

## Where Instance Types Come From

Instance types are stored in Kubernetes node labels:

```yaml
# Primary label (most common)
node.kubernetes.io/instance-type: "m5.large"

# Legacy label (older clusters)
beta.kubernetes.io/instance-type: "m5.large"
```

## The Missing Integration

Here's what SHOULD happen (but doesn't yet):

```python
# 1. When scanning a workload (e.g., nginx deployment)
workload = "nginx"

# 2. Find which pods belong to this workload
pods = ["nginx-7f89b6c4-abc", "nginx-7f89b6c4-def"]

# 3. Find which nodes these pods run on
nodes = ["node-1", "node-2"]

# 4. Get instance type from node labels
instance_type = get_node_label(
    "node-1", 
    "node.kubernetes.io/instance-type"
)  # Returns: "m5.large"

# 5. Query Vantage API
cost_data = vantage_client.get_instance_cost(
    instance_type="m5.large",
    region="us-east-1"
)
```

## Current State

When you run:
```bash
krr simple --cost-provider vantage --vantage-api-key YOUR_KEY
```

What happens:
1. Cost provider is initialized ✅
2. Workloads are scanned ✅
3. **Instance types are NOT extracted** ❌
4. **Vantage API is NOT called** ❌
5. Cost data remains empty ❌

## The Code Gap

The missing piece is in `runner.py` around line 232:

```python
async def _calculate_object_recommendations(self, object: K8sObjectData):
    # ... existing metrics calculation ...
    
    # MISSING: This code should exist but doesn't
    # node_info = await self._get_node_instance_type(object)
    # if node_info and self._cost_provider:
    #     cost_data = await self._cost_provider.get_workload_cost(
    #         instance_type=node_info['instance_type'],
    #         region=node_info['region']
    #     )
    
    return self._format_result(result)
```

## Summary

The Vantage integration is designed to receive instance types from Kubernetes node labels, but the code to extract and pass these instance types doesn't exist yet. This is why cost features are implemented but non-functional - they're waiting for this critical integration piece. 