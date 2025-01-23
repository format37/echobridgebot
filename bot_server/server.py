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
        message_data = {
            "role": role,
            "content": text
        }
    else:
        message_data = {
            "role": role,
            "content": text
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
                total_length += len(content['content'])
                files.append((filepath, os.path.getctime(filepath), content))

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
            if isinstance(message_data['content'], dict):
                # Handle conversation format
                history.extend([
                    ("user", message_data['content']['user_message']),
                    ("assistant", message_data['content']['assistant_response'])
                ])
            else:
                # Handle legacy format
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

    # Store the user's message for later
    user_message = text

    # Get chat history and create prompt template
    chat_history = get_chat_history(user_id)
    
    # Create prompt template with history placeholder
    history_placeholder = MessagesPlaceholder("history")
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful AI assistant."),
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
            "user_message": user_message,
            "assistant_response": response
        },
        role="conversation"
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