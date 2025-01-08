# TableTop
A Discord bot written using the discord.py library for simple tabletop games with friends in your server.

**Currently in beta, now using Discord's Interaction model for bots**

## Commands
### Game Commands
The most commonly used commands, with the main functions of the bot - games. Each game is contained in its own file within the `games` folder

- **connect4 (opponent:discord.Member)**
  - Two players take turns dropping counters onto a 7x6 grid and get four in a row horizontally, vertically or diagonally to win.
- **megaconnect4**
  - Connect 4, but for 4 players. Includes a larger 11x10 grid.
- **tictactoe (opponent:discord.Member)**
  - Two players take turns claiming squares on a 3x3 grid and get three in a row horizontally, vertically or diagonally to win.

(More coming soon)

### Misc/Utility Commands

- **settings**
  - Allows the user to adjust various preferences, such as offline detection behaviour and cosmetics
  - Server admins can also change some settings on a server-wide level.
- **ping**
  - Returns the latency of the bot

### Dev-Only Commands
These commands are only accessible by users listed as admins/developers of the bot in the Discord Developer Portal, any other users will be rejected from use if an attempt is made.
- **update (sync:bool)**
  - Refreshes all extensions and syncs command tree(s) if specified
- **running**
  - Returns a list of the currently running games, stating the internal game ID, game type (e.g. Connect 4), players, guild name and channel name.
  - Also shows number of each game type being played currently.
- **force_remove [game ID]**
  - Used as a temporary fix for some games not being registered as finished, removes the game with the specified ID from the list of current games, allowing the players to start a new game
- **guild_toggle**
  - Toggles the premium status of the guild the command is run in
- **user_toggle [user id]**
  - Toggles the premium status of the selected user
- **add_status [string]**
  - Adds the specified string to the status loop
- **view_status**
  - Returns the list of statuses currently in the loop
- **remove_status [index]**
  - Removes the specified status at the index from the list of statuses

## Files
- **main.py**
  - Contains a minimal setup to get the bot up and running, importing the other files to provide most of its functionality. Run from this file.
- **game_commands.py, utility_commands.py & dev_commands.py**
  - Contain the commands that the bot uses, categorised by type.
  - The game commands call the related game function from its file, but the other categories have the full functionality of their commands within the same file.
- **languages.py**
  - This has not yet been changed from v1.2.2, so still contains all translated strings specifically from that version, but will be updated in the future.
- **games/**
  - Contains individualised files for each game function.
- **storage/**
  - Contains (or will contain when created by the program) files for long term storage, such as statistics and preferences.
  - **words.pkl**
    - The list of words used in Hangman. It is currently incomplete, but [this](https://github.com/dwyl/english-words) might come in handy if you want to help expand it.

### Notes for anyone intending to run the bot themselves:

These beta versions have commands available only in specified guilds - add your guild ID(s) to the dev_guilds and beta_test_guilds lists in `main.py`, `game_commands.py`, `utility_commands.py` & `dev_commands.py` to enable them there.

Also be sure to update token.txt (or `token` in `main.py`) with your own bot's token!
