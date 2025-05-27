# KRR - Kubernetes Resource Recommender

## What is KRR?

KRR (Kubernetes Resource Recommender) is a CLI tool that analyzes your Kubernetes workloads' actual resource usage from Prometheus metrics and provides optimized CPU and memory recommendations. It helps reduce costs and improve performance by right-sizing your containers.

## Core Functionality

### 1. **Metrics Collection**
- Connects to Prometheus (or compatible systems like Victoria Metrics, Thanos, Coralogix)
- Collects historical CPU and memory usage data for pods
- Supports multiple authentication methods (tokens, headers, AWS/Azure managed Prometheus)

### 2. **Resource Analysis**
- Analyzes usage patterns over configurable time periods (default: 14 days)
- Calculates recommendations using pluggable strategies:
  - **Simple Strategy**: CPU at 95th percentile, Memory at max + 15% buffer
  - **Simple Limit Strategy**: Similar to Simple but also sets resource limits

### 3. **Output Formats**
- Multiple output formats: table (CLI), JSON, YAML, CSV, HTML
- Can save to files or send to Slack
- Supports filtering by namespace, resource type, labels

### 4. **Integration Points**
- **Kubernetes**: Direct cluster access via kubeconfig
- **Prometheus**: Auto-discovery or manual URL configuration
- **Cloud Providers**: Native support for EKS, AKS, GKE managed Prometheus
- **Platforms**: Robusta SaaS for UI visualization

## Key Components

```
robusta_krr/
├── strategies/          # Recommendation algorithms
│   ├── simple.py       # Default strategy
│   └── simple_limit.py # Strategy with limits
├── core/
│   ├── integrations/   # External system connectors
│   │   ├── kubernetes/ # K8s API client
│   │   └── prometheus/ # Metrics queries
│   └── models/         # Data structures
├── formatters/         # Output formatting
└── main.py            # CLI interface
```

## How It Works

1. **Discovery**: KRR connects to your Kubernetes cluster and Prometheus
2. **Collection**: Queries historical resource usage for each container
3. **Analysis**: Applies selected strategy to calculate optimal resources
4. **Recommendation**: Outputs specific CPU/memory requests (and optionally limits)

## Example Usage

```bash
# Basic scan of all namespaces
krr simple

# Scan specific namespaces with custom Prometheus
krr simple -n production -n staging -p http://prometheus:9090

# Output as JSON with minimum thresholds
krr simple -f json --cpu-min 100 --mem-min 128 --fileoutput report.json

# Use different strategy
krr simple-limit --history-duration 7
```

## Technical Details

- **Language**: Python 3.9+
- **Dependencies**: Kubernetes client, Prometheus API client, Typer (CLI)
- **Metrics Used**:
  - `container_cpu_usage_seconds_total`
  - `container_memory_working_set_bytes`
  - Pod ownership metrics for workload mapping 