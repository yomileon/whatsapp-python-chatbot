import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai
import json
from wasenderapi import create_sync_wasender, WasenderSyncClient
from wasenderapi.errors import WasenderAPIError
from wasenderapi.webhook import WasenderWebhookEvent
from wasenderapi.models import RetryConfig
import asyncio
import time
from functools import wraps
from message_splitter import split_message

# Load environment variables
load_dotenv()

# Flask application setup
app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('whatsapp_bot.log')
    ]
)
logger = logging.getLogger("whatsapp_bot")

# Application configuration
CONFIG = {
    "CONVERSATIONS_DIR": os.getenv('CONVERSATIONS_DIR', 'conversations'),
    "GEMINI_API_KEY": os.getenv('GEMINI_API_KEY'),
    "WASENDER_API_TOKEN": os.getenv('WASENDER_API_TOKEN'),
    "GEMINI_MODEL": os.getenv('GEMINI_MODEL', 'gemini-2.0-flash'),
    "WEBHOOK_SECRET": os.getenv('WEBHOOK_SECRET'),
    "MAX_RETRIES": int(os.getenv('MAX_RETRIES', '3')),
    "MESSAGE_CHUNK_MAX_LINES": int(os.getenv('MESSAGE_CHUNK_MAX_LINES', '3')),
    "MESSAGE_CHUNK_MAX_CHARS": int(os.getenv('MESSAGE_CHUNK_MAX_CHARS', '100')),
    "MESSAGE_DELAY_MIN": float(os.getenv('MESSAGE_DELAY_MIN', '0.55')),
    "MESSAGE_DELAY_MAX": float(os.getenv('MESSAGE_DELAY_MAX', '1.5')),
}

# Directory for storing conversations
if not os.path.exists(CONFIG["CONVERSATIONS_DIR"]):
    os.makedirs(CONFIG["CONVERSATIONS_DIR"])
    logger.info(f"Created conversations directory at {CONFIG['CONVERSATIONS_DIR']}")

# Configure retry options for WaSenderAPI
retry_config = RetryConfig(
    enabled=True,
    max_retries=CONFIG["MAX_RETRIES"]
)

# Initialize WaSenderAPI client
try:
    wasender_client = create_sync_wasender(
        api_key=CONFIG["WASENDER_API_TOKEN"],
        webhook_secret=CONFIG["WEBHOOK_SECRET"],
        retry_options=retry_config
    )
    logger.info("WaSenderAPI client initialized successfully with retry support")
except Exception as e:
    logger.error(f"Error initializing WaSenderAPI client: {e}", exc_info=True)
    wasender_client = None

# Initialize Gemini client
if CONFIG["GEMINI_API_KEY"]:
    genai.configure(api_key=CONFIG["GEMINI_API_KEY"])
    logger.info("Gemini API client initialized successfully")
else:
    logger.error("GEMINI_API_KEY not found in environment variables. The application might not work correctly.")

@app.errorhandler(Exception)
def handle_global_exception(e):
    """Global handler for unhandled exceptions."""
    logger.error(f"Unhandled Exception: {e}", exc_info=True)
    return jsonify(status='error', message='An internal server error occurred.'), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    status = {
        'status': 'ok',
        'wasender_client': wasender_client is not None,
        'gemini_client': CONFIG["GEMINI_API_KEY"] is not None,
        'conversations_dir': os.path.exists(CONFIG["CONVERSATIONS_DIR"]),
        'timestamp': time.time()
    }
    
    if not wasender_client:
        status['status'] = 'degraded'
        status['issues'] = ['WaSender client not initialized']
    
    if not CONFIG["GEMINI_API_KEY"]:
        status['status'] = 'degraded'
        if 'issues' not in status:
            status['issues'] = []
        status['issues'].append('Gemini API key not configured')
    
    status_code = 200 if status['status'] == 'ok' else 503
    return jsonify(status), status_code



# --- Load Persona ---
def load_persona(file_path='persona.json'):
    """
    Load persona configuration from a JSON file.
    Returns a tuple of (persona_description, persona_name).
    """
    default_name = "Assistant"
    default_description = "You are a helpful assistant."
    default_base_prompt = (
        "You are a helpful and concise AI assistant replying in a WhatsApp chat. "
        "Do not use Markdown formatting. Keep your answers short, friendly, and easy to read. "
        "Split long answers every 3 lines using a real newline character Use \n to break the message."
        "Each \n means a new WhatsApp message. Avoid long paragraphs or unnecessary explanations."
    )

    try:
        if not os.path.exists(file_path):
            logger.warning(f"Persona file not found at {file_path}. Using default persona.")
            return f"{default_base_prompt}\n\n{default_description}", default_name
            
        with open(file_path, 'r') as f:
            persona_data = json.load(f)
            
        custom_description = persona_data.get('description', default_description)
        base_prompt = persona_data.get('base_prompt', default_base_prompt)
        persona_name = persona_data.get('name', default_name)
        
        full_persona = f"{base_prompt}\n\n{custom_description}"
        logger.info(f"Successfully loaded persona: {persona_name}")
        
        return full_persona, persona_name
        
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {file_path}. Using default persona.")
        return f"{default_base_prompt}\n\n{default_description}", default_name
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading persona: {e}. Using default persona.")
        return f"{default_base_prompt}\n\n{default_description}", default_name

# Load persona configuration
PERSONA_FILE_PATH = os.getenv('PERSONA_FILE_PATH', 'persona.json')
PERSONA_DESCRIPTION, PERSONA_NAME = load_persona(PERSONA_FILE_PATH)
logger.info(f"Using persona '{PERSONA_NAME}'")
# --- End Load Persona ---

class ConversationManager:
    """Manages conversation history with context window management."""
    
    def __init__(self, storage_dir, max_history=10):
        """
        Initialize the conversation manager.
        
        Args:
            storage_dir: Directory to store conversation histories
            max_history: Maximum number of message pairs to retain in history
        """
        self.storage_dir = storage_dir
        self.max_history = max_history
        
    def load(self, user_id):
        """
        Load conversation history for a given user_id with context window management.
        
        Args:
            user_id: The user identifier
            
        Returns:
            A list of message dictionaries suitable for Gemini
        """
        file_path = os.path.join(self.storage_dir, f"{user_id}.json")
        
        try:
            if not os.path.exists(file_path):
                return []
                
            with open(file_path, 'r') as f:
                history = json.load(f)
                
            # Validate history format
            if not isinstance(history, list) or not all(
                isinstance(item, dict) and 'role' in item and 'parts' in item 
                for item in history):
                logger.warning(f"Invalid history format in {file_path}. Starting fresh.")
                return []
                
            # Limit history to most recent exchanges to prevent context overflow
            if len(history) > self.max_history * 2:  # Each exchange is 2 messages (user + model)
                logger.info(f"Trimming history for {user_id} to last {self.max_history} exchanges")
                history = history[-self.max_history * 2:]
                
            return history
                
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {file_path}. Starting fresh.")
            return []
        except Exception as e:
            logger.error(f"Unexpected error loading history from {file_path}: {e}")
            return []
            
    def save(self, user_id, history):
        """
        Saves conversation history for a given user_id.
        
        Args:
            user_id: The user identifier
            history: The conversation history to save
        """
        file_path = os.path.join(self.storage_dir, f"{user_id}.json")
        
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save the history
            with open(file_path, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving conversation history to {file_path}: {e}")
    
    def add_exchange(self, user_id, user_message, model_response):
        """
        Add a new message exchange to the conversation history.
        
        Args:
            user_id: The user identifier
            user_message: The message from the user
            model_response: The response from the model
        """
        history = self.load(user_id)
        
        # Add the new exchange
        history.append({'role': 'user', 'parts': [user_message]})
        history.append({'role': 'model', 'parts': [model_response]})
        
        # Save the updated history
        self.save(user_id, history)
        
        return history

# Initialize the conversation manager
conversation_manager = ConversationManager(CONFIG["CONVERSATIONS_DIR"], max_history=20)

def load_conversation_history(user_id):
    """Loads conversation history for a given user_id."""
    return conversation_manager.load(user_id)

def save_conversation_history(user_id, history):
    """Saves conversation history for a given user_id."""
    conversation_manager.save(user_id, history)

class GeminiClient:
    """Client for interacting with the Gemini AI API."""
    
    def __init__(self, api_key, model_name, system_instruction):
        """
        Initialize the Gemini client.
        
        Args:
            api_key: The Gemini API key
            model_name: The model to use (e.g., 'gemini-2.0-flash')
            system_instruction: System instruction for persona
        """
        self.api_key = api_key
        self.model_name = model_name
        self.system_instruction = system_instruction
        
        if not api_key:
            logger.error("Gemini API key is not configured.")
            raise ValueError("Gemini API key is required")
            
        genai.configure(api_key=api_key)
        logger.info(f"Gemini client initialized with model: {model_name}")
        
    def generate_response(self, message_text, conversation_history=None):
        """
        Generate a response from Gemini using the provided message and optional history.
        
        Args:
            message_text: The message to respond to
            conversation_history: Optional conversation history
            
        Returns:
            The generated response text
        """
        if not self.api_key:
            logger.error("Gemini API key is not configured.")
            return "Sorry, I'm having trouble connecting to my brain right now (API key issue)."

        try:
            # Create model with system instruction for persona
            model = genai.GenerativeModel(
                self.model_name, 
                system_instruction=self.system_instruction
            )
            
            logger.info(f"Sending prompt to Gemini (system persona active): {message_text[:200]}...")

            if conversation_history:
                # Use chat history if available
                chat = model.start_chat(history=conversation_history)
                response = chat.send_message(message_text)
            else:
                # For first message with no history
                response = model.generate_content(message_text)

            # Extract the text from the response
            if response and hasattr(response, 'text') and response.text:
                return response.text.strip()
            elif response and response.candidates:
                # Fallback if .text is not directly available but candidates are
                try:
                    return response.candidates[0].content.parts[0].text.strip()
                except (IndexError, AttributeError, KeyError) as e:
                    logger.error(f"Error parsing Gemini response candidates: {e}. Response: {response}")
                    return "I received an unusual response structure from Gemini. Please try again."
            else:
                logger.error(f"Gemini API returned an empty or unexpected response: {response}")
                return "I received an empty or unexpected response from Gemini. Please try again."

        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}", exc_info=True)
            return "I'm having trouble processing that request with my AI brain. Please try again later."

# Initialize Gemini client if API key is available
gemini_client = None
if CONFIG["GEMINI_API_KEY"]:
    try:
        gemini_client = GeminiClient(
            api_key=CONFIG["GEMINI_API_KEY"],
            model_name=CONFIG["GEMINI_MODEL"],
            system_instruction=PERSONA_DESCRIPTION
        )
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {e}", exc_info=True)

def get_gemini_response(message_text, conversation_history=None):
    """
    Generates a response from Gemini using the gemini_client.
    This wrapper maintains compatibility with the existing code.
    """
    if not gemini_client:
        logger.error("Gemini client is not initialized.")
        return "Sorry, I'm having trouble connecting to my brain right now (API key issue)."
    
    return gemini_client.generate_response(message_text, conversation_history)

def send_whatsapp_message(recipient_number, message_content, message_type='text', media_url=None):
    """Sends a message via WaSenderAPI SDK. Supports text and media messages."""
    if not wasender_client:
        logger.error("WaSender API client is not initialized. Please check .env file.")
        return False
    
    # Sanitize recipient_number to remove "@s.whatsapp.net"
    if recipient_number and "@s.whatsapp.net" in recipient_number:
        formatted_recipient_number = recipient_number.split('@')[0]
    else:
        formatted_recipient_number = recipient_number
    
    try:
        if message_type == 'text':
            response = wasender_client.send_text(
                to=formatted_recipient_number,
                text_body=message_content
            )
            logger.info(f"Text message sent to {recipient_number}.")
            return True
        elif message_type == 'image' and media_url:
            response = wasender_client.send_image(
                to=formatted_recipient_number,
                url=media_url,
                caption=message_content if message_content else None
            )
            logger.info(f"Image message sent to {recipient_number}.")
            return True
        elif message_type == 'video' and media_url:
            response = wasender_client.send_video(
                to=formatted_recipient_number,
                url=media_url,
                caption=message_content if message_content else None
            )
            logger.info(f"Video message sent to {recipient_number}. ")
            return True
        elif message_type == 'audio' and media_url:
            response = wasender_client.send_audio(
                to=formatted_recipient_number,
                url=media_url
            )
            logger.info(f"Audio message sent to {recipient_number}.")
            return True
        elif message_type == 'document' and media_url:
            response = wasender_client.send_document(
                to=formatted_recipient_number,
                url=media_url,
                caption=message_content if message_content else None
            )
            logger.info(f"Document message sent to {recipient_number}. ")
            return True
        else:
            if message_type != 'text':
                logger.error(f"Media URL is required for message type '{message_type}'.")
                return False
            logger.error(f"Unsupported message type or missing content/media_url: {message_type}")
            return False
    except WasenderAPIError as e:
        logger.error(f"WaSenderAPI Error sending {message_type} to {recipient_number}: {e.message} (Status: {e.status_code})")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending WhatsApp message: {e}")
        return False

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handles incoming WhatsApp messages via webhook using the WaSenderAPI SDK."""
    try:        
        if not wasender_client:
            logger.error("WaSender API client is not initialized. Cannot process webhook.")
            return jsonify({'status': 'error', 'message': 'WaSender client not initialized'}), 500

        data = request.json
        if data.get('event') == 'messages.upsert' and data.get('data') and data['data'].get('messages'):
                message_info = data['data']['messages']
                
                # Check if it's a message sent by the bot itself
                if message_info.get('key', {}).get('fromMe'):
                    logger.info(f"Ignoring self-sent message: {message_info.get('key', {}).get('id')}")
                    return jsonify({'status': 'success', 'message': 'Self-sent message ignored'}), 200

                sender_number = message_info.get('key', {}).get('remoteJid')
                
                incoming_message_text = None
                message_type = 'unknown'

                # Extract message content based on message structure
                if message_info.get('message'):
                    msg_content_obj = message_info['message']
                    if 'conversation' in msg_content_obj:
                        incoming_message_text = msg_content_obj['conversation']
                        message_type = 'text'
                    elif 'extendedTextMessage' in msg_content_obj and 'text' in msg_content_obj['extendedTextMessage']:
                        incoming_message_text = msg_content_obj['extendedTextMessage']['text']
                        message_type = 'text'

                if not sender_number:
                    logger.warning("Webhook received message without sender information.")
                    return jsonify({'status': 'error', 'message': 'Incomplete sender data'}), 400

                safe_sender_id = "".join(c if c.isalnum() else '_' for c in sender_number)
                
                # we should do this in queue in production if we take too long to respond the request will timeout
                if message_type == 'text' and incoming_message_text:
                    conversation_history = load_conversation_history(safe_sender_id)
                    gemini_reply = get_gemini_response(incoming_message_text, conversation_history)
                    
                    if gemini_reply:
                        message_chunks = split_message(gemini_reply)
                        print(f"Sending {len(message_chunks)} message chunks to {sender_number}")
                        for i, chunk in enumerate(message_chunks):
                            if not send_whatsapp_message(sender_number, chunk, message_type='text'):
                                logger.error(f"Failed to send message chunk to {sender_number}")
                                break
                            # Delay between messages
                            import random
                            import time
                            if i < len(message_chunks) - 1:
                                delay = random.uniform(5, 7)
                                time.sleep(delay)
                        
                        # Save conversation history
                        conversation_manager.add_exchange(safe_sender_id, incoming_message_text, gemini_reply)
            
                return jsonify({'status': 'success'}), 200
            
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@app.route('/status', methods=['GET'])
def status():
    """Get status information about the service."""
    return jsonify({
        'status': 'active',
        'version': '1.0.0',
        'persona': PERSONA_NAME,
        'services': {
            'wasender': wasender_client is not None,
            'gemini': gemini_client is not None,
        },
        'config': {
            'conversation_dir': CONFIG["CONVERSATIONS_DIR"],
            'gemini_model': CONFIG["GEMINI_MODEL"],
        }
    })

@app.route('/clear_history/<user_id>', methods=['POST'])
def clear_history(user_id):
    """Clear conversation history for a user."""
    try:
        # Sanitize user_id to prevent directory traversal
        safe_user_id = "".join(c if c.isalnum() else '_' for c in user_id)
        file_path = os.path.join(CONFIG["CONVERSATIONS_DIR"], f"{safe_user_id}.json")
        
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleared conversation history for {safe_user_id}")
            return jsonify({'status': 'success', 'message': f'History cleared for {safe_user_id}'}), 200
        else:
            logger.info(f"No conversation history found for {safe_user_id}")
            return jsonify({'status': 'success', 'message': f'No history found for {safe_user_id}'}), 200
    except Exception as e:
        logger.error(f"Error clearing history for {user_id}: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

if __name__ == '__main__':
    # Display startup information
    logger.info("======================================================")
    logger.info("  WhatsApp Gemini Chatbot Starting")
    logger.info("======================================================")
    logger.info(f"Persona: {PERSONA_NAME}")
    logger.info(f"Gemini Model: {CONFIG['GEMINI_MODEL']}")
    logger.info(f"Conversations Directory: {CONFIG['CONVERSATIONS_DIR']}")
    logger.info(f"WaSender API Client: {'Initialized' if wasender_client else 'NOT INITIALIZED'}")
    logger.info(f"Gemini API Client: {'Initialized' if gemini_client else 'NOT INITIALIZED'}")
    logger.info(f"Starting Flask server on port 5001...")
    logger.info("======================================================")
    
    # For development with webhook testing via ngrok
    port = int(os.getenv('PORT', '5001'))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug, port=port, host='0.0.0.0')
