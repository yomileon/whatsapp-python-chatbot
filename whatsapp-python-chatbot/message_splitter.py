import re

"""
message_splitter.py - Implementation of the message splitting functionality
"""

def split_message(text, max_lines=3, max_chars_per_line=100):
    """
    The main message splitting function, used throughout the application.
    This is just an alias to keep backwards compatibility.
    """
    return split_message_impl(text, max_lines, max_chars_per_line)

def split_message_impl(text, max_lines=3, max_chars_per_line=100):
    """
    Split a long message into smaller chunks for better WhatsApp readability.
    This improved implementation properly handles long lines without newlines.
    
    Args:
        text: The text to split
        max_lines: Maximum lines per message chunk
        max_chars_per_line: Maximum characters per line
        
    Returns:
        List of message chunks ready to send
    """
    if not text:
        return []
    
    # Convert escaped newlines and normalize line endings
    normalized_text = text.replace('\\n', '\n').replace('\r\n', '\n')
    
    # Remove standalone backslashes using regex
    normalized_text = re.sub(r'\n\s*\\\s*\n', '\n', normalized_text)
    normalized_text = re.sub(r'^\s*\\\s*\n', '', normalized_text)
    normalized_text = re.sub(r'\n\s*\\\s*$', '', normalized_text)
    
    # Split by existing newlines
    paragraphs = normalized_text.split('\n')
    chunks = []
    current_chunk = []
    current_line_count = 0
    
    for paragraph in paragraphs:
        # Handle empty paragraphs
        if not paragraph.strip():
            if current_line_count >= max_lines:
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_line_count = 0
            
            if current_line_count < max_lines:
                current_chunk.append('')
                current_line_count += 1
            continue
        
        # For paragraphs longer than max_chars_per_line, break them up
        if len(paragraph) > max_chars_per_line:
            words = paragraph.split()
            
            # Special case: single very long word
            if len(words) == 1:
                word = words[0]
                for i in range(0, len(word), max_chars_per_line):
                    if current_line_count >= max_lines:
                        if current_chunk:
                            chunks.append('\n'.join(current_chunk))
                        current_chunk = []
                        current_line_count = 0
                    current_chunk.append(word[i:i+max_chars_per_line])
                    current_line_count += 1
                continue
            
            # Regular case: paragraph with multiple words
            current_line = []
            current_length = 0
            
            for word in words:
                # Handle very long words
                if len(word) > max_chars_per_line:
                    # Add accumulated words first
                    if current_line:
                        if current_line_count >= max_lines:
                            if current_chunk:
                                chunks.append('\n'.join(current_chunk))
                            current_chunk = []
                            current_line_count = 0
                        current_chunk.append(' '.join(current_line))
                        current_line_count += 1
                        current_line = []
                        current_length = 0
                    
                    # Split the long word
                    for i in range(0, len(word), max_chars_per_line):
                        if current_line_count >= max_lines:
                            if current_chunk:
                                chunks.append('\n'.join(current_chunk))
                            current_chunk = []
                            current_line_count = 0
                        current_chunk.append(word[i:i+max_chars_per_line])
                        current_line_count += 1
                
                # Normal word handling
                elif current_length + len(word) + (1 if current_line else 0) > max_chars_per_line:
                    # Finalize current line
                    if current_line:
                        if current_line_count >= max_lines:
                            if current_chunk:
                                chunks.append('\n'.join(current_chunk))
                            current_chunk = []
                            current_line_count = 0
                        current_chunk.append(' '.join(current_line))
                        current_line_count += 1
                    
                    # Start new line with this word
                    current_line = [word]
                    current_length = len(word)
                
                else:
                    # Word fits on current line
                    if current_line:
                        current_length += 1  # space
                    current_line.append(word)
                    current_length += len(word)
            
            # Add the last line if it exists
            if current_line:
                if current_line_count >= max_lines:
                    if current_chunk:
                        chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_line_count = 0
                current_chunk.append(' '.join(current_line))
                current_line_count += 1
        
        else:
            # Paragraph fits on one line
            if current_line_count >= max_lines:
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_line_count = 0
            current_chunk.append(paragraph)
            current_line_count += 1
    
    # Add the final chunk
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks