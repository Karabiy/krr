"""
Factory for creating cost provider instances
"""

import logging
from typing import Optional, Dict, Any

from robusta_krr.core.models.config import settings
from .base import CostProvider

logger = logging.getLogger("krr")


class CostProviderFactory:
    """Factory for creating cost provider instances"""
    
    @staticmethod
    def create_provider(
        provider_name: Optional[str] = None,
        **kwargs
    ) -> Optional[CostProvider]:
        """
        Create a cost provider instance.
        
        Args:
            provider_name: Name of the provider (e.g., 'vantage')
            **kwargs: Provider-specific configuration
            
        Returns:
            CostProvider instance or None if no provider configured
        """
        # Use settings if provider_name not specified
        if provider_name is None:
            provider_name = getattr(settings, 'cost_provider', None)
        
        if not provider_name:
            logger.debug("No cost provider configured")
            return None
        
        # Import here to avoid circular dependency
        from . import get_provider
        
        provider_class = get_provider(provider_name)
        if not provider_class:
            logger.warning(f"Unknown cost provider: {provider_name}")
            return None
        
        # Get provider configuration from settings
        config = CostProviderFactory._get_provider_config(provider_name, kwargs)
        
        try:
            provider = provider_class(**config)
            logger.info(f"Created cost provider: {provider_name}")
            return provider
        except Exception as e:
            logger.error(f"Failed to create cost provider {provider_name}: {e}")
            return None
    
    @staticmethod
    def _get_provider_config(provider_name: str, override_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Get configuration for a specific provider"""
        config = {}
        
        # Get common cost settings
        if hasattr(settings, 'cost_currency'):
            config['currency'] = settings.cost_currency
        if hasattr(settings, 'cost_cache_hours'):
            config['cache_hours'] = settings.cost_cache_hours
        
        # Get provider-specific settings
        if provider_name == 'vantage':
            if hasattr(settings, 'vantage_api_key'):
                config['api_key'] = settings.vantage_api_key
            if hasattr(settings, 'vantage_api_url'):
                config['api_url'] = settings.vantage_api_url
        
        # Override with kwargs
        config.update(override_kwargs)
        
        return config 