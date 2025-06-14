"""
conftest.py - Contains pytest fixtures used across multiple test files
"""

import os
import pytest
import json
import tempfile
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables used by the application."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_api_key")
    monkeypatch.setenv("WASENDER_API_TOKEN", "test_wasender_api_token")
    monkeypatch.setenv("WEBHOOK_SECRET", "test_webhook_secret")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test-model")
    
    # Use a temp directory for conversation storage during tests
    temp_dir = tempfile.mkdtemp()
    monkeypatch.setenv("CONVERSATIONS_DIR", temp_dir)
    
    yield temp_dir
    
    # Cleanup temp directories
    try:
        for f in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, f))
        os.rmdir(temp_dir)
    except (OSError, FileNotFoundError):
        pass

@pytest.fixture
def mock_wasender_client():
    """Mock wasender client for testing."""
    client = MagicMock()
    # Mock methods with appropriate return values
    client.send_text = MagicMock(return_value=MagicMock(
        response=MagicMock(
            data=MagicMock(message_id="test_message_id")
        )
    ))
    client.send_image = MagicMock(return_value=MagicMock(
        response=MagicMock(
            data=MagicMock(message_id="test_image_id")
        )
    ))
    client.handle_webhook_event = MagicMock()
    return client

@pytest.fixture
def mock_genai_response():
    """Mock Gemini AI response for testing."""
    response = MagicMock()
    response.text = "This is a test response from Gemini API."
    return response

@pytest.fixture
def mock_gemini_model():
    """Mock Gemini model for testing."""
    model = MagicMock()
    model.generate_content = MagicMock()
    model.start_chat = MagicMock()
    return model

@pytest.fixture
def test_persona_file(tmp_path):
    """Create a test persona file."""
    persona = {
        "name": "Test Bot",
        "description": "I am a test bot for unit tests.",
        "base_prompt": "You are a test bot responding to test messages."
    }
    
    persona_path = tmp_path / "test_persona.json"
    with open(persona_path, 'w') as f:
        json.dump(persona, f)
    
    return str(persona_path)

@pytest.fixture
def sample_webhook_message():
    """Create a sample webhook message payload."""
    return {
        "event": "messages.upsert",
        "data": {
            "messages": {
                "key": {
                    "remoteJid": "1234567890@s.whatsapp.net",
                    "fromMe": False,
                    "id": "test_message_id"
                },
                "message": {
                    "conversation": "Hello, chatbot!"
                }
            }
        }
    }

@pytest.fixture
def sample_webhook_message_sdk_format():
    """Create a sample webhook event in SDK format."""
    from wasenderapi.webhook import WasenderWebhookEvent
    from enum import Enum
    
    class MockEventType(Enum):
        MESSAGES_UPSERT = 'messages.upsert'
    
    event = MagicMock(spec=WasenderWebhookEvent)
    event.event_type = MockEventType.MESSAGES_UPSERT
    
    # Create message structure
    message = MagicMock()
    message.key = MagicMock()
    message.key.remoteJid = "1234567890@s.whatsapp.net"
    message.key.fromMe = False
    message.key.id = "test_message_id"
    message.messageStubType = None
    
    message.message = MagicMock()
    message.message.conversation = "Hello, chatbot!"
    
    # Attach messages to event data
    event.data = MagicMock()
    event.data.messages = [message]
    
    return event
