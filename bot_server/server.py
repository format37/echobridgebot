from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
import os
import logging
import json
import telebot
from telebot.formatting import escape_markdown
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Union
import requests

# Initialize FastAPI
app = FastAPI()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load config
with open('config.json') as config_file:
    config = json.load(config_file)
    HISTORY_THRESHOLD = config.get('HISTORY_THRESHOLD', 4000)  # Default to 4000 chars if not specified

# Set environment variables for LangSmith
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGSMITH_API_KEY"] = config["LANGSMITH_API_KEY"]
os.environ["LANGSMITH_PROJECT"] = config["LANGSMITH_PROJECT"]
os.environ["OPENAI_API_KEY"] = config["OPENAI_API_KEY"]

# Configure Telegram bot API endpoints
server_api_uri = 'http://localhost:8081/bot{0}/{1}'
telebot.apihelper.API_URL = server_api_uri
server_file_url = 'http://localhost:8081'
telebot.apihelper.FILE_URL = server_file_url

# Initialize bot from config
with open('config.json') as config_file:
    config = json.load(config_file)
    bot = telebot.TeleBot(config['TOKEN'])
    
# Initialize OpenAI chat model
llm = ChatOpenAI(
    model_name="gpt-4",
    openai_api_key=config['OPENAI_API_KEY']
)

def user_access(message):
    with open('data/users.txt') as f:
        users = f.read().splitlines()
    return str(message['from']['id']) in users

def manage_chat_history(user_id: str, message_id: str, text: Union[str, dict], role: str = "user"):
    """Manages chat history for a user, storing messages and pruning old ones."""
    # Create user directory if it doesn't exist
    user_dir = f'data/users/{user_id}'
    os.makedirs(user_dir, exist_ok=True)

    # Save current message
    date = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{date}_{message_id}.json'
    
    if isinstance(text, dict):
        # Store directly in new format
        message_data = text
    else:
        # Legacy single message format
        message_data = {
            role: text
        }
    
    with open(os.path.join(user_dir, filename), 'w', encoding='utf-8') as f:
        json.dump(message_data, f, ensure_ascii=False)

    # Get all message files and their creation times
    files = []
    total_length = 0
    for f in os.listdir(user_dir):
        if f.endswith('.json'):
            filepath = os.path.join(user_dir, f)
            with open(filepath, 'r', encoding='utf-8') as file:
                content = json.load(file)
                # Calculate length based on the format of the message
                if 'user' in content and 'assistant' in content:
                    # New format
                    total_length += len(content['user']) + len(content['assistant'])
                elif 'content' in content:
                    # Old format
                    if isinstance(content['content'], dict):
                        total_length += len(content['content']['user_message']) + len(content['content']['assistant_response'])
                    else:
                        total_length += len(content['content'])
                else:
                    # Single message format
                    total_length += sum(len(v) for v in content.values())

    # Sort files by creation time (oldest first)
    files.sort(key=lambda x: x[1])

    # Remove oldest files until total length is below threshold
    while total_length > HISTORY_THRESHOLD and files:
        filepath, _, content = files[0]
        total_length -= len(content['content'])
        os.remove(filepath)
        files.pop(0)

def get_chat_history(user_id: str) -> list:
    """Retrieves chat history for a user as a list of message tuples."""
    user_dir = f'data/users/{user_id}'
    if not os.path.exists(user_dir):
        return []

    # Get all message files and their creation times
    files = []
    for f in os.listdir(user_dir):
        if f.endswith('.json'):
            filepath = os.path.join(user_dir, f)
            files.append((filepath, os.path.getctime(filepath)))

    # Sort files by creation time (oldest first)
    files.sort(key=lambda x: x[1])

    # Build chat history list
    history = []
    for filepath, _ in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            message_data = json.load(f)
            if 'user' in message_data and 'assistant' in message_data:
                # Handle new format
                history.extend([
                    ("user", message_data['user']),
                    ("assistant", message_data['assistant'])
                ])
            elif isinstance(message_data.get('content'), dict):
                # Handle old conversation format
                content = message_data['content']
                history.extend([
                    ("user", content['user_message']),
                    ("assistant", content['assistant_response'])
                ])
            else:
                # Handle legacy single message format
                history.append((message_data['role'], message_data['content']))

    return history

def clear_chat_history(user_id: str) -> None:
    """Clears all chat history for a given user."""
    user_dir = f'data/users/{user_id}'
    if os.path.exists(user_dir):
        for file in os.listdir(user_dir):
            if file.endswith('.json'):
                os.remove(os.path.join(user_dir, file))

@app.post("/message")
async def call_message(request: Request, authorization: str = Header(None)):
    message = await request.json()
    logger.info(message)

    if not user_access(message):
        return JSONResponse(content={
            "type": "text", 
            "body": "You are not authorized to use this bot."
        })

    chat_id = message['chat']['id']
    user_id = str(message['from']['id'])

    # Handle audio document
    if 'document' in message and 'mime_type' in message['document'] and 'audio' in message['document']['mime_type']:
        bot.send_message(
            chat_id,
            "Audio file received",
            reply_to_message_id=message['message_id']
        )
        return JSONResponse(content={"type": "empty", "body": ''})

    # Handle voice message
    if 'voice' in message and 'audio' in message['voice']['mime_type']:
        voice_file_id = message['voice']['file_id']
        duration = message['voice']['duration']
        
        if duration < 1:
            response = "Voice message received, but duration is too short"
        elif duration > 60:
            response = "Voice message received, but duration is too long"
        else:
            # Create temp directory if it doesn't exist
            temp_dir = 'data/temp'
            os.makedirs(temp_dir, exist_ok=True)
            
            # Get the file path using the Telegram API
            file_info = bot.get_file(voice_file_id)
            file_path = file_info.file_path
            
            # Download and save the audio file
            downloaded_file = bot.download_file(file_path)
            audio_path = os.path.join(temp_dir, f'{user_id}.ogg')
            with open(audio_path, 'wb') as audio_file:
                audio_file.write(downloaded_file)
            
            response = f"Voice message received and saved successfully"
            
        bot.send_message(
            chat_id,
            response,
            reply_to_message_id=message['message_id']
        )
        return JSONResponse(content={"type": "empty", "body": ''})

    # Original text message handling
    if 'text' not in message:
        bot.send_message(
            chat_id,
            "Sorry, this message type is not supported yet.",
            reply_to_message_id=message['message_id']
        )
        return JSONResponse(content={"type": "empty", "body": ''})

    text = message['text']

    if text == '/reset':
        clear_chat_history(user_id)
        bot.send_message(
            chat_id,
            "Chat history has been reset.",
            reply_to_message_id=message['message_id']
        )
        return JSONResponse(content={"type": "empty", "body": ''})
    
    if text == '/start':
        try:
            with open('greeting.txt', 'r') as f:
                greeting = f.read()
            bot.send_message(
                chat_id,
                greeting,
                reply_to_message_id=message['message_id']
            )
            return JSONResponse(content={"type": "empty", "body": ''})
        except FileNotFoundError:
            logger.error("greeting.txt not found")
            bot.send_message(
                chat_id,
                "Welcome! I'm Janet, your AI assistant.",
                reply_to_message_id=message['message_id']
            )
            return JSONResponse(content={"type": "empty", "body": ''})

    # Store the user's message for later
    user_message = text

    # Get chat history and create prompt template
    chat_history = get_chat_history(user_id)
    
    # Create prompt template with history placeholder
    history_placeholder = MessagesPlaceholder("history")
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "Your name is Janet. You are a helpful AI assistant."),
        history_placeholder,
        ("human", "{question}")
    ])

    # Generate prompt with chat history
    prompt_value = prompt_template.invoke({
        "history": chat_history,
        "question": text
    })

    # Get response from LLM
    response = llm.invoke(prompt_value).content

    # Store both user message and LLM response in a single file
    manage_chat_history(
        user_id, 
        str(message['message_id']), 
        {
            "user": user_message,
            "assistant": response
        }
    )

    # Send response via Telegram
    try:
        bot.send_message(
            chat_id,
            response,
            reply_to_message_id=message['message_id'],
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f'Error sending message: {e}')
        bot.send_message(chat_id, response)

    return JSONResponse(content={"type": "empty", "body": ''})

@app.get("/test")
async def call_test():
    return JSONResponse(content={"status": "ok"})