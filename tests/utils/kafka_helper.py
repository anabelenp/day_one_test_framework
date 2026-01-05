import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from service_manager import get_message_client

# Get message client from service manager
_message_client = None

def _get_message_client():
    """Get message client instance"""
    global _message_client
    if _message_client is None:
        _message_client = get_message_client()
    return _message_client

def publish_event(topic, message):
    """Publish message to topic"""
    # Convert string message to dict if needed
    if isinstance(message, str):
        message_dict = {"message": message}
    else:
        message_dict = message
    
    return _get_message_client().publish(topic, message_dict)

def consume_event(topic, timeout_ms=1000):
    """Consume messages from topic"""
    messages = _get_message_client().consume(topic, timeout_ms)
    
    # Extract message content for backward compatibility
    return [msg.get("message", msg) for msg in messages]

def create_topic(topic, partitions=1):
    """Create a new topic"""
    return _get_message_client().create_topic(topic, partitions)

def list_topics():
    """List all available topics"""
    return _get_message_client().list_topics()

def subscribe_to_topic(topic, callback):
    """Subscribe to topic with callback function"""
    return _get_message_client().subscribe(topic, callback)
