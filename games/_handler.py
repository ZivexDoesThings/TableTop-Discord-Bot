import sys, os.path, discord, random, asyncio, logging, pickle, itertools
from datetime import datetime
from typing import Optional
sys.path.append(os.path.dirname("__file__"))
sys.path.append('../tabletop')
from languages import *
from discord.ext import commands
from utility_commands import GuildSettings, UserSettings

nextID = 1
current_games = {}

langs = []
# premium = [
#     449433954529837056, # Zivex
#     146009145290653696, # JDtheQwerty
#     317778691390439424, # Kuba
#     629082225014734851, # Duckie
#     350363572045348875, # Enrico
#     387918981698289674, # L3mmy
#     657394368789086218, # Support Server
#     454129794284519434, # Zivex Zone
#     654316563679412274, # Kuba's Server
#     620479099948761089, # FluteFam
#     577287230125506580, # Cool Beans
#     467842457879576596, # Tutorial Army
#     620499156368097290, # Test Server
# ]

def flatten(x):
    return list(itertools.chain(*x))

class Kill(Exception):
    pass

logger = logging.getLogger()
logging.basicConfig(filename='errors.log', level=logging.ERROR, format='''
%(asctime)s - %(message)s''', datefmt='%d/%m/%Y %I:%M:%S %p')

def read_pickled_dict(directory:str) -> dict:
    file = open(directory, 'rb')
    merged = {}
    while True:
        try:
            load:dict = pickle.load(file)
        except EOFError:
            break
        merged = dict(itertools.chain(merged.items(), load.items()))
    file.close()
    return merged

def read_current_games() -> dict:
    return read_pickled_dict('storage/current_games.pkl')

def read_premium_list() -> dict:
    return read_pickled_dict('storage/premium.pkl')

def del_from_current_games(game):
    current_games = read_current_games()
    try:
        del current_games[game.id]
        file = open('storage/current_games.pkl', 'wb')
        pickle.dump(current_games, file, protocol=pickle.HIGHEST_PROTOCOL)
        file.close()
    except: pass

class Player:
    """A minimal version of `discord.Member` for passing around to other files.

    The optional `interaction` parameter takes a `discord.Interaction` object as a means to follow up the 'join game' confirmation with an extra hidden message for game setup (for mastermind, battleship, etc.)"""
    def __init__(self, user:discord.Member, interaction:discord.Interaction=None):
        if interaction: self.followup = interaction.followup
        self.setup_msg : int = None
        self.global_name = user.global_name
        self.nick = user.display_name
        self.username = user.name
        self.id = user.id
        self.mention = user.mention
        self.check_settings_update()
    
    def check_user_update(self, user:discord.Member):
        "Checks for nickname/username/global name changes and updates the relevant attributes to reflect said changes."
        if user.id == self.id:
            if self.nick != user.display_name: self.nick == user.display_name
            if self.global_name != user.global_name: self.global_name == user.global_name
            if self.name != user.name: self.name == user.name
        else: raise ValueError("User does not match stored player ID")
    
    def check_settings_update(self):
        "Checks for updates to the user's display name setting"
        try:
            self.settings : UserSettings = read_pickled_dict('storage/settings.pkl')[self.id]
            if self.settings.display_name.global_name: self.name = self.global_name
            elif self.settings.display_name.nick: self.name = self.nick
            elif self.settings.display_name.username: self.name = self.username
        except KeyError:
            self.settings = UserSettings()
            self.name = self.global_name


class PlayerStatistics:
    "Contains all game statistics for a specific user"
    class Connect4:
        def __init__(self):
            self.wins = 0
            self.losses = 0
            self.draws = 0
            self.played = 0

            self.min_turns = 0
            self.max_turns = 0
            self.total_turns = 0
    class MegaConnect4:
        def __init__(self):
            self.wins = 0
            self.losses = 0
            self.draws = 0
            self.played = 0

            self.min_turns = 0
            self.max_turns = 0
            self.total_turns = 0
    class TicTacToe:
        def __init__(self):
            self.wins = 0
            self.losses = 0
            self.draws = 0
            self.played = 0
    class Mastermind:
        def __init__(self):
            self.wins = 0
            self.losses = 0
            self.draws = 0
            self.played = 0

            self.min_turns = 0
            self.max_turns = 0
            self.total_turns = 0
    class Battleship:
        def __init__(self):
            self.wins = 0
            self.losses = 0
            self.draws = 0
            self.played = 0

            self.min_turns = 0
            self.max_turns = 0
            self.total_turns = 0
    class Hangman:
        def __init__(self):
            self.wins = 0
            self.losses = 0
            self.draws = 0
            self.played = 0

            self.min_turns = 0
            self.max_turns = 0
            self.total_turns = 0

    def __init__(self):
        self.wins = 0
        self.losses = 0
        self.draws = 0
        self.played = 0

        self.c4 = self.Connect4()
        self.mc4 = self.MegaConnect4()
        self.ttt = self.TicTacToe()
        self.mm = self.Mastermind()
        self.bs = self.Battleship()
        self.hm = self.Hangman()

class Game:
    """
    Contains all info about any individual game\n
    ### Parameters:
    `ctx`: The original interaction (typically a slash command) that started the game\n
    `opponent` (Optional): The opponent that was mentioned in the command (if applicable)\n
    `mode` (Optional): The gamemode or specified display option (such as Hangman's 'co-op' or 'comp')

    ### Attributes:
    `id`: Numerical ID of the game object\n
    `gameType`: The name of the game (in proper capitalised words) e.g. "Mega Connect 4"\n
    `players`: A list of all the players currently in the game, as `Player` objects\n
    `lang`: A `Language` object with all the phrases set to the appropriate locale

    ### Methods:
    `setup()`: Initial player-gathering. Waits for response from `opponent` if there is one, otherwise gives an open invitation.
    `rematch_setup()`: 
    """

    def __init__(self, ctx:discord.Interaction, opponent:discord.Member=None, mode:bool=None):
        self.ctx = ctx
        self.gameType = None
        self.opponent = opponent
        if mode != None: self.mode = mode
        if "COMMUNITY" in ctx.guild.features: self.lang = Language(str(ctx.guild_locale))
        elif self.ctx.guild.id in langs: self.lang = Language(langs[ctx.guild.id])
        else: self.lang = Language('en-US')
        self.players = [Player(self.ctx.user, self.ctx)]
        self.rematch = False
        self.start_time = f"{datetime.now().hour}:{datetime.now().minute}, {datetime.now().day}/{datetime.now().month}/{datetime.now().year}"
    
    async def check_kill(self):
        current_games = read_current_games()
        if self.id not in current_games:
            self.kill()

    async def kill(self):
        pass # Used as a placeholder for the other games to fill in with their own thang
    
    async def setup(self):
        """Performs initial setup of the game. Waits for response from `opponent`, if specified, otherwise gives an open invitation."""
        # Confirms min/max player counts based on whether the game is a 'premium' game
        premium = read_premium_list()
        if self.ctx.guild_id in premium['servers']: player_counts = {"Connect 4":[2,2], "Tic Tac Toe":[2,2], "Battleship":[2,2], "Mastermind":[2,8], "Mega Connect 4":[3,6], "Hangman":[2,16]}
        else: player_counts = {"Connect 4":[2,2], "Tic Tac Toe":[2,2], "Battleship":[2,2], "Mastermind":[2,2], "Mega Connect 4":[4,4], "Hangman":[2,4]}
        min_player_count = player_counts[self.gameType][0]
        max_player_count = player_counts[self.gameType][1]

        ctx_user_name = self.players[0].name

        class Buttons(discord.ui.View):
            def __init__(self, ctx:discord.Interaction, parent:Game):
                super().__init__()
                self.confirmCancel = False
                self.ctx = ctx
                self.parent = parent

            @discord.ui.button(emoji="✅", style=discord.ButtonStyle.green)
            async def yes(self, interaction:discord.Interaction, button):
                if self.parent.opponent == None:
            
                    if interaction.user == self.ctx.user:
                        if min_player_count == max_player_count:
                            await interaction.response.send_message(
                                content="You're already in this game, you created it!\nPress the ❌ button if you want to cancel this game.",
                                ephemeral=True, delete_after=20)
                        elif len(self.parent.players) >= min_player_count:
                            if self.parent.gameType in ["Connect 4", "Mega Connect 4", "Tic Tac Toe"]: await interaction.response.send_message(content=", ".join(p.mention for p in self.parent.players) + "... The game is starting!", delete_after=15)
                            else: await interaction.response.defer()
                            self.stop()
                        else: # Can also be written as elif len(self.parent.players) < min_player_count:
                            if (min_player_count - len(self.parent.players)) == 1:
                                await interaction.response.send_message(
                                    content = "There aren't enough players yet! You need at least 1 more person to join before the game can start.",
                                    ephemeral=True, delete_after=30
                                )
                            else:
                                await interaction.response.send_message(
                                    content = "There aren't enough players yet! You need at least " + str(min_player_count - len(self.parent.players)) + " more people to join before the game can start.",
                                    ephemeral=True, delete_after=30
                                )
                    
                    elif interaction.user.id in [p.id for p in self.parent.players]:
                        await interaction.response.send_message(
                            content="You're already in this game!\nPress the ❌ button if you want to cancel this game.",
                            ephemeral=True, delete_after=20)
                        
                    elif interaction.user != self.ctx.user:
                        self.parent.players.append(Player(interaction.user, interaction))
                        if len(self.parent.players) < max_player_count:
                            await interaction.response.send_message(content="You've joined the game!\nPress the ❌ button if you want to leave before it starts.", ephemeral=True, delete_after=30)
                            if len(self.parent.players) < min_player_count:
                                await self.parent.ctx.edit_original_response(content=(f"## {ctx_user_name} is giving an open invitation to a game of {self.parent.gameType}!\n**Press ✅ to join!**\n### Current players ({len(self.parent.players)}/{max_player_count}):\n" + '\n'.join(p.name for p in self.parent.players) + f"\n\n*{ctx_user_name}, you can cancel this by pressing ❌*"))
                            else:
                                await self.parent.ctx.edit_original_response(content=(f"## {ctx_user_name} is giving an open invitation to a game of {self.parent.gameType}!\n**Press ✅ to join!**\n### Current players ({len(self.parent.players)}/{max_player_count}):\n" + '\n'.join(p.name for p in self.parent.players) + f"\n\n*{ctx_user_name}, you can start the game now by pressing ✅, or cancel by pressing ❌*"))
                        else:
                            if self.parent.gameType in ["Connect 4", "Mega Connect 4", "Tic Tac Toe"]: await interaction.response.send_message(content=", ".join(p.mention for p in self.parent.players) + "... The game is starting!", delete_after=15)
                            else: await interaction.response.defer()
                            self.stop()
                            

                else: # if opponent is specified
                    if interaction.user == self.parent.opponent:
                        self.parent.players.append(Player(interaction.user, interaction))
                        if self.parent.gameType in ["Connect 4", "Mega Connect 4", "Tic Tac Toe"]: await interaction.response.send_message(content=", ".join(p.mention for p in self.parent.players) + "... The game is starting!", delete_after=15)
                        else: await interaction.response.defer()
                        self.stop()
                    elif interaction.user == self.ctx.user:
                        await interaction.response.send_message(content="You're already in this game, you created it!\nPress the ❌ button if you want to cancel this game.", ephemeral=True, delete_after=20)
                    else:
                        await interaction.response.send_message(content="Sorry, you haven't been invited to this game! Run the command if you want to play.", ephemeral=True, delete_after=30)
            
            @discord.ui.button(emoji="✖️", style=discord.ButtonStyle.red)
            async def no(self, interaction:discord.Interaction, button):
                if interaction.user == self.ctx.user:
                    if not self.confirmCancel:
                            await interaction.response.send_message(content="You're about to cancel the game. If you're sure, press the button again.", ephemeral=True, delete_after=20)
                            self.confirmCancel = True
                    else:
                        await interaction.response.edit_message(content=None, embed=discord.Embed(title="This game has been cancelled.", colour=0x595554), view=None, delete_after=60)
                        self.stop()
                        self.parent.cancel = True
                
                elif self.parent.opponent == None:
                    if interaction.user not in self.parent.players:
                        await interaction.response.send_message(content="You can't leave a game you haven't joined!", ephemeral=True, delete_after=20)
                    else:
                        await interaction.response.send_message(content="You've left the game. Press ✅ if you want to join again.", ephemeral=True, delete_after=20)
                        for p in self.parent.players:
                            if p.id == interaction.user.id:
                                self.parent.players.remove(p)
                                break
                        await self.parent.ctx.edit_original_response(content=(f"## {ctx_user_name} is giving an open invitation to a game of {self.parent.gameType}!\n**Press ✅ to join!**\n### Current players ({len(self.parent.players)}/{max_player_count}):\n" + '\n'.join(p.name for p in self.parent.players) + f"\n\n*{ctx_user_name}, you can cancel this by pressing ❌*"))

                elif interaction.user == self.parent.opponent:
                        await interaction.response.edit_message(content=None, embed=discord.Embed(title="This game invitation was declined.", colour=0x595554), view=None, delete_after=60)
                        self.stop()
                        self.parent.cancel = True
                else:
                    await interaction.response.send_message(content="Sorry, you can't cancel a game you're not involved in!", ephemeral=True, delete_after=30)

            async def on_timeout(self):
                self.parent.cancel = True
                await self.ctx.edit_original_response(content=None, embed=discord.Embed(title="This game invitation timed out.", colour=0x595554), view=None)


        current_games = read_current_games()
        print(current_games)
        for game in current_games:
            for player in current_games[game].players:
                if player.id == self.ctx.user.id:
                    print("Oi, that's not allowed")
        
        buttons = Buttons(self.ctx, self)
        self.cancel = False

        try: settings = read_pickled_dict('storage/settings.pkl')
        except: settings = {}

        # Get guild's previously saved settings. If none exists, then creates a new GuildSettings object for it
        if self.ctx.guild.id in settings: guild_settings:GuildSettings = settings[self.ctx.guild.id]
        else: guild_settings = GuildSettings(self.ctx.guild)

        # Decide what message content should be in the setup message, based on game type, thread type, and whether an opponent was passed through the command
        if self.opponent:
            if guild_settings.threads.private: msg_content = f"## Hey {self.opponent.mention}!\n## {self.ctx.user.mention} invites you to a game of {self.gameType}!\n**Press ✅ to accept, or ❌ to decline.**"
            else: msg_content = f"## Hey {self.opponent.mention}!\n## {ctx_user_name} invites you to a game of {self.gameType}!\n**Press ✅ to accept, or ❌ to decline.**"
        elif max_player_count == 2:
            msg_content = f"## {ctx_user_name} is giving an open invitation to a game of {self.gameType}!\n**Press ✅ to play!**\n\n*{ctx_user_name}, you can cancel this by pressing ❌*"
        elif max_player_count == min_player_count: msg_content = f"## {ctx_user_name} is giving an open invitation to a game of {self.gameType}!\n**Press ✅ to join!**\n\n*{ctx_user_name}, you can cancel this by pressing ❌*"
        else: msg_content = f"## {ctx_user_name} is giving an open invitation to a game of {self.gameType}!\n**Press ✅ to join!**\n\n*{ctx_user_name}, you can start the game with at least {min_player_count} players by pressing ✅, or cancel this by pressing ❌*"

        if guild_settings.threads.disabled or (guild_settings.threads.private and self.opponent == None):
            await self.ctx.response.send_message(content=msg_content, view=buttons)
            self.msg = await self.ctx.original_response()
            self.timeout = await buttons.wait()
            await asyncio.sleep(0.2)
            if self.timeout:
                await self.msg.edit(content=None, embed=discord.Embed(title="This game invitation timed out.", colour=0x595554), view=None, delete_after=300)
                return
            elif self.cancel: return

        elif guild_settings.threads.public or (guild_settings.threads.private and self.opponent != None):
            if guild_settings.threads.public: type = discord.ChannelType.public_thread
            elif guild_settings.threads.private: type = discord.ChannelType.private_thread
            if self.ctx.channel.type in [discord.ChannelType.public_thread, discord.ChannelType.private_thread]:
                channel = self.ctx.channel.parent
            elif self.ctx.channel.type == discord.ChannelType.text:
                channel = self.ctx.channel
            else:
                await self.ctx.response.send_message(content="Sorry, games can't be played here!\nGo to a text channel to start a game.", ephemeral=True)
                return
            if self.opponent == None: opp_str = "???"
            else: opp_str = Player(self.opponent).name
            thread = await channel.create_thread(name=f"{self.gameType} - {ctx_user_name} vs {opp_str}", type=type, invitable=True, auto_archive_duration=60)
            self.msg = await thread.send(content=msg_content, view=buttons)

            await self.ctx.response.send_message(content=f"Game thread created: {thread.jump_url}", ephemeral=True, delete_after=30)

        self.timeout = await buttons.wait()
        await asyncio.sleep(1) # Gives a moment for on_timeout() to fire before proceeding
        if self.cancel:
            if self.msg.channel.type in [discord.ChannelType.public_thread, discord.ChannelType.private_thread]:
                await asyncio.sleep(30)
                await thread.delete()
            return

        random.shuffle(self.players)
        del buttons

        self.channel = self.msg.channel.id
        self.message = self.msg.id

        global nextID
        self.id = nextID
        nextID += 1
        self.killing = False

        if guild_settings.threads.public or guild_settings.threads.private:
            await thread.edit(name=f"{self.gameType} [{str(self.id).zfill(3)}] - {' vs. '.join(p.name for p in self.players)}")
            self.thread_id = thread.id

        del self.msg
        del self.timeout
        del self.ctx
        del self.lang
        del self.opponent

        if self.gameType not in ["Mastermind", "Battleship", "Hangman"]:
            for player in self.players:
                del player.followup
            file = open('storage/current_games.pkl', 'ab')
            pickle.dump({self.id:self}, file, pickle.HIGHEST_PROTOCOL)
            file.close()
        print(vars(self))
    
    async def rematch_setup(self):
        class Rematch(discord.ui.View):
            def __init__(self, parent:Game):
                self.parent = parent
                super().__init__(timeout=20)

            @discord.ui.button(label="Rematch!", emoji="💪", style=discord.ButtonStyle.blurple)
            async def rematch_button(self, interaction:discord.Interaction, button):
                class ConfirmRematch(discord.ui.View):
                    def __init__(self, parent:Rematch):
                        self.parent = parent
                        self.respondents = {}
                        super().__init__(timeout=20)
                    
                    @discord.ui.button(emoji="✅")
                    async def accept(self, interaction:discord.Interaction, button):
                        if interaction.user.id == self.parent.init_user.id:
                            if len(self.parent.players_except_init) == 1: s = ""
                            else: s = "s"
                            await interaction.response.send_message(content=f"You requested this rematch! Please wait for your opponent{s} to respond.", ephemeral=True, delete_after=20)
                            return
                        elif interaction.user.id not in [p.id for p in self.parent.parent.players]:
                            await interaction.response.send_message(content=f"This is a rematch, you can't join at this stage!\nYou can start a new game by running `/{self.parent.parent.gameType.lower().strip()}`", ephemeral=True, delete_after=20)
                            return
                        elif interaction.user.id in self.respondents:
                            if len(self.parent.players_except_init) - len(self.respondents) <= 1: s = ""
                            else: s = "s"
                            if self.respondents[interaction.user.id]:
                                await interaction.response.send_message(content=f"You've already accepted this rematch request! Please wait for the remaining player{s} to respond.", ephemeral=True, delete_after=20)
                            return
                        
                        self.respondents[interaction.user.id] = True
                        if len(self.parent.players_except_init) - len(self.respondents) > 0:
                            remaining_players = self.parent.players_except_init
                            remaining_players.remove(p for p in self.respondents)
                            if len(self.respondents) == 1: respondents_str = self.respondents[0].name + " is in!"
                            else: respondents_str = ', '.join(p.name for p in self.respondents[:-1]) + " and " + self.respondents[-1].name + " are in!"
                            await interaction.response.edit_message(content=f"## {self.parent.init_user.name} wants a rematch!\n### {', '.join(p.mention for p in remaining_players)}, do you accept?\n{respondents_str}", ephemeral=True)
                        else:
                            self.parent.parent.rematch = True
                            await interaction.message.delete()
                            self.parent.parent.message = await interaction.response.send_message(f"Rematch confirmed. Let's begin!\n{' '.join(p.mention for p in self.parent.parent.players)}")
                            self.stop()

                    @discord.ui.button(emoji="❌")
                    async def decline(self, interaction:discord.Interaction, button):
                        if interaction.user.id == self.parent.init_user.id:
                            if len(self.parent.players_except_init) == 1: s = ""
                            else: s = "s"
                            await interaction.response.send_message(content=f"You requested this rematch! Please wait for your opponent{s} to respond.", ephemeral=True, delete_after=20)
                            return
                        elif interaction.user.id not in [p.id for p in self.parent.parent.players]:
                            await interaction.response.send_message(content=f"You can't decline a request that's not meant for you!", ephemeral=True, delete_after=20)
                            return
                        elif interaction.user.id in [r[0] for r in self.respondents]:
                            if len(self.parent.players_except_init) - len(self.respondents) <= 1: s = ""
                            else: s = "s"
                            await interaction.response.send_message(content=f"You've already responded to this rematch request! Please wait for the remaining player{s} to respond.", ephemeral=True, delete_after=20)
                            return
                        
                        self.respondents.append((interaction.user.id, False))
                        if len(self.parent.players_except_init) - len(self.respondents) > 0:
                            remaining_players = self.parent.players_except_init
                            remaining_players.remove(p for p in self.respondents)
                            if len(self.respondents) == 1: respondents_str = self.respondents[0].name + " is in!"
                            else: respondents_str = ', '.join(p.name for p in self.respondents[:-1]) + " and " + self.respondents[-1].name + " are in!"
                            await interaction.response.edit_message(content=f"## {self.parent.init_user.name} wants a rematch!\n### {', '.join(p.mention for p in remaining_players)}, do you accept?\n{respondents_str}", ephemeral=True)
                        else:
                            self.parent.parent.rematch = False
                            await interaction.message.edit(content="The rematch request was declined 😔 Maybe another time?")
                            self.stop()

                    
                    async def on_timeout(self):
                        self.parent.parent.rematch = False
                        await self.parent.req_msg.delete()
                        await self.parent.parent.kill()
                        

                if interaction.user.id not in [p.id for p in self.parent.players]: # Stop non-players from requesting a rematch
                    await interaction.response.send_message(content=f"You can't start a rematch for a game you weren't in!\nStart a new game by running `/{self.parent.gameType.lower().strip()}`", ephemeral=True, delete_after=20)
                    return
                for p in self.parent.players: # Identify player object of the user that requested rematch
                    if p.id == interaction.user.id: self.init_user = p
                self.players_except_init = self.parent.players
                self.players_except_init.remove(self.init_user)
                await self.parent.msg.edit(view=None)
                confirmation = ConfirmRematch(self)
                await interaction.response.send_message(content=f"## {self.init_user.name} wants a rematch!\n### {', '.join(p.mention for p in self.players_except_init)}, do you accept?", view=confirmation)
                self.req_msg = await interaction.original_response()
                while not confirmation.is_finished():
                    await asyncio.sleep(1)
                self.stop()

            async def on_timeout(self):
                self.parent.rematch = False
                await self.parent.msg.edit(view=None)
        
        rematch_button = Rematch(self)
        await self.msg.edit(view=rematch_button)
        while not rematch_button.is_finished():
            await asyncio.sleep(1)
        return self.rematch