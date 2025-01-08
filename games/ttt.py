import sys, os.path, discord, random
from discord.ext import commands
sys.path.append(os.path.dirname("__file__"))
sys.path.append('../tabletop')

from . import _handler as handler
from languages import *
import tt_assets as assets

class TicTacToe(handler.Game):
    """
    Tic Tac Toe class, inherited from `handler.Game`
    
    Use .tictactoe() method to run the game, as below
    
    `await ttt.TicTacToe(ctx, "Tic Tac Toe", opponent).tictactoe()`
    """

    async def tictactoe(self, bot:commands.Bot):
        """Runs a Tic Tac Toe game, including player setup"""
        self.gameType = "Tic Tac Toe"
        await self.setup()
        if self.cancel: return
        
        @bot.listen()
        async def on_member_update(before:discord.Member, after:discord.Member):
            #print("Member update - " + after.global_name)
            for p in self.players:
                if p.id == after.id: p.check_user_update()
        @bot.listen()
        async def on_user_update(before:discord.User, after:discord.User):
            #print("User update - " + after.global_name)
            for p in self.players:
                if p.id == after.id: p.check_user_update()

        channel = await bot.fetch_channel(self.channel)
        self.msg = await channel.fetch_message(self.message)
        del self.message

        symbols = [["❌", 0xff9900],["⭕", 0xff9900]]
        self.buttonList = [[],[],[]]
        self.disabledButtons = [False for i in range(9)]

        self.turn = 0
        self.win = None
        self.embed = discord.Embed(title=f"{symbols[self.turn % 2][0]} It's {self.players[self.turn % 2].name}'s turn! {symbols[self.turn % 2][0]}", description="\n".join(symbols[self.players.index(p)][0] + " - " + p.name for p in self.players), colour=symbols[self.turn % 2][1])
        
        def check_win(button:discord.ui.Button, buttonList, players:list[handler.Player], turn):
            button.emoji = symbols[button.parent.turn % 2][0]
            button.disabled = True

            # Win Detection
            win = None
            # Horizontal
            if str(buttonList[button.row][0].emoji) == str(buttonList[button.row][1].emoji) == str(buttonList[button.row][2].emoji) != assets.blank:
                win = players[turn % 2]
                for b in buttonList[button.row]:
                    b.style = discord.ButtonStyle.green
            # Vertical
            if str(buttonList[0][int(button.custom_id)%3].emoji) == str(buttonList[1][int(button.custom_id)%3].emoji) == str(buttonList[2][int(button.custom_id)%3].emoji) != assets.blank:
                win = players[turn % 2]
                for b in [buttonList[0][int(button.custom_id)%3], buttonList[1][int(button.custom_id)%3], buttonList[2][int(button.custom_id)%3]]:
                    b.style = discord.ButtonStyle.green
            # Diagonal
            if str(buttonList[0][0].emoji) == str(buttonList[1][1].emoji) == str(buttonList[2][2].emoji) != assets.blank:
                win = players[turn % 2]
                for b in [buttonList[0][0], buttonList[1][1], buttonList[2][2]]:
                    b.style = discord.ButtonStyle.green
            if str(buttonList[2][0].emoji) == str(buttonList[1][1].emoji) == str(buttonList[0][2].emoji) != assets.blank:
                win = players[turn % 2]
                for b in [buttonList[2][0], buttonList[1][1], buttonList[0][2]]:
                    b.style = discord.ButtonStyle.green
            
            if win == None:
                draw = True
                for row in buttonList:
                    for b in row:
                        if not b.disabled: draw = False
                if draw:
                    win = "Draw"
            
            return win, button, buttonList

        class Button(discord.ui.Button):
            def __init__(self, id:int, emoji:str=assets.blank, row:int=0, viewParent=None, gameParent:handler.Game=None):
                self.viewParent = viewParent
                self.parent:handler.Game = gameParent
                self.row = row
                id = str(id)
                super().__init__(emoji=emoji, custom_id=id, style=discord.ButtonStyle.grey, row=row, disabled=self.parent.disabledButtons[int(id)])
            
            async def callback(self, interaction:discord.Interaction):
                if interaction.user.id not in [p.id for p in self.parent.players]:
                    await interaction.response.send_message(content="**You're not in this game!**", ephemeral=True, delete_after=20)
                    return
                elif interaction.user.id != self.parent.players[self.parent.turn % len(self.parent.players)].id:
                    await interaction.response.send_message(content="**Hold on, it's not your turn yet!**", ephemeral=True, delete_after=20)
                    return
                self.parent.win, self, self.parent.buttonList = check_win(self, self.parent.buttonList, self.parent.players, self.parent.turn)
                self.parent.disabledButtons[int(self.custom_id)] = True
                if self.parent.win == None:
                    self.parent.turn += 1
                    self.parent.embed = discord.Embed(title=f"{symbols[self.parent.turn % 2][0]} It's {self.parent.players[self.parent.turn % 2].name}'s turn! {symbols[self.parent.turn % 2][0]}", description="\n".join(symbols[self.parent.players.index(p)][0] + " - " + p.name for p in self.parent.players), colour=symbols[self.parent.turn % 2][1])
                    await interaction.response.edit_message(embed=self.parent.embed, view=self.viewParent)
                else:
                    self.viewParent.stop()
                    await interaction.response.defer()
                    if type(self.parent.win) == str:
                        self.parent.embed = discord.Embed(title="It's a draw!", description="\n".join(symbols[self.parent.players.index(p)][0] + " - " + p.name for p in self.parent.players), colour=assets.orange)
                    else:
                        self.embed = discord.Embed(title=f"{self.parent.win.name} won!", description="\n".join(symbols[self.parent.players.index(p)][0] + " - " + p.name for p in self.parent.players), colour=symbols[self.parent.turn % 2][1])
                    await self.parent.msg.edit(embed=self.parent.embed, view=self.viewParent)
                    self.parent.buttons.stop()
                    handler.del_from_current_games(self.parent)

        class View(discord.ui.View):
            def __init__(self, gameParent:TicTacToe=None):
                super().__init__(timeout=30)
                self.parent = gameParent

                if self.parent.buttonList == [[],[],[]]:
                    for row in range(3):
                        for col in range(3):
                            self.add_item(Button(id=(col+row*3), row=row, viewParent=self, gameParent=self.parent))
                
                    for i in range(3):
                        self.parent.buttonList[i] = [self.children[i*3], self.children[1+(i*3)], self.children[2+(i*3)]]
                
                else:
                    for row in self.parent.buttonList:
                        for i in row:
                            self.add_item(i)
            
            async def on_timeout(self):
                if self.parent.kill:
                    self.stop()
                    return
                print("timed out, picking random button")
                button = self.parent.buttonList[random.randint(0,2)][random.randint(0,2)]
                while button.disabled: button = self.parent.buttonList[random.randint(0,2)][random.randint(0,2)]
                self.parent.win, button, self.parent.buttonList = check_win(button, self.parent.buttonList, self.parent.players, self.parent.turn)
                self.parent.disabledButtons[int(button.custom_id)] = True
                print("random button selected")

                if not self.parent.win:
                    print("no win detected - moving on to next turn")
                    self.parent.turn += 1
                    self.parent.embed = discord.Embed(title=f"{symbols[self.parent.turn % 2][0]} It's {self.parent.players[self.parent.turn % 2].name}'s turn! {symbols[self.parent.turn % 2][0]}", description="\n".join(symbols[self.parent.players.index(p)][0] + " - " + p.name for p in self.parent.players), colour=symbols[self.parent.turn % 2][1])
                    self.parent.embed.set_footer(text=f"{self.parent.players[(self.parent.turn-1)%2].name} took too long, a random slot was selected")
                    await self.parent.msg.edit(embed=self.parent.embed, view=self)
                    self.embed.remove_footer()
                else: print("win detected")
                return await super().on_timeout()
        

        self.buttons = View(self)
        await self.msg.edit(content=None, embed=self.embed, view=self.buttons)
        try:
            while not self.win:
                await self.buttons.wait()
                if self.kill: raise handler.Kill
                del self.buttons
                self.buttons = View(self)
            for b in self.buttons.children:
                b.disabled = True
            if type(self.win) == str: self.embed = discord.Embed(title="It's a draw!", description="\n".join(symbols[self.players.index(p)][0] + " - " + p.name for p in self.players), colour=symbols[self.turn % 2][1])
            else: self.embed = discord.Embed(title=f"{self.win.name} won!", description="\n".join(symbols[self.players.index(p)][0] + " - " + p.name for p in self.players), colour=symbols[self.turn % 2][1])
            await self.msg.edit(embed=self.embed, view=self.buttons)
            self.buttons.stop()
            handler.del_from_current_games(self)
            del self
        except handler.Kill:
            handler.del_from_current_games(self)
            del self
        except:
            handler.del_from_current_games(self)
            try:
                self.embed.title = "Whoops! An error occured."
                self.embed.remove_footer()
                try:
                    for b in self.buttons.children:
                        b.disabled = True
                except: pass
                await self.msg.edit(embed=self.embed, view=self.buttons)
            except: pass
            del self