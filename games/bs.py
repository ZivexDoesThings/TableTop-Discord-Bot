import sys, os.path, discord, random
from discord.ext import commands
sys.path.append(os.path.dirname("__file__"))
sys.path.append('../tabletop')

from . import _handler as handler
import tt_assets as assets
from languages import *

class Battleship(handler.Game):
    """
    Battleship class, inherited from `handler.Game`

    Use .battleship() method to run the game, as below

    `await bs.Battleship(ctx, "Battleship", opponent).battleship()`
    """

    async def battleship(self):
        "Runs a Battleship game, including player setup"
        self.gameType = "Battleship"
        await self.setup()
        await self.msg.edit(content="*(insert battleship game here)*")