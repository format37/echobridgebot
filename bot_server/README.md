# How to build
1. Define the config.json with the following content
```
{
    "TOKEN": "",
    "OPENAI_API_KEY": "",
    "LANGSMITH_API_KEY": "",
    "LANGSMITH_PROJECT": "echobridgebot",
    "HISTORY_THRESHOLD": 4000,
    "TTS_API_URL": "http://localhost:5000"
}
```
Where TOKEN is a telegram bot token
Langchain monitoring can be defined on the [langsmith site](https://smith.langchain.com).
2. Go to [telegram_bot](https://github.com/format37/telegram_bot) and add your new bot in the bots.json as follows
```
    "ECHOBRIDGEBOT":{
        "PORT": 4222,
        "TOKEN": "",
        "bot": "",
        "active": 1
    }
```
where TOKEN is a telegram bot token
And restart the telegram_bot container
```
sh compose.sh
```
3. Return to echobridgebot/bot_server and run
```
cd ../bots/echobridgebot/bot_server
chmod +x build.sh
chmod +x run.sh
chmod +x logs.sh
sh build_and_run.sh
```
4. Check that bot is able to answer
# NGROK installation to provide the IP channel voice cloning feature
1. Installation
```
sudo snap install ngrok
```
2. login to ngrok.com and get instruction on how to install, configure and run
3. Run:
```
ngrok http http://localhost:5000
```
4. Update the TTS_API_URL in the bot_server/config.json
5. Restart the bot_server:
```
sh build_and_run.sh
```