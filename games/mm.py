import sys, os.path, discord, random, asyncio, pickle
from discord.ext import commands
sys.path.append(os.path.dirname("__file__"))
sys.path.append('../tabletop')

from . import _handler as handler
from languages import *
import tt_assets as assets

class Mastermind(handler.Game):
    """
    Mastermind class, inherited from `handler.Game`

    Use .mastermind() method to run the game, as below

    `await mm.Mastermind(ctx, "Mastermind", opponent).mastermind()`
    """
    
    async def mastermind(self, bot:commands.Bot):
        "Runs a Mastermind game, including player setup"
        self.gameType = "Mastermind"
        await self.setup()
        await self.msg.edit(content="*(insert mastermind game here)*")