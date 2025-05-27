import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
import logging

logger = logging.getLogger("krr")

DEFAULT_CONFIG_FILENAMES = [".krr.yaml", ".krr.yml", "krr.yaml", "krr.yml"]


def find_config_file(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Search for a KRR configuration file starting from the given path or current directory.
    Searches up the directory tree until a config file is found or root is reached.
    """
    if start_path is None:
        start_path = Path.cwd()
    
    current_path = start_path.resolve()
    
    while True:
        # Check for config files in current directory
        for filename in DEFAULT_CONFIG_FILENAMES:
            config_path = current_path / filename
            if config_path.exists() and config_path.is_file():
                return config_path
        
        # Move up to parent directory
        parent = current_path.parent
        if parent == current_path:  # Reached root
            break
        current_path = parent
    
    return None


def load_config_file(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.
    If no path is provided, searches for a config file in the current directory and parents.
    """
    if config_path is None:
        config_path = find_config_file()
        if config_path is None:
            return {}
        logger.info(f"Found configuration file: {config_path}")
    
    if not config_path.exists():
        logger.warning(f"Configuration file not found: {config_path}")
        return {}
    
    try:
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f) or {}
            
        logger.info(f"Loaded configuration from {config_path}")
        return config_data
    except yaml.YAMLError as e:
        logger.error(f"Error parsing configuration file {config_path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error loading configuration file {config_path}: {e}")
        return {}


def merge_configs(cli_args: Dict[str, Any], file_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge CLI arguments with file configuration.
    CLI arguments take precedence over file configuration.
    """
    # Start with file config
    merged = file_config.copy()
    
    # Update with CLI args, but only if they're not None/default
    for key, value in cli_args.items():
        # Skip None values and certain keys that shouldn't be merged
        if value is not None and key not in ['config_file']:
            merged[key] = value
        elif key not in merged and value is not None:
            merged[key] = value
    
    return merged


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize configuration values.
    """
    # Convert string lists to actual lists where needed
    list_fields = ['clusters', 'namespaces', 'resources']
    for field in list_fields:
        if field in config and isinstance(config[field], str) and config[field] != '*':
            config[field] = [item.strip() for item in config[field].split(',')]
    
    # Ensure prometheus headers are dictionaries
    if 'prometheus_other_headers' in config:
        headers = config['prometheus_other_headers']
        if isinstance(headers, list):
            # Convert list of "key: value" strings to dict
            config['prometheus_other_headers'] = {
                k.strip(): v.strip() 
                for header in headers 
                for k, v in [header.split(':', 1)]
            }
    
    return config 