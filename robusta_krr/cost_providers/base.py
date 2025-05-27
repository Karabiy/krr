"""
Base classes for cost providers
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class PricingModel(Enum):
    """Cloud pricing models"""
    ON_DEMAND = "on_demand"
    SPOT = "spot"
    RESERVED = "reserved"
    SAVINGS_PLAN = "savings_plan"


@dataclass
class InstanceCost:
    """Cost information for an instance type"""
    instance_type: str
    region: str
    hourly_cost: float
    currency: str
    pricing_model: PricingModel = PricingModel.ON_DEMAND
    cpu_count: Optional[int] = None
    memory_gb: Optional[float] = None
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.utcnow()
    
    @property
    def monthly_cost(self) -> float:
        """Calculate monthly cost (730 hours)"""
        return self.hourly_cost * 730
    
    @property
    def yearly_cost(self) -> float:
        """Calculate yearly cost"""
        return self.hourly_cost * 8760


@dataclass
class CostData:
    """Cost data for a workload"""
    current_cost: Optional[InstanceCost] = None
    recommended_cost: Optional[InstanceCost] = None
    
    @property
    def monthly_savings(self) -> Optional[float]:
        """Calculate monthly savings"""
        if self.current_cost and self.recommended_cost:
            if self.current_cost.currency != self.recommended_cost.currency:
                raise ValueError("Cannot calculate savings with different currencies")
            return self.current_cost.monthly_cost - self.recommended_cost.monthly_cost
        return None
    
    @property
    def savings_percentage(self) -> Optional[float]:
        """Calculate savings percentage"""
        if self.current_cost and self.recommended_cost and self.current_cost.monthly_cost > 0:
            return (self.monthly_savings / self.current_cost.monthly_cost) * 100
        return None


class CostProvider(ABC):
    """Abstract base class for cost providers"""
    
    def __init__(self, currency: str = "USD", cache_hours: int = 24):
        self.currency = currency
        self.cache_hours = cache_hours
        self._cache: Dict[str, InstanceCost] = {}
    
    @abstractmethod
    async def get_instance_cost(
        self, 
        instance_type: str, 
        region: str,
        pricing_model: PricingModel = PricingModel.ON_DEMAND
    ) -> Optional[InstanceCost]:
        """
        Get cost information for an instance type.
        
        Args:
            instance_type: Cloud instance type (e.g., 'm5.large')
            region: Cloud region (e.g., 'us-east-1')
            pricing_model: Pricing model to use
            
        Returns:
            InstanceCost object or None if not found
        """
        pass
    
    @abstractmethod
    async def validate_credentials(self) -> bool:
        """
        Validate that the provider credentials are valid.
        
        Returns:
            True if credentials are valid, False otherwise
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of this cost provider"""
        pass
    
    def _get_cache_key(self, instance_type: str, region: str, pricing_model: PricingModel) -> str:
        """Generate cache key for instance cost"""
        return f"{instance_type}:{region}:{pricing_model.value}"
    
    def _is_cache_valid(self, cost: InstanceCost) -> bool:
        """Check if cached cost data is still valid"""
        if not cost.last_updated:
            return False
        
        age_hours = (datetime.utcnow() - cost.last_updated).total_seconds() / 3600
        return age_hours < self.cache_hours
    
    def _get_from_cache(self, instance_type: str, region: str, pricing_model: PricingModel) -> Optional[InstanceCost]:
        """Get cost from cache if valid"""
        key = self._get_cache_key(instance_type, region, pricing_model)
        if key in self._cache:
            cost = self._cache[key]
            if self._is_cache_valid(cost):
                return cost
        return None
    
    def _set_cache(self, cost: InstanceCost):
        """Store cost in cache"""
        key = self._get_cache_key(cost.instance_type, cost.region, cost.pricing_model)
        self._cache[key] = cost
    
    async def get_workload_cost(
        self,
        current_instance_type: str,
        recommended_instance_type: str,
        region: str,
        pricing_model: PricingModel = PricingModel.ON_DEMAND
    ) -> CostData:
        """
        Get cost data for current and recommended configurations.
        
        Args:
            current_instance_type: Current instance type
            recommended_instance_type: Recommended instance type  
            region: Cloud region
            pricing_model: Pricing model to use
            
        Returns:
            CostData object with current and recommended costs
        """
        current_cost = await self.get_instance_cost(current_instance_type, region, pricing_model)
        recommended_cost = await self.get_instance_cost(recommended_instance_type, region, pricing_model)
        
        return CostData(
            current_cost=current_cost,
            recommended_cost=recommended_cost
        ) 