"""
test_gemini_client.py - Tests for the GeminiClient class
"""

import pytest
from unittest.mock import patch, MagicMock
from script import GeminiClient

class TestGeminiClient:
    def test_initialization(self):
        """Test GeminiClient initialization with valid parameters."""
        # Arrange
        api_key = "test_api_key"
        model_name = "test_model"
        system_instruction = "You are a test AI."
        
        # Act & Assert
        with patch('script.genai'):
            client = GeminiClient(api_key, model_name, system_instruction)
            assert client.api_key == api_key
            assert client.model_name == model_name
            assert client.system_instruction == system_instruction
    
    def test_initialization_no_api_key(self):
        """Test GeminiClient initialization with missing API key."""
        # Arrange
        api_key = None
        model_name = "test_model"
        system_instruction = "You are a test AI."
        
        # Act & Assert
        with pytest.raises(ValueError):
            with patch('script.genai'):
                GeminiClient(api_key, model_name, system_instruction)
    
    def test_generate_response_no_history(self, mock_genai_response, mock_gemini_model):
        """Test generating a response without conversation history."""
        # Arrange
        with patch('script.genai') as mock_genai:
            mock_genai.GenerativeModel.return_value = mock_gemini_model
            mock_gemini_model.generate_content.return_value = mock_genai_response
            
            client = GeminiClient("test_api_key", "test_model", "You are a test AI.")
            message = "Hello, bot!"
            
            # Act
            response = client.generate_response(message)
            
            # Assert
            mock_gemini_model.generate_content.assert_called_once_with(message)
            assert response == mock_genai_response.text
    
    def test_generate_response_with_history(self, mock_genai_response, mock_gemini_model):
        """Test generating a response with conversation history."""
        # Arrange
        with patch('script.genai') as mock_genai:
            mock_chat = MagicMock()
            mock_chat.send_message.return_value = mock_genai_response
            mock_gemini_model.start_chat.return_value = mock_chat
            
            mock_genai.GenerativeModel.return_value = mock_gemini_model
            
            client = GeminiClient("test_api_key", "test_model", "You are a test AI.")
            message = "Hello again, bot!"
            history = [
                {'role': 'user', 'parts': ["Hello, bot!"]},
                {'role': 'model', 'parts': ["Hello, user!"]}
            ]
            
            # Act
            response = client.generate_response(message, history)
            
            # Assert
            mock_gemini_model.start_chat.assert_called_once_with(history=history)
            mock_chat.send_message.assert_called_once_with(message)
            assert response == mock_genai_response.text
    
    def test_generate_response_error_handling(self, mock_gemini_model):
        """Test error handling when Gemini API raises an exception."""
        # Arrange
        with patch('script.genai') as mock_genai:
            mock_genai.GenerativeModel.return_value = mock_gemini_model
            mock_gemini_model.generate_content.side_effect = Exception("API Error")
            
            client = GeminiClient("test_api_key", "test_model", "You are a test AI.")
            message = "Hello, bot!"
            
            # Act
            response = client.generate_response(message)
            
            # Assert
            assert "trouble processing" in response
            assert "try again later" in response
    
    
    def test_generate_response_candidates_fallback(self, mock_gemini_model):
        """Test fallback to candidates when .text is not available."""
        # Arrange
        with patch('script.genai') as mock_genai:
            mock_genai.GenerativeModel.return_value = mock_gemini_model
            
            # Create a response with candidates but no direct text property
            mock_response = MagicMock()
            del mock_response.text  # Ensure text property doesn't exist
            mock_response.candidates = [
                MagicMock(
                    content=MagicMock(
                        parts=[MagicMock(text="Response from candidates")]
                    )
                )
            ]
            mock_gemini_model.generate_content.return_value = mock_response
            
            client = GeminiClient("test_api_key", "test_model", "You are a test AI.")
            message = "Hello, bot!"
            
            # Act
            response = client.generate_response(message)
            
            # Assert
            assert response == "Response from candidates"
