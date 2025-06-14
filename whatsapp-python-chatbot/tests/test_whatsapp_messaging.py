"""
test_whatsapp_messaging.py - Tests for WhatsApp messaging functionality
"""

import pytest
from unittest.mock import patch, MagicMock
from script import send_whatsapp_message

class TestWhatsAppMessaging:
    def test_send_text_message(self, mock_wasender_client):
        """Test sending a text message via the WaSender API."""
        # Arrange
        with patch('script.wasender_client', mock_wasender_client):
            recipient = "1234567890@s.whatsapp.net"
            message = "Hello, this is a test message."
            
            # Act
            result = send_whatsapp_message(recipient, message, message_type='text')
            
            # Assert
            assert result is True
            mock_wasender_client.send_text.assert_called_once_with(
                to="1234567890",  # Should strip the @s.whatsapp.net part
                text_body=message
            )
    
    def test_send_image_message(self, mock_wasender_client):
        """Test sending an image message via the WaSender API."""
        # Arrange
        with patch('script.wasender_client', mock_wasender_client):
            recipient = "1234567890"
            caption = "Check out this image"
            media_url = "https://example.com/image.jpg"
            
            # Act
            result = send_whatsapp_message(recipient, caption, message_type='image', media_url=media_url)
            
            # Assert
            assert result is True
            mock_wasender_client.send_image.assert_called_once_with(
                to=recipient,
                url=media_url,
                caption=caption
            )
    
    def test_send_video_message(self, mock_wasender_client):
        """Test sending a video message via the WaSender API."""
        # Arrange
        with patch('script.wasender_client', mock_wasender_client):
            recipient = "1234567890"
            caption = "Check out this video"
            media_url = "https://example.com/video.mp4"
            
            # Act
            result = send_whatsapp_message(recipient, caption, message_type='video', media_url=media_url)
            
            # Assert
            assert result is True
            mock_wasender_client.send_video.assert_called_once_with(
                to=recipient,
                url=media_url,
                caption=caption
            )
    
    def test_send_audio_message(self, mock_wasender_client):
        """Test sending an audio message via the WaSender API."""
        # Arrange
        with patch('script.wasender_client', mock_wasender_client):
            recipient = "1234567890"
            message = ""  # Audio doesn't use caption
            media_url = "https://example.com/audio.mp3"
            
            # Act
            result = send_whatsapp_message(recipient, message, message_type='audio', media_url=media_url)
            
            # Assert
            assert result is True
            mock_wasender_client.send_audio.assert_called_once_with(
                to=recipient,
                url=media_url
            )
    
    def test_send_document_message(self, mock_wasender_client):
        """Test sending a document message via the WaSender API."""
        # Arrange
        with patch('script.wasender_client', mock_wasender_client):
            recipient = "1234567890"
            caption = "Check out this document"
            media_url = "https://example.com/document.pdf"
            
            # Act
            result = send_whatsapp_message(recipient, caption, message_type='document', media_url=media_url)
            
            # Assert
            assert result is True
            mock_wasender_client.send_document.assert_called_once_with(
                to=recipient,
                url=media_url,
                caption=caption
            )
    
    def test_send_message_missing_media_url(self, mock_wasender_client):
        """Test sending a media message without providing media_url."""
        # Arrange
        with patch('script.wasender_client', mock_wasender_client):
            recipient = "1234567890"
            caption = "This should fail"
            
            # Act
            result = send_whatsapp_message(recipient, caption, message_type='image')
            
            # Assert
            assert result is False
            mock_wasender_client.send_image.assert_not_called()
    
    def test_send_message_unsupported_type(self, mock_wasender_client):
        """Test sending a message with an unsupported type."""
        # Arrange
        with patch('script.wasender_client', mock_wasender_client):
            recipient = "1234567890"
            message = "This should fail"
            
            # Act
            result = send_whatsapp_message(recipient, message, message_type='unsupported_type')
            
            # Assert
            assert result is False
    
    def test_send_message_wasender_api_error(self, mock_wasender_client):
        """Test error handling when WaSender API raises an exception."""
        # Arrange
        from wasenderapi.errors import WasenderAPIError
        
        with patch('script.wasender_client', mock_wasender_client):
            mock_wasender_client.send_text.side_effect = WasenderAPIError(
                "Error sending message", 
                status_code=400
            )
            
            recipient = "1234567890"
            message = "This should handle the error"
            
            # Act
            result = send_whatsapp_message(recipient, message, message_type='text')
            
            # Assert
            assert result is False
    
    def test_send_message_without_wasender_client(self):
        """Test behavior when wasender_client is not initialized."""
        # Arrange
        with patch('script.wasender_client', None):
            recipient = "1234567890"
            message = "This should fail"
            
            # Act
            result = send_whatsapp_message(recipient, message, message_type='text')
            
            # Assert
            assert result is False
