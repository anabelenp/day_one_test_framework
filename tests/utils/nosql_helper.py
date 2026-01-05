import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from service_manager import get_database_client

# Get database client from service manager
_db_client = None

def _get_db_client():
    """Get database client instance"""
    global _db_client
    if _db_client is None:
        _db_client = get_database_client()
    return _db_client

def insert_log(log):
    """Insert log document"""
    return _get_db_client().insert_one("logs", log)

def get_logs(filter_dict=None):
    """Get log documents with optional filter"""
    if filter_dict is None:
        filter_dict = {}
    return _get_db_client().find_many("logs", filter_dict)

def insert_document(collection, document):
    """Insert document into collection"""
    return _get_db_client().insert_one(collection, document)

def find_document(collection, filter_dict):
    """Find single document in collection"""
    return _get_db_client().find_one(collection, filter_dict)

def find_documents(collection, filter_dict=None, limit=100):
    """Find multiple documents in collection"""
    if filter_dict is None:
        filter_dict = {}
    return _get_db_client().find_many(collection, filter_dict, limit)

def update_document(collection, filter_dict, update_dict):
    """Update document in collection"""
    return _get_db_client().update_one(collection, filter_dict, update_dict)

def delete_document(collection, filter_dict):
    """Delete document from collection"""
    return _get_db_client().delete_one(collection, filter_dict)

def count_documents(collection, filter_dict=None):
    """Count documents in collection"""
    if filter_dict is None:
        filter_dict = {}
    return _get_db_client().count_documents(collection, filter_dict)
