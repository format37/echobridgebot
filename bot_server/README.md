# How to build
0. First steps:
init
```
git clone https://github.com/format37/echobridgebot.git
cd echobridgebot
```
(logout)[https://github.com/format37/telegram_bot] your bot from the official telegram server and restart the bot server.
```
cd ~/projects/telegram_bot/logout
python3 logout.py
cd ..
sh compose.sh
```

1. Define the config.json with the following content
```
cd echobridgebot/bot_server
nano config.json
```
Content:
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
Define your bot token in the run.sh and logs.sh  
Define your port in the Dockerfile if necessary
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
6. To run ngrok as a daemon:
Edit ngrok config
```
mkdir ~/.ngrok2
nano ~/.ngrok2/ngrok.yml
```
Update your token and url as ngrok site provides
```
version: "3"
agent:
    authtoken: your_token
endpoints:
  - name: tts-tunnel
    url: your_url
    upstream:
      url: 5000
```
Install ngrok as a service:
```
sudo ngrok service install --config ~/.ngrok2/ngrok.yml
```
Start the ngrok service:
```
ngrok service start
```
Check
```
sudo systemctl status ngrok
```