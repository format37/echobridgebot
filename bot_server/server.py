from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
import os
import logging
import json
import telebot
from telebot.formatting import escape_markdown
from datetime import datetime
# from langchain.chat_models import ChatOpenAI
# from langchain.memory import ConversationBufferMemory
# from langchain.chains import ConversationChain
from langchain_openai import ChatOpenAI

# Initialize FastAPI
app = FastAPI()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load config
with open('config.json') as config_file:
    config = json.load(config_file)

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

@app.post("/message")
async def call_message(request: Request, authorization: str = Header(None)):
    message = await request.json()
    logger.info(message)

    if not user_access(message):
        return JSONResponse(content={
            "type": "text", 
            "body": "You are not authorized to use this bot."
        })

    if 'text' not in message:
        return JSONResponse(content={"type": "empty", "body": ''})

    chat_id = message['chat']['id']
    text = message['text']

    # Handle /reset command
    if text == '/reset':
        return JSONResponse(content={
            "type": "text",
            "body": "Command no longer needed - chat is stateless"
        })

    # Direct LLM call instead of using conversation chain
    response = llm.invoke(text).content

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