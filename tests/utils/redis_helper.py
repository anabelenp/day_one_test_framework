import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.service_manager import get_cache_client

# Get cache client from service manager
_cache_client = None


def _get_cache_client():
    """Get cache client instance"""
    global _cache_client
    if _cache_client is None:
        _cache_client = get_cache_client()
    return _cache_client


def set_key(key, value):
    """Set a key-value pair in cache"""
    return _get_cache_client().set(key, value)


def get_key(key):
    """Get value by key from cache"""
    return _get_cache_client().get(key)


def delete_key(key):
    """Delete a key from cache"""
    return _get_cache_client().delete(key)


def exists_key(key):
    """Check if key exists in cache"""
    return _get_cache_client().exists(key)


def flush_all():
    """Clear all cached data"""
    return _get_cache_client().flush_all()


# Backward compatibility functions
def set_test_key(key, value):
    """Backward compatibility function"""
    return set_key(key, value)


def get_test_key(key):
    """Backward compatibility function"""
    return get_key(key)
