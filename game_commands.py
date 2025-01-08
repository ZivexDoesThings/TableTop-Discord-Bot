import discord, os, sys, importlib
from discord import app_commands
from discord.ext import commands
sys.path.append(os.path.dirname("__file__"))
from games import _handler, c4, ttt, mm, bs, hm
import importlib

beta_test_guilds = [
    discord.Object(id=0)
            ]

dev_guilds = [
    discord.Object(id=0)
]

def reload_all():
    global discord, app_commands, commands, _handler, c4, ttt, mm, bs, hm, importlib
    for module in [discord, app_commands, commands, _handler, c4, ttt, mm, bs, hm, importlib]:
        importlib.reload(module)

class GameCommands(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

    async def check_opponent_validity(self, ctx:discord.Interaction, opponent:discord.Member):
        if opponent:
            if opponent == ctx.user:
                await ctx.response.send_message(content="Sorry, you can't play against yourself!", ephemeral=True, delete_after=30)
                return False
            elif opponent.id == self.bot.user.id:
                await ctx.response.send_message(content="Sorry, I can't play with you! I just facilitate the games.", ephemeral=True, delete_after=30)
                return False
            elif opponent.bot:
                await ctx.response.send_message(content="Sorry, bots can't play!", ephemeral=True, delete_after=30)
                return False
        return True

    @app_commands.command()
    @app_commands.describe(opponent="The user you want to play against. Leave blank to send an open invitation.")
    async def connect4(self, ctx:discord.Interaction, opponent:discord.Member=None):
        """Start a game of Connect 4. 1v1. Get 4 in a row to win."""
        valid = await self.check_opponent_validity(ctx, opponent)
        if not valid: return
        await c4.Connect4(ctx, opponent).connect4(self.bot)

    @app_commands.command()
    async def megaconnect4(self, ctx:discord.Interaction):
        """Start a game of Mega Connect 4. More players, larger board. Get 4 in a row to win."""
        await c4.Connect4(ctx).mc4(self.bot)

    @app_commands.command()
    @app_commands.describe(opponent="The user you want to play against. Leave blank to send an open invitation.")
    async def tictactoe(self, ctx:discord.Interaction, opponent:discord.Member=None):
        """Start a game of Tic Tac Toe. 1v1. Get 3 in a row to win."""
        valid = await self.check_opponent_validity(ctx, opponent)
        if not valid: return
        await ttt.TicTacToe(ctx, opponent).tictactoe(self.bot)

    @app_commands.command()
    @app_commands.describe(
        opponent = "The user you want to play against. Leave blank to send an open invitation.",
        display_mode = "How the codes should be displayed, with colors or numbers")
    @app_commands.choices(
        display_mode = [
            app_commands.Choice(name="Colors", value=0),
            app_commands.Choice(name="Numbers", value=1)])
    async def mastermind(self, ctx:discord.Interaction, opponent:discord.Member=None, display_mode:int=False):
        """Start a game of Mastermind. Crack your opponents' code first to win."""
        valid = await self.check_opponent_validity(ctx, opponent)
        if not valid: return
        await mm.Mastermind(ctx, opponent, mode=bool(display_mode)).mastermind(self.bot)

    @app_commands.command()
    @app_commands.describe(opponent="The user you want to play against. Leave blank to send an open invitation.")
    async def battleship(self, ctx:discord.Interaction, opponent:discord.Member=None):
        """Start a game of Battleship. 1v1, find the locations of all your opponents' ships first to win."""
        await ctx.response.send_message(content="Sorry, this game isn't ready yet! Check back later", ephemeral=True, delete_after=30)
        return

        valid = await self.check_opponent_validity(ctx, opponent)
        if not valid: return
        await bs.Battleship(ctx, opponent).battleship(self.bot)

    @app_commands.command()
    @app_commands.describe(gamemode="The game mode you want to play. Leave blank to put it up to a vote.")
    @app_commands.choices(
        gamemode = [
            app_commands.Choice(name="Co-operative", value="co-op"),
            app_commands.Choice(name="Competitive", value="comp")])
    async def hangman(self, ctx:discord.Interaction, gamemode:str=None):
        """Start a game of Hangman. 2 or more players. Guess the word or phrase to win."""
        await ctx.response.send_message(content="Sorry, this game isn't ready yet! Check back later", ephemeral=True, delete_after=30)
        return

        await hm.Hangman(ctx, mode=gamemode).hangman(self.bot)



async def setup(bot:commands.Bot):
    reload_all()
    gc = GameCommands(bot)
    bot.tree.add_command(gc.connect4, guilds=beta_test_guilds)
    bot.tree.add_command(gc.megaconnect4, guilds=beta_test_guilds)
    bot.tree.add_command(gc.tictactoe, guilds=beta_test_guilds)
    # bot.tree.add_command(gc.mastermind, guilds=beta_test_guilds)
    # bot.tree.add_command(gc.battleship, guilds=beta_test_guilds)
    # bot.tree.add_command(gc.hangman, guilds=beta_test_guilds)
    print("Game Commands Loaded")