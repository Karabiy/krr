"""
Cost Providers Module

This module provides optional cost integration for KRR, allowing accurate
dollar-based savings calculations using cloud provider pricing data.
"""

from typing import Dict, Type, Optional
from .base import CostProvider, InstanceCost, CostData
from .factory import CostProviderFactory

# Provider registry
_PROVIDERS: Dict[str, Type[CostProvider]] = {}


def register_provider(name: str):
    """Decorator to register a cost provider"""
    def decorator(cls: Type[CostProvider]):
        _PROVIDERS[name.lower()] = cls
        return cls
    return decorator


def get_provider(name: str) -> Optional[Type[CostProvider]]:
    """Get a registered cost provider by name"""
    return _PROVIDERS.get(name.lower())


def list_providers() -> list[str]:
    """List all registered cost providers"""
    return list(_PROVIDERS.keys())


# Import providers to trigger registration
try:
    from .vantage import VantageCostProvider
except ImportError:
    pass  # Vantage provider not available


__all__ = [
    "CostProvider",
    "InstanceCost", 
    "CostData",
    "CostProviderFactory",
    "register_provider",
    "get_provider",
    "list_providers",
] 