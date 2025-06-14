"""
test_persona.py - Tests for persona loading functionality
"""

import os
import json
import pytest
from unittest.mock import patch, mock_open
from script import load_persona

class TestPersona:
    def test_load_valid_persona(self, test_persona_file):
        """Test loading a valid persona from a file."""
        # Arrange & Act
        persona_description, persona_name = load_persona(test_persona_file)
        
        # Assert
        assert persona_name == "Test Bot"
        assert "I am a test bot for unit tests." in persona_description
        assert "You are a test bot responding to test messages." in persona_description
        
    def test_load_nonexistent_persona(self):
        """Test loading persona when the file doesn't exist."""
        # Arrange & Act
        with patch('os.path.exists', return_value=False):
            persona_description, persona_name = load_persona("nonexistent.json")
        
        # Assert
        assert persona_name == "Assistant"
        assert "You are a helpful assistant." in persona_description
        
    def test_load_invalid_json_persona(self):
        """Test loading persona when the file contains invalid JSON."""
        # Arrange
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data="This is not valid JSON")):
            
            # Act
            persona_description, persona_name = load_persona("invalid.json")
        
        # Assert
        assert persona_name == "Assistant"
        assert "You are a helpful assistant." in persona_description
        
    def test_load_persona_missing_fields(self):
        """Test loading persona when the file is missing required fields."""
        # Arrange
        incomplete_persona = json.dumps({
            "name": "Incomplete Bot"
            # Missing description and base_prompt
        })
        
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=incomplete_persona)):
            
            # Act
            persona_description, persona_name = load_persona("incomplete.json")
        
        # Assert
        assert persona_name == "Incomplete Bot"
        assert "You are a helpful and concise AI assistant" in persona_description
        assert "You are a helpful assistant." in persona_description
        
    def test_load_persona_unexpected_error(self):
        """Test handling of unexpected errors when loading persona."""
        # Arrange
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', side_effect=Exception("Unexpected error")):
            
            # Act
            persona_description, persona_name = load_persona("error.json")
        
        # Assert
        assert persona_name == "Assistant"
        assert "You are a helpful assistant." in persona_description
