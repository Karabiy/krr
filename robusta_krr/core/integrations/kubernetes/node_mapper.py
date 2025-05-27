"""
Node mapping utilities for extracting cloud instance information from Kubernetes nodes
"""

import logging
from typing import Dict, Optional, List
from kubernetes.client.models import V1Node

logger = logging.getLogger("krr")


class NodeMapper:
    """Maps Kubernetes nodes to cloud instance information"""
    
    def __init__(self):
        self._node_cache: Dict[str, Dict[str, str]] = {}
    
    def get_node_instance_info(self, node: V1Node) -> Dict[str, Optional[str]]:
        """
        Extract instance information from a Kubernetes node.
        
        Returns:
            Dict with keys: instance_type, region, zone, provider
        """
        node_name = node.metadata.name
        
        # Check cache
        if node_name in self._node_cache:
            return self._node_cache[node_name]
        
        labels = node.metadata.labels or {}
        
        # Extract instance type from various possible labels
        instance_type = (
            labels.get("node.kubernetes.io/instance-type") or
            labels.get("beta.kubernetes.io/instance-type") or
            labels.get("kops.k8s.io/instancegroup") or
            None
        )
        
        # Extract region and zone
        region = labels.get("topology.kubernetes.io/region") or labels.get("failure-domain.beta.kubernetes.io/region")
        zone = labels.get("topology.kubernetes.io/zone") or labels.get("failure-domain.beta.kubernetes.io/zone")
        
        # Determine cloud provider from providerID
        provider = self._detect_cloud_provider(node.spec.provider_id if node.spec else None)
        
        info = {
            "instance_type": instance_type,
            "region": region,
            "zone": zone,
            "provider": provider,
            "node_name": node_name
        }
        
        # Cache the result
        self._node_cache[node_name] = info
        
        if not instance_type:
            logger.warning(f"No instance type found for node {node_name}")
        else:
            logger.debug(f"Node {node_name} is instance type {instance_type} in {region}/{zone}")
        
        return info
    
    def _detect_cloud_provider(self, provider_id: Optional[str]) -> Optional[str]:
        """Detect cloud provider from provider ID"""
        if not provider_id:
            return None
        
        if provider_id.startswith("aws://"):
            return "aws"
        elif provider_id.startswith("azure://"):
            return "azure"
        elif provider_id.startswith("gce://"):
            return "gcp"
        else:
            return None
    
    def get_workload_node_info(self, pod_nodes: List[str]) -> Optional[Dict[str, str]]:
        """
        Get instance info for a workload based on its pods' nodes.
        
        For now, returns info from the first node (assumes homogeneous node pools).
        Future: handle heterogeneous pools.
        """
        for node_name in pod_nodes:
            if node_name in self._node_cache:
                return self._node_cache[node_name]
        
        return None
    
    def extract_aws_specific_info(self, node: V1Node) -> Dict[str, Optional[str]]:
        """Extract AWS-specific information from node"""
        labels = node.metadata.labels or {}
        
        return {
            "eks_nodegroup": labels.get("eks.amazonaws.com/nodegroup"),
            "eks_nodegroup_image": labels.get("eks.amazonaws.com/nodegroup-image"),
            "kops_instancegroup": labels.get("kops.k8s.io/instancegroup"),
            "lifecycle": labels.get("node.kubernetes.io/lifecycle"),  # spot/on-demand
        }
    
    def clear_cache(self):
        """Clear the node cache"""
        self._node_cache.clear() 