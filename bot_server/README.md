# How to build
1. Define the config.json with the following content
```
{
    "TOKEN": "",
    "OPENAI_API_KEY": "",
    "LANGSMITH_API_KEY": "",
    "LANGSMITH_PROJECT": "echobridgebot",
    "HISTORY_THRESHOLD": 4000
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
sh build.sh
sh run.sh
sh logs.sh
```
4. Check that bot is able to answer