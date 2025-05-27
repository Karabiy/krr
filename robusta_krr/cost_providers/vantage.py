"""
Vantage API cost provider for AWS pricing
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

try:
    import aiohttp
except ImportError:
    aiohttp = None

from .base import CostProvider, InstanceCost, PricingModel
from . import register_provider

logger = logging.getLogger("krr")


@register_provider("vantage")
class VantageCostProvider(CostProvider):
    """Vantage API integration for AWS costs"""
    
    def __init__(
        self, 
        api_key: str,
        api_url: str = "https://api.vantage.sh/v1",
        currency: str = "USD",
        cache_hours: int = 24,
        timeout: int = 30
    ):
        super().__init__(currency, cache_hours)
        
        if not aiohttp:
            raise ImportError("aiohttp is required for Vantage provider. Install with: pip install aiohttp")
        
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Instance type to resource mapping cache
        self._instance_specs: Dict[str, Dict[str, Any]] = {}
    
    def get_provider_name(self) -> str:
        return "vantage"
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self._session
    
    async def __aenter__(self):
        await self._get_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def validate_credentials(self) -> bool:
        """Validate Vantage API credentials"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.api_url}/providers") as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Failed to validate Vantage credentials: {e}")
            return False
    
    async def get_instance_cost(
        self, 
        instance_type: str, 
        region: str,
        pricing_model: PricingModel = PricingModel.ON_DEMAND
    ) -> Optional[InstanceCost]:
        """Get AWS instance cost from Vantage API"""
        
        # Check cache first
        cached = self._get_from_cache(instance_type, region, pricing_model)
        if cached:
            logger.debug(f"Using cached cost for {instance_type} in {region}")
            return cached
        
        try:
            # Query Vantage API for costs
            cost_data = await self._query_costs(instance_type, region, pricing_model)
            if not cost_data:
                logger.warning(f"No cost data found for {instance_type} in {region}")
                return None
            
            # Get instance specs if not cached
            if instance_type not in self._instance_specs:
                specs = await self._get_instance_specs(instance_type)
                if specs:
                    self._instance_specs[instance_type] = specs
            
            # Create InstanceCost object
            specs = self._instance_specs.get(instance_type, {})
            instance_cost = InstanceCost(
                instance_type=instance_type,
                region=region,
                hourly_cost=cost_data['hourly_cost'],
                currency=self.currency,
                pricing_model=pricing_model,
                cpu_count=specs.get('vcpus'),
                memory_gb=specs.get('memory_gb'),
                last_updated=datetime.utcnow()
            )
            
            # Cache the result
            self._set_cache(instance_cost)
            
            return instance_cost
            
        except Exception as e:
            logger.error(f"Error getting cost for {instance_type}: {e}")
            return None
    
    async def _query_costs(
        self, 
        instance_type: str, 
        region: str, 
        pricing_model: PricingModel
    ) -> Optional[Dict[str, Any]]:
        """Query Vantage API for instance costs"""
        session = await self._get_session()
        
        # Map pricing model to Vantage terms
        term_map = {
            PricingModel.ON_DEMAND: "on_demand",
            PricingModel.SPOT: "spot",
            PricingModel.RESERVED: "reserved_1yr",
            PricingModel.SAVINGS_PLAN: "compute_savings_1yr"
        }
        
        params = {
            "filter[instance_type]": instance_type,
            "filter[region]": region,
            "filter[term]": term_map.get(pricing_model, "on_demand"),
            "filter[provider]": "aws",
            "filter[service]": "ec2"
        }
        
        try:
            async with session.get(f"{self.api_url}/costs", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('costs') and len(data['costs']) > 0:
                        cost_item = data['costs'][0]
                        return {
                            'hourly_cost': float(cost_item.get('amount', 0)),
                            'currency': cost_item.get('currency', 'USD')
                        }
                elif response.status == 429:
                    logger.warning("Vantage API rate limit reached")
                else:
                    logger.warning(f"Vantage API returned status {response.status}")
                    
        except asyncio.TimeoutError:
            logger.error("Vantage API request timed out")
        except Exception as e:
            logger.error(f"Error querying Vantage API: {e}")
        
        return None
    
    async def _get_instance_specs(self, instance_type: str) -> Optional[Dict[str, Any]]:
        """Get instance specifications from Vantage"""
        session = await self._get_session()
        
        params = {
            "filter[instance_type]": instance_type,
            "filter[provider]": "aws"
        }
        
        try:
            async with session.get(f"{self.api_url}/resources/compute", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('resources') and len(data['resources']) > 0:
                        resource = data['resources'][0]
                        return {
                            'vcpus': resource.get('vcpus'),
                            'memory_gb': resource.get('memory_gb'),
                            'storage_gb': resource.get('storage_gb'),
                            'network_performance': resource.get('network_performance')
                        }
        except Exception as e:
            logger.debug(f"Could not get instance specs for {instance_type}: {e}")
        
        return None
    
    @staticmethod
    def map_node_to_instance_type(node_labels: Dict[str, str]) -> Optional[str]:
        """
        Map Kubernetes node labels to AWS instance type.
        
        Common labels:
        - node.kubernetes.io/instance-type
        - kops.k8s.io/instancegroup
        - eks.amazonaws.com/nodegroup
        """
        # Direct instance type label
        instance_type = node_labels.get('node.kubernetes.io/instance-type')
        if instance_type:
            return instance_type
        
        # EKS specific
        instance_type = node_labels.get('beta.kubernetes.io/instance-type')
        if instance_type:
            return instance_type
        
        # Try to parse from other labels
        # Add more mapping logic as needed
        
        return None 