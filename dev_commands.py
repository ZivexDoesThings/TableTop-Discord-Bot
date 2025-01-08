import discord, pickle, os, sys, importlib
from discord import app_commands
from discord.ext import commands
sys.path.append(os.path.dirname("__file__"))
from games import _handler

def reload_all():
    global discord, pickle, app_commands, commands, _handler
    for module in [discord, pickle, app_commands, commands, _handler]:
        importlib.reload(module)

dev_guilds = [
    discord.Object(id=0)
    ]

class DevCommands(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

        self.user_toggle_ctx = app_commands.ContextMenu( # Context menu commands can't be defined inside a class using the decorator, so here's the workaround
            name="Toggle Premium Status",
            callback=self.user_toggle_context_menu
        )
        self.bot.tree.add_command(self.user_toggle_ctx, guilds=dev_guilds)
    
    async def check_allowed(self, ctx:discord.Interaction):
        if ctx.user.id not in self.bot.owner_ids:
            await ctx.response.send_message(content="Oops! You're not supposed to see this command... ( ⚆ _ ⚆ )\n*I was never here...*", ephemeral=True, delete_after=10)

            embed = discord.Embed(title="🚨 Illegal Dev Command Usage 🚨", description=f"**Command:** `{ctx.command.name}`\n**User:** {ctx.user.global_name} (`{ctx.user.name}`)\n{ctx.channel.jump_url}\n{ctx.guild.name} > #{ctx.channel.name}")
            
            for u in self.bot.owner_ids:
                user = self.bot.get_user(u)
                await user.send(embed=embed)
            return False
        else: return True

    @app_commands.command()
    @app_commands.checks.has_permissions(administrator=True)
    async def guild_toggle(self, ctx:discord.Interaction, guild_id:str=None):
        "DEV ONLY: Toggles the premium status of the selected guild. If no guild is specified, uses the one the command was run in"
        if not await self.check_allowed(ctx): return
        if guild_id == None: guild_id = ctx.guild.id
        else: guild_id = int(guild_id)
        server = self.bot.get_guild(guild_id)
        if server == None:
            await ctx.response.send_message(content=f"Server not found.", ephemeral=True)
            return
        premium = _handler.read_premium_list()
        if guild_id in premium['servers']:
            premium['servers'].remove(guild_id)
            await ctx.response.send_message(content=f"Premium features disabled for {server.name}", ephemeral=True)
        else:
            premium['servers'].append(guild_id)
            await ctx.response.send_message(content=f"Premium features enabled for {server.name}", ephemeral=True)

        file = open('storage/premium.pkl', 'wb')
        pickle.dump(premium, file, protocol=pickle.HIGHEST_PROTOCOL)
        file.close()

    @app_commands.command()
    @app_commands.checks.has_permissions(administrator=True)
    async def user_toggle(self, ctx:discord.Interaction, user_id:str):
        "DEV ONLY: Toggles the premium status of the selected user"
        if not await self.check_allowed(ctx): return
        user_id = int(user_id)
        user = self.bot.get_user(user_id)
        if user == None:
            await ctx.response.send_message(content=f"User not found.", ephemeral=True)
            return
        
        premium = _handler.read_premium_list()
        if user.id in premium['permanent_users']:
            premium['permanent_users'].remove(user.id)
            await ctx.response.send_message(content=f"Premium features disabled for {user.name}", ephemeral=True)
        else:
            premium['permanent_users'].append(user.id)
            await ctx.response.send_message(content=f"Premium features enabled for {user.name}", ephemeral=True)

        file = open('storage/premium.pkl', 'wb')
        pickle.dump(premium, file, protocol=pickle.HIGHEST_PROTOCOL)
        file.close()

    @app_commands.checks.has_permissions(administrator=True)
    async def user_toggle_context_menu(self, ctx:discord.Interaction, user:discord.Member):
        "DEV ONLY: Toggles the premium status of the selected user"
        if not await self.check_allowed(ctx): return
        premium = _handler.read_premium_list()
        if user.id in premium['permanent_users']:
            premium['permanent_users'].remove(user.id)
            await ctx.response.send_message(content=f"Premium features disabled for {user.global_name}", ephemeral=True)
        else:
            premium['permanent_users'].append(user.id)
            await ctx.response.send_message(content=f"Premium features enabled for {user.global_name}", ephemeral=True)

        file = open('storage/premium.pkl', 'wb')
        pickle.dump(premium, file, protocol=pickle.HIGHEST_PROTOCOL)
        file.close()

    @app_commands.command()
    @app_commands.checks.has_permissions(administrator=True)
    async def running(self, ctx:discord.Interaction):
        "DEV ONLY: Displays all of the games that are currently running"
        if not await self.check_allowed(ctx): return
        current_games = _handler.read_current_games()
        numbers = {"Total":0, "Connect 4":0, "Mega Connect 4":0, "Tic Tac Toe":0, "Mastermind":0, "Battleship":0, "Hangman":0}
        overview = discord.Embed(title="Current Games", description="Overview")
        details = discord.Embed(title="Current Games", description="Individual Details")
        for game in current_games:
            g : _handler.Game = current_games[game]
            numbers[g.gameType] += 1
            numbers["Total"] += 1
            try:
                msg = await self.bot.get_channel(g.channel).fetch_message(g.message)
                msg = msg.jump_url
            except AttributeError: msg = "`Channel not found - link unavailable`"
            except discord.errors.NotFound: msg = "`Message not found - link unavailable`"
            details.add_field(name=g.gameType, value=(f"**ID:** {game}\n**Started at:** {g.start_time}\n**Players:** {', '.join(self.bot.get_user(p.id).name for p in g.players)}\n**Server:** {self.bot.get_channel(g.channel).guild.name}\n**Channel:** {self.bot.get_channel(g.channel).name}\n{msg}"))
            #details.add_field(name=g.gameType, value=(f"**ID:** {game}\n**Started at:** {g.start_time}\n**Players:** {', '.join(self.bot.get_user(p.id).name for p in g.players)}"))

        if numbers["Total"] > 0:
            for key in numbers:
                overview.add_field(name=key, value=numbers[key])
            await ctx.response.send_message(content=None, embeds=[overview, details], ephemeral=True)
        else:
            await ctx.response.send_message(content=None, embed=discord.Embed(title="No Games Currently Running"), ephemeral=True)

    @app_commands.command()
    @app_commands.checks.has_permissions(administrator=True)
    async def force_remove(self, ctx:discord.Interaction, game_id:int):
        "DEV ONLY: Removes the specified game from the list of ongoing games"
        if not await self.check_allowed(ctx): return
        current_games = _handler.read_current_games()
        if game_id not in current_games:
            await ctx.response.send_message(content=None, embed=discord.Embed(title="Invalid Game ID", colour=0xbf0502), ephemeral=True)
            return
        game : _handler.Game = current_games[game_id]
        del current_games[game_id]
        file = open('storage/current_games.pkl', 'wb')
        pickle.dump(current_games, file, protocol=pickle.HIGHEST_PROTOCOL)
        file.close()
        try:
            msg = await self.bot.get_channel(game.channel).fetch_message(game.message)
            msg = msg.jump_url
        except discord.errors.NotFound: msg = "`Message not found - link unavailable`"
        try:
            channel = self.bot.get_channel(game.channel).name
        except discord.errors.NotFound: msg = "`Channel no longer exists`"
        try:
            guild = self.bot.get_channel(game.channel).guild.name
        except discord.errors.NotFound: msg = "`Guild unknown`"
        embed = discord.Embed(title=f"Successfully removed {game.gameType} game with ID {game_id} from list of ongoing games", description=f"{msg}\nServer: {guild}\nChannel: {channel}\n**Players:** {', '.join(self.bot.get_user(p.id).username for p in game.players)}", colour=0x02bf0f)
        await ctx.response.send_message(content=None, embed=embed, ephemeral=True)


async def setup(bot:commands.Bot):
    reload_all()
    dev = DevCommands(bot)
    bot.tree.add_command(dev.guild_toggle, guilds=dev_guilds)
    bot.tree.add_command(dev.user_toggle, guilds=dev_guilds)
    bot.tree.add_command(dev.running, guilds=dev_guilds)
    bot.tree.add_command(dev.force_remove, guilds=dev_guilds)
    print("Dev Commands Loaded")
