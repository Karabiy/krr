import logging
from datetime import datetime
from typing import Any, Dict, List

import yaml

from robusta_krr.core.abstract import formatters
from robusta_krr.core.models.result import Result, ResourceScan
from robusta_krr.core.models.config import settings

logger = logging.getLogger("krr")


@formatters.register()
def crd(result: Result) -> str:
    """
    Format recommendations as Kubernetes CRDs (Custom Resource Definitions).
    Generates both individual ResourceRecommendation CRDs and a RecommendationReport CRD.
    """
    documents = []
    scan_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    # Create individual ResourceRecommendation CRDs
    recommendation_refs = []
    
    for scan in result.scans:
        recommendation_name = f"{scan.object.name}-{scan.object.container}-{scan_id}".lower()
        recommendation_refs.append({
            "name": recommendation_name,
            "namespace": scan.object.namespace
        })
        
        recommendation_crd = _create_recommendation_crd(scan, recommendation_name, scan_id, result)
        documents.append(recommendation_crd)
    
    # Create the aggregated RecommendationReport CRD
    report_crd = _create_report_crd(result, scan_id, recommendation_refs)
    documents.append(report_crd)
    
    # Convert to YAML with document separators
    yaml_output = ""
    for i, doc in enumerate(documents):
        if i > 0:
            yaml_output += "\n---\n"
        yaml_output += yaml.dump(doc, default_flow_style=False, sort_keys=False)
    
    return yaml_output


def _create_recommendation_crd(scan: ResourceScan, name: str, scan_id: str, result: Result) -> Dict[str, Any]:
    """Create a ResourceRecommendation CRD for a single workload/container."""
    
    # Calculate savings
    cpu_current = scan.object.allocations.requests.cpu
    cpu_recommended = scan.recommended.requests.cpu.value if scan.recommended.requests.cpu else None
    memory_current = scan.object.allocations.requests.memory
    memory_recommended = scan.recommended.requests.memory.value if scan.recommended.requests.memory else None
    
    cpu_savings = 0
    memory_savings = 0
    
    if cpu_current and cpu_recommended and cpu_current > cpu_recommended:
        cpu_savings = (cpu_current - cpu_recommended) * scan.object.current_pods_count
    
    if memory_current and memory_recommended and memory_current > memory_recommended:
        memory_savings = (memory_current - memory_recommended) * scan.object.current_pods_count
    
    # Check if we have cost data from a cost provider
    has_cost_data = hasattr(scan.object.allocations, 'cost_data') and scan.object.allocations.cost_data
    
    # Build impact section with cost data if available
    impact = {
        "estimatedSavings": {
            "cpu": f"{int(cpu_savings)}m" if cpu_savings > 0 else "0m",
            "memory": f"{int(memory_savings)}Mi" if memory_savings > 0 else "0Mi"
        },
        "severity": scan.severity.name.lower()
    }
    
    # Add accurate cost data if available
    if has_cost_data:
        cost_data = scan.object.allocations.cost_data
        if cost_data.monthly_savings is not None:
            impact["estimatedSavings"]["monthlyCost"] = f"{cost_data.monthly_savings:.2f}"
            impact["estimatedSavings"]["currency"] = cost_data.current_cost.currency if cost_data.current_cost else "USD"
            
            # Add cost breakdown
            impact["costBreakdown"] = {
                "currentMonthly": f"{cost_data.current_cost.monthly_cost:.2f}" if cost_data.current_cost else None,
                "recommendedMonthly": f"{cost_data.recommended_cost.monthly_cost:.2f}" if cost_data.recommended_cost else None,
                "savingsPercentage": f"{cost_data.savings_percentage:.1f}" if cost_data.savings_percentage else None,
                "instanceType": {
                    "current": cost_data.current_cost.instance_type if cost_data.current_cost else None,
                    "recommended": cost_data.recommended_cost.instance_type if cost_data.recommended_cost else None
                },
                "lastUpdated": datetime.now().isoformat()
            }
    else:
        # Use rough estimates if no cost provider
        impact["estimatedSavings"]["monthlyCost"] = _calculate_monthly_cost_savings(cpu_savings, memory_savings)
    
    # Build metrics summary
    metrics_summary = {
        "cpu": {},
        "memory": {}
    }
    
    # Add CPU metrics if available
    if scan.recommended.info.get("CPU"):
        metrics_info = scan.recommended.info["CPU"]
        # Extract percentile values if available in the info string
        metrics_summary["cpu"] = {
            "current": f"{cpu_current}m" if cpu_current else None,
            "recommended": f"{cpu_recommended}m" if cpu_recommended else None,
            "info": metrics_info
        }
    
    # Add Memory metrics if available  
    if scan.recommended.info.get("Memory"):
        metrics_info = scan.recommended.info["Memory"]
        metrics_summary["memory"] = {
            "current": f"{memory_current}Mi" if memory_current else None,
            "recommended": f"{memory_recommended}Mi" if memory_recommended else None,
            "info": metrics_info
        }
    
    return {
        "apiVersion": "krr.robusta.dev/v1alpha1",
        "kind": "ResourceRecommendation",
        "metadata": {
            "name": name,
            "namespace": scan.object.namespace,
            "labels": {
                "krr.robusta.dev/workload-name": scan.object.name,
                "krr.robusta.dev/workload-kind": scan.object.kind.lower(),
                "krr.robusta.dev/container": scan.object.container,
                "krr.robusta.dev/scan-id": scan_id,
                "krr.robusta.dev/severity": scan.severity.name.lower()
            },
            "annotations": {
                "krr.robusta.dev/cluster": scan.object.cluster or "current",
                "krr.robusta.dev/strategy": result.strategy.name,
                "krr.robusta.dev/scan-time": datetime.now().isoformat(),
                "krr.robusta.dev/cost-provider": settings.cost_provider if hasattr(settings, 'cost_provider') and settings.cost_provider else "none"
            }
        },
        "spec": {
            "targetRef": {
                "apiVersion": "apps/v1",
                "kind": scan.object.kind,
                "name": scan.object.name,
                "namespace": scan.object.namespace
            },
            "recommendations": {
                "containers": [{
                    "name": scan.object.container,
                    "resources": {
                        "cpu": {
                            "request": f"{int(cpu_recommended)}m" if cpu_recommended else None,
                            "limit": f"{int(scan.recommended.limits.cpu.value)}m" if scan.recommended.limits.cpu.value else None
                        },
                        "memory": {
                            "request": f"{int(memory_recommended)}Mi" if memory_recommended else None,
                            "limit": f"{int(scan.recommended.limits.memory.value)}Mi" if scan.recommended.limits.memory.value else None
                        }
                    }
                }]
            },
            "analysis": {
                "strategy": result.strategy.name,
                "historyDuration": f"{result.strategy.settings.get('history_duration', 336)}h",
                "dataPoints": scan.object.current_pods_count + scan.object.deleted_pods_count,
                "confidence": 0.95 if scan.severity.name in ["CRITICAL", "WARNING"] else 0.8,
                "metrics": metrics_summary
            },
            "impact": impact
        },
        "status": {
            "phase": "pending"
        }
    }


def _create_report_crd(result: Result, scan_id: str, recommendation_refs: List[Dict[str, str]]) -> Dict[str, Any]:
    """Create a RecommendationReport CRD that aggregates all recommendations."""
    
    # Calculate summary statistics
    total_workloads = len(set((scan.object.cluster, scan.object.namespace, scan.object.name) 
                              for scan in result.scans))
    
    by_severity = {"critical": 0, "warning": 0, "ok": 0, "good": 0}
    by_namespace = {}
    total_cpu_savings = 0
    total_memory_savings = 0
    
    for scan in result.scans:
        severity = scan.severity.name.lower()
        by_severity[severity] = by_severity.get(severity, 0) + 1
        
        namespace = scan.object.namespace
        if namespace not in by_namespace:
            by_namespace[namespace] = {"workloads": 0, "savings": {"cpu": 0, "memory": 0}}
        
        by_namespace[namespace]["workloads"] += 1
        
        # Calculate savings
        cpu_current = scan.object.allocations.requests.cpu or 0
        cpu_recommended = scan.recommended.requests.cpu.value if scan.recommended.requests.cpu else cpu_current
        memory_current = scan.object.allocations.requests.memory or 0
        memory_recommended = scan.recommended.requests.memory.value if scan.recommended.requests.memory else memory_current
        
        if cpu_current > cpu_recommended:
            cpu_savings = (cpu_current - cpu_recommended) * scan.object.current_pods_count
            total_cpu_savings += cpu_savings
            by_namespace[namespace]["savings"]["cpu"] += cpu_savings
            
        if memory_current > memory_recommended:
            memory_savings = (memory_current - memory_recommended) * scan.object.current_pods_count
            total_memory_savings += memory_savings
            by_namespace[namespace]["savings"]["memory"] += memory_savings
    
    # Get cluster info
    clusters = list(set(scan.object.cluster for scan in result.scans if scan.object.cluster))
    if not clusters:
        clusters = ["current"]
    
    # Get namespaces
    namespaces = list(set(scan.object.namespace for scan in result.scans))
    
    return {
        "apiVersion": "krr.robusta.dev/v1alpha1",
        "kind": "RecommendationReport",
        "metadata": {
            "name": f"krr-report-{scan_id}",
            "namespace": "default",  # Reports go to default namespace
            "labels": {
                "krr.robusta.dev/scan-id": scan_id,
                "krr.robusta.dev/strategy": result.strategy.name
            },
            "annotations": {
                "krr.robusta.dev/scan-time": datetime.now().isoformat(),
                "krr.robusta.dev/version": "1.0"
            }
        },
        "spec": {
            "scanTime": datetime.now().isoformat(),
            "scope": {
                "clusters": clusters,
                "namespaces": namespaces,
                "labelSelector": settings.selector or ""
            },
            "summary": {
                "totalWorkloads": total_workloads,
                "totalRecommendations": len(result.scans),
                "estimatedMonthlySavings": _calculate_monthly_cost_savings(total_cpu_savings, total_memory_savings),
                "byNamespace": {
                    ns: {
                        "workloads": data["workloads"],
                        "savings": f"${_calculate_monthly_cost_savings(data['savings']['cpu'], data['savings']['memory'])}"
                    }
                    for ns, data in by_namespace.items()
                },
                "bySeverity": by_severity
            },
            "recommendations": recommendation_refs
        },
        "status": {
            "phase": "completed",
            "completionTime": datetime.now().isoformat(),
            "recommendationsCreated": len(recommendation_refs),
            "errors": [error.get("name", "Unknown error") for error in result.errors] if result.errors else []
        }
    }


def _calculate_monthly_cost_savings(cpu_millicores: float, memory_mb: float) -> str:
    """
    Calculate estimated monthly cost savings.
    These are rough estimates - actual costs vary by cloud provider and region.
    """
    # Rough cost estimates (adjust based on your cloud provider)
    # Assuming ~$25/month per vCPU and ~$3.5/month per GB RAM
    cpu_cost_per_vcpu_month = 25.0
    memory_cost_per_gb_month = 3.5
    
    cpu_vcpus = cpu_millicores / 1000
    memory_gb = memory_mb / 1024
    
    monthly_savings = (cpu_vcpus * cpu_cost_per_vcpu_month) + (memory_gb * memory_cost_per_gb_month)
    
    return f"{monthly_savings:.2f}" 