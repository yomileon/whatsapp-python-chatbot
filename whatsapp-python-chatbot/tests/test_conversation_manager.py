"""
test_conversation_manager.py - Tests for the ConversationManager class
"""

import os
import json
import pytest
from script import ConversationManager

class TestConversationManager:
    def test_initialization(self, mock_env_vars):
        """Test ConversationManager initialization."""
        # Arrange
        storage_dir = mock_env_vars
        max_history = 10
        
        # Act
        manager = ConversationManager(storage_dir, max_history)
        
        # Assert
        assert manager.storage_dir == storage_dir
        assert manager.max_history == max_history
    
    def test_load_nonexistent_file(self, mock_env_vars):
        """Test loading conversation history when the file does not exist."""
        # Arrange
        manager = ConversationManager(mock_env_vars)
        user_id = "nonexistent_user"
        
        # Act
        history = manager.load(user_id)
        
        # Assert
        assert history == []
    
    def test_save_and_load(self, mock_env_vars):
        """Test saving and loading conversation history."""
        # Arrange
        manager = ConversationManager(mock_env_vars)
        user_id = "test_user"
        test_history = [
            {'role': 'user', 'parts': ["Hello, bot!"]},
            {'role': 'model', 'parts': ["Hello, user!"]}
        ]
        
        # Act
        manager.save(user_id, test_history)
        loaded_history = manager.load(user_id)
        
        # Assert
        assert loaded_history == test_history
        
        # Verify the file was created
        file_path = os.path.join(mock_env_vars, f"{user_id}.json")
        assert os.path.exists(file_path)
        
        # Verify file contents
        with open(file_path, 'r') as f:
            saved_data = json.load(f)
        assert saved_data == test_history
    
    def test_add_exchange(self, mock_env_vars):
        """Test adding a new message exchange to history."""
        # Arrange
        manager = ConversationManager(mock_env_vars)
        user_id = "test_user"
        user_message = "How are you?"
        model_response = "I'm doing great, thanks for asking!"
        
        # Create initial history
        initial_history = [
            {'role': 'user', 'parts': ["Hello!"]},
            {'role': 'model', 'parts': ["Hi there!"]}
        ]
        manager.save(user_id, initial_history)
        
        # Act
        updated_history = manager.add_exchange(user_id, user_message, model_response)
        
        # Assert
        expected_history = initial_history + [
            {'role': 'user', 'parts': [user_message]},
            {'role': 'model', 'parts': [model_response]}
        ]
        assert updated_history == expected_history
        
        # Verify the saved history matches what was returned
        loaded_history = manager.load(user_id)
        assert loaded_history == expected_history
    
    def test_history_truncation(self, mock_env_vars):
        """Test that history gets truncated when it exceeds max_history."""
        # Arrange
        max_history = 2  # Only keep 2 exchanges (4 messages total)
        manager = ConversationManager(mock_env_vars, max_history)
        user_id = "test_user"
        
        # Create a history that's longer than max_history
        long_history = []
        for i in range(5):  # Create 5 exchanges (10 messages)
            long_history.append({'role': 'user', 'parts': [f"User message {i}"]})
            long_history.append({'role': 'model', 'parts': [f"Model response {i}"]})
        
        manager.save(user_id, long_history)
        
        # Act
        loaded_history = manager.load(user_id)
        
        # Assert
        # Should only contain the last 2 exchanges (4 messages)
        assert len(loaded_history) == 4
        assert loaded_history[0]['parts'][0] == "User message 3"
        assert loaded_history[1]['parts'][0] == "Model response 3"
        assert loaded_history[2]['parts'][0] == "User message 4"
        assert loaded_history[3]['parts'][0] == "Model response 4"
        
    def test_load_invalid_json(self, mock_env_vars):
        """Test loading when the file contains invalid JSON."""
        # Arrange
        manager = ConversationManager(mock_env_vars)
        user_id = "test_user"
        file_path = os.path.join(mock_env_vars, f"{user_id}.json")
        
        # Create a file with invalid JSON
        with open(file_path, 'w') as f:
            f.write("This is not valid JSON")
        
        # Act
        history = manager.load(user_id)
        
        # Assert
        assert history == []
        
    def test_load_invalid_format(self, mock_env_vars):
        """Test loading when the file contains valid JSON but in wrong format."""
        # Arrange
        manager = ConversationManager(mock_env_vars)
        user_id = "test_user"
        file_path = os.path.join(mock_env_vars, f"{user_id}.json")
        
        # Create a file with valid JSON but wrong format
        with open(file_path, 'w') as f:
            json.dump({"not": "a list"}, f)
        
        # Act
        history = manager.load(user_id)
        
        # Assert
        assert history == []
