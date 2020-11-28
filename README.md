# DiscordBot
Bot for guild's discord server to add gold values to a sheet. Includes a gambling game as well.

--------------------------

# Necessary packages

++++
pip3 install gspread discord.py python-dotenv gspread-formatting
```
gspread: call google API
discord.py
dotenv: loads .env for setting


--------------------------
# Discord Token
.env needs to have one line with the discord bot token key

```
DISCORD_TOKEN=############
```

--------------------------
# botCreds.json
You need a .json credential, generated via service account at
https://gspread.readthedocs.io/en/latest/oauth2.html
The service account needs access to both sheets.
Name the file "botCreds.json"
