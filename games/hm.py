import sys, os.path, discord, random
from discord.ext import commands
sys.path.append(os.path.dirname("__file__"))
sys.path.append('../tabletop')

from . import _handler as handler
from languages import *
import tt_assets as assets

class Hangman(handler.Game):
    """
    Hangman class, inherited from `handler.Game`

    Use .hangman() method to run the game, as below

    `await hm.Hangman(ctx, mode=mode).hangman()`
    """

    async def hangman(self):
        "Runs a Hangman game, including player setup"
        self.gameType = "Hangman"
        await self.setup()
        await self.msg.edit(content="*(insert hangman game here)*")