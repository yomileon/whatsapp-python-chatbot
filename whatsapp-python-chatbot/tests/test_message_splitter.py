"""
test_message_splitter_improved.py - Tests for message splitting functionality
"""

import pytest
import sys
import os

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from message_splitter import split_message

class TestImprovedMessageSplitting:
    def test_empty_message(self):
        """Test splitting an empty message."""
        # Arrange & Act
        result = split_message("")
        
        # Assert
        assert result == []
    
    def test_short_message(self):
        """Test splitting a message that fits in a single chunk."""
        # Arrange
        message = "This is a short message."
        
        # Act
        result = split_message(message)
        
        # Assert
        assert len(result) == 1
        assert result[0] == message
    
    def test_multiline_message(self):
        """Test splitting a message with multiple lines."""
        # Arrange
        message = "Line 1\nLine 2\nLine 3\nLine 4"
        
        # Act
        result = split_message(message, max_lines=3)
        
        # Assert
        assert len(result) == 2
        assert result[0] == "Line 1\nLine 2\nLine 3"
        assert result[1] == "Line 4"
    
    def test_long_line_splitting(self):
        """Test splitting a single line that exceeds max_chars_per_line."""
        # Arrange
        long_word = "word" * 30  # 120 characters
        message = f"Start {long_word} end"
        
        # Act
        # Using a smaller max_chars_per_line to ensure splitting
        result = split_message(message, max_lines=3, max_chars_per_line=20)
        
        # Assert
        assert len(result) > 1  # Should be split into multiple chunks
        
        # Check that all key parts of the content are preserved
        combined = ''.join(result).replace('\n', ' ')
        assert "Start" in combined
        assert "end" in combined
        
        # Check all the "word" repetitions are included
        assert "word" * 30 in combined.replace(" ", "")
    
    def test_very_long_word_splitting(self):
        """Test that very long words (longer than max_chars_per_line) are properly split."""
        # Arrange
        super_long_word = "supercalifragilisticexpialidocious" * 5  # ~145 characters
        message = f"Before {super_long_word} after"
        
        # Act
        result = split_message(message, max_lines=2, max_chars_per_line=30)
        
        # Assert
        assert len(result) > 3  # Should be split into multiple chunks
        
        # Check that all parts are preserved (ignoring spaces which may change)
        combined = ''.join(result).replace('\n', '').replace(' ', '')
        expected = message.replace(' ', '')
        assert combined == expected
    
    def test_normalize_newlines(self):
        """Test that different newline formats are normalized."""
        # Arrange
        message = "Line 1\\nLine 2\r\nLine 3\nLine 4"
        
        # Act
        result = split_message(message, max_lines=2)
        
        # Assert
        assert len(result) == 2
        assert result[0] == "Line 1\nLine 2"
        assert result[1] == "Line 3\nLine 4"
    
    def test_empty_lines(self):
        """Test that empty lines are handled correctly."""
        # Arrange
        message = "Line 1\n\nLine 3\n\n\nLine 6"
        
        # Act
        result = split_message(message, max_lines=3)
        
        # Assert
        # The exact chunking may vary depending on implementation details
        # What's important is that all lines are preserved and appear in order
        combined = '\n'.join(result)
        assert "Line 1" in combined
        assert "Line 3" in combined
        assert "Line 6" in combined
        
        # Verify lines appear in the correct order
        line1_pos = combined.find("Line 1")
        line3_pos = combined.find("Line 3")
        line6_pos = combined.find("Line 6")
        assert line1_pos < line3_pos < line6_pos
    
    def test_max_lines_respected(self):
        """Test that max_lines parameter is respected."""
        # Arrange
        message = "1\n2\n3\n4\n5\n6\n7\n8\n9\n10"
        
        # Act
        result = split_message(message, max_lines=4)
        
        # Assert
        assert len(result) == 3  # Should split into 3 chunks (4+4+2 lines)
        for chunk in result[:-1]:  # All chunks except last should have exactly max_lines
            assert chunk.count('\n') == 3  # 4 lines means 3 newlines
    
    def test_mixed_content(self):
        """Test with a mix of normal lines, long lines, and empty lines."""
        # Arrange
        mixed_content = (
            "Normal line\n"
            "\n"  # Empty line
            "This is a very long line that should be split into multiple pieces because it exceeds the maximum character limit\n"
            "Short line\n"
            "\n"  # Another empty line
            "Final line"
        )
        
        # Act
        result = split_message(mixed_content, max_lines=2, max_chars_per_line=30)
        
        # Assert
        assert len(result) > 2  # Should be split into multiple chunks
        
        # Check that all the content is preserved
        content = '\n'.join(result)
        for line in ["Normal line", "This is a very long line", "Short line", "Final line"]:
            assert line in content
    
    def test_consecutive_empty_lines(self):
        """Test handling of multiple consecutive empty lines."""
        # Arrange
        message = "Line 1\n\n\n\nLine 5"
        
        # Act
        result = split_message(message, max_lines=3)
        
        # Assert
        assert "Line 1" in result[0]
        assert "Line 5" in result[-1]  # Should be in last chunk
