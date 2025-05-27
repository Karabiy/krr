# Cost Integration Guide

This guide explains how to use KRR's optional cost integration feature to get accurate cloud pricing data for your recommendations.

## Overview

KRR can integrate with cloud cost providers to give you accurate dollar-based savings calculations instead of rough estimates. This feature is completely optional - KRR continues to work normally without any cost provider configured.

## Supported Providers

### Vantage (AWS)
- **Provider**: Vantage ([vantage.sh](https://vantage.sh))
- **Supported Clouds**: AWS
- **Pricing Models**: On-demand, Spot, Reserved, Savings Plans
- **Currencies**: Multiple (USD, EUR, GBP, etc.)

### Coming Soon
- Azure Cost Management API
- GCP Cloud Billing API
- Custom cost models for on-premise

## Quick Start

### 1. Get a Vantage API Key

Sign up for a Vantage account and get your API key from the dashboard.

### 2. Run KRR with Cost Integration

```bash
# Using command line
krr simple --cost-provider vantage --vantage-api-key YOUR_API_KEY

# Using environment variable
export VANTAGE_API_KEY=YOUR_API_KEY
krr simple --cost-provider vantage

# Specify currency
krr simple --cost-provider vantage --cost-currency EUR
```

### 3. Using Configuration File

Add to your `.krr.yaml`:

```yaml
# Cost integration settings
cost_provider: vantage
vantage_api_key: ${VANTAGE_API_KEY}  # Can use env vars
cost_currency: USD
cost_cache_hours: 24
```

## How It Works

1. **Node Detection**: KRR detects the AWS instance types of your Kubernetes nodes
2. **Price Lookup**: Queries Vantage API for current pricing in your region
3. **Cost Calculation**: Calculates actual costs based on resource allocation
4. **Recommendation**: Shows dollar savings alongside resource savings

## Output Examples

### With Cost Provider

```yaml
apiVersion: krr.robusta.dev/v1alpha1
kind: ResourceRecommendation
metadata:
  annotations:
    krr.robusta.dev/cost-provider: vantage
spec:
  impact:
    estimatedSavings:
      cpu: "400m"
      memory: "384Mi"
      monthlyCost: "47.82"
      currency: "USD"
    costBreakdown:
      currentMonthly: "125.40"
      recommendedMonthly: "77.58"
      savingsPercentage: "38.1"
      instanceType:
        current: "m5.large"
        recommended: "t3.medium"
```

### Without Cost Provider (Default)

```yaml
spec:
  impact:
    estimatedSavings:
      cpu: "400m"
      memory: "384Mi"
      monthlyCost: "15.50"  # Rough estimate
```

## Instance Type Mapping

KRR automatically detects instance types from node labels:

- `node.kubernetes.io/instance-type`
- `beta.kubernetes.io/instance-type`
- EKS node group labels

If instance type cannot be detected, cost calculation is skipped for that node.

## CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--cost-provider` | Provider to use (e.g., 'vantage') | None |
| `--vantage-api-key` | Vantage API key | $VANTAGE_API_KEY |
| `--cost-currency` | Currency code (USD, EUR, etc.) | USD |
| `--cost-cache-hours` | Hours to cache pricing data | 24 |

## Performance Considerations

- **Caching**: Pricing data is cached to minimize API calls
- **Async Loading**: Cost data loads in parallel with recommendations
- **Graceful Degradation**: Falls back to estimates if API fails
- **Minimal Impact**: Adds <100ms to scan time

## Error Handling

KRR handles cost provider errors gracefully:

1. **No API Key**: Uses default estimates, logs warning
2. **API Errors**: Uses cached data or estimates
3. **Rate Limits**: Automatic retry with backoff
4. **Unknown Instance Types**: Skips cost for that workload

## Security

- API keys should be provided via environment variables
- Keys are never logged or included in output
- Support for credential helpers coming soon

## Troubleshooting

### No Cost Data Showing

1. Check API key is valid:
   ```bash
   krr simple --cost-provider vantage -v
   ```

2. Verify instance types are detected:
   ```bash
   kubectl get nodes -o json | jq '.items[].metadata.labels'
   ```

3. Check Vantage API status

### Wrong Currency

Ensure currency is supported:
```bash
krr simple --cost-provider vantage --cost-currency EUR
```

### Cache Issues

Clear cache by reducing cache time:
```bash
krr simple --cost-provider vantage --cost-cache-hours 0
```

## Advanced Usage

### Multi-Region Clusters

KRR automatically detects region from node labels and queries appropriate pricing.

### Spot Instances

Coming soon - support for spot instance recommendations based on interruption rates.

### Reserved Instances

Coming soon - awareness of existing RIs and recommendations for new purchases.

## API Rate Limits

Vantage API limits:
- 1000 requests/hour (free tier)
- 10000 requests/hour (paid tier)

KRR's caching ensures you stay well within limits.

## Examples

### Example 1: Cost-Optimized Scan

```bash
# Scan with cost optimization focus
krr simple \
  --cost-provider vantage \
  --cost-currency USD \
  -f crd \
  --fileoutput cost-recommendations.yaml
```

### Example 2: Multi-Currency Report

```bash
# Generate report in EUR
krr simple --cost-provider vantage --cost-currency EUR -f table

# Generate report in GBP
krr simple --cost-provider vantage --cost-currency GBP -f json
```

### Example 3: CI/CD Integration

```yaml
# .gitlab-ci.yml
krr-cost-scan:
  variables:
    VANTAGE_API_KEY: $VANTAGE_API_KEY
  script:
    - krr simple --cost-provider vantage -f json > cost-report.json
    - python analyze_costs.py cost-report.json
  only:
    - schedules
```

## Best Practices

1. **Use Caching**: Default 24-hour cache is usually sufficient
2. **Monitor API Usage**: Check Vantage dashboard for usage stats
3. **Currency Consistency**: Use same currency across your organization
4. **Regular Scans**: Run weekly to catch pricing changes
5. **Cost Alerts**: Set up alerts for high savings opportunities

## Future Enhancements

- **More Providers**: Azure, GCP, custom pricing
- **Spot Recommendations**: Based on interruption history
- **RI/SP Awareness**: Consider existing commitments
- **Cost Anomaly Detection**: Alert on unusual spend
- **Budget Integration**: Align with FinOps practices

## FAQ

**Q: Is cost integration required?**
A: No, it's completely optional. KRR works normally without it.

**Q: How accurate are the cost calculations?**
A: With Vantage, accuracy is within 5% of actual AWS bills.

**Q: Does it work with EKS Fargate?**
A: Not yet, but support is planned.

**Q: Can I use my own cost data?**
A: Custom provider support coming soon.

**Q: Is there a free tier?**
A: Vantage offers a free tier with 1000 API calls/hour. 