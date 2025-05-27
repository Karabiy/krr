import logging
from typing import Any, Dict, List

import yaml

from robusta_krr.core.abstract import formatters
from robusta_krr.core.models.result import Result

logger = logging.getLogger("krr")


@formatters.register()
def yaml_manifests(result: Result) -> str:
    """
    Format recommendations as Kubernetes YAML manifests that can be directly applied.
    Each workload gets its own YAML document separated by '---'.
    """
    manifests = []
    
    for _, group in result.group_by(["object.cluster", "object.namespace", "object.name", "object.kind"]):
        if group.is_empty():
            continue
            
        # Get the first item to extract workload info
        first_item = group.entries[0]
        workload = first_item.object
        
        # Build the manifest based on workload kind
        manifest = {
            "apiVersion": "apps/v1",
            "kind": workload.kind,
            "metadata": {
                "name": workload.name,
                "namespace": workload.namespace,
                "annotations": {
                    "krr.robusta.dev/updated": "true",
                    "krr.robusta.dev/strategy": str(result.strategy),
                    "krr.robusta.dev/version": "1.0"
                }
            },
            "spec": {
                "template": {
                    "spec": {
                        "containers": []
                    }
                }
            }
        }
        
        # Add container resource specifications
        for item in group.entries:
            container_spec = {
                "name": item.object.container,
                "resources": {}
            }
            
            # Add requests
            if item.recommended.requests:
                container_spec["resources"]["requests"] = {}
                if item.recommended.requests.cpu:
                    container_spec["resources"]["requests"]["cpu"] = f"{item.recommended.requests.cpu}m"
                if item.recommended.requests.memory:
                    container_spec["resources"]["requests"]["memory"] = f"{item.recommended.requests.memory}Mi"
            
            # Add limits
            if item.recommended.limits:
                container_spec["resources"]["limits"] = {}
                if item.recommended.limits.cpu:
                    container_spec["resources"]["limits"]["cpu"] = f"{item.recommended.limits.cpu}m"
                if item.recommended.limits.memory:
                    container_spec["resources"]["limits"]["memory"] = f"{item.recommended.limits.memory}Mi"
            
            manifest["spec"]["template"]["spec"]["containers"].append(container_spec)
        
        # Add cluster info if available
        if workload.cluster:
            manifest["metadata"]["annotations"]["krr.robusta.dev/cluster"] = workload.cluster
        
        manifests.append(manifest)
    
    # Convert to YAML with document separators
    yaml_output = ""
    for i, manifest in enumerate(manifests):
        if i > 0:
            yaml_output += "\n---\n"
        yaml_output += yaml.dump(manifest, default_flow_style=False, sort_keys=False)
    
    return yaml_output 