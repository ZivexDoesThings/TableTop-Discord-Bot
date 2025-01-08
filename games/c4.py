import sys, os.path, discord, random
from discord.ext import commands
sys.path.append(os.path.dirname("__file__"))
sys.path.append('../tabletop')

from . import _handler as handler
import tt_assets as assets
from languages import *
    
class Connect4(handler.Game):
    """
    Connect 4 & Mega Connect 4 class, inherited from `handler.Game`

    Use .connect4() or .mc4() methods to run the game, as below

    `await c4.Connect4(ctx, "Connect 4", opponent).connect4()`
    """

    async def mc4(self, bot:commands.Bot):
        """Runs a Mega Connect 4 game, including setup.\n
        Use only as an alias for connect4(), as it simply changes the name of the game shown to the users."""
        self.gameType = "Mega Connect 4"
        await self.connect4(bot)

    async def connect4(self, bot:commands.Bot):
        "Runs a Connect 4 game, including setup"
    
        @bot.listen()
        async def on_member_update(before:discord.Member, after:discord.Member):
            #print("Member update - " + after.global_name)
            for p in self.players:
                if p.id == after.id: p.check_user_update(after)
        @bot.listen()
        async def on_user_update(before:discord.User, after:discord.User):
            #print("User update - " + after.global_name)
            for p in self.players:
                if p.id == after.id: p.check_user_update(after)

        if self.gameType == None: self.gameType = "Connect 4"
        if not self.rematch:
            await self.setup()
            if self.cancel: return
            channel = await bot.fetch_channel(self.channel)
            self.msg = await channel.fetch_message(self.message)
            del self.channel

        if len(self.players) == 2:
            numbers = [assets.one, assets.two, assets.three, assets.four, assets.five, assets.six, assets.seven]
            counters = [[assets.yellow, assets.yellow_with_bg, assets.yellow_counter], [assets.red, assets.red_with_bg, assets.red_counter]]
            boardlist = [[assets.darken for j in range(7)] for i in range(6)]
        else:
            numbers = [assets.zero, assets.one, assets.two, assets.three, assets.four, assets.five, assets.six, assets.seven, assets.eight, assets.nine, assets.ten]
            counters = [[assets.yellow, assets.yellow_with_bg, assets.yellow_counter], [assets.red, assets.red_with_bg, assets.red_counter], [assets.light_blue, assets.blue_with_bg, assets.blue_counter], [assets.green, assets.green_with_bg, assets.green_counter], [assets.orange, assets.orange_with_bg, assets.orange_counter], [assets.purple, assets.purple_with_bg, assets.purple_counter]][:len(self.players)]
            boardlist = [[assets.darken for j in range(11)] for i in range(10)]
        
        self.turn = 0
        self.win = None
        self.players_embed = discord.Embed(description="\n".join(counters[self.players.index(p)][-1] + " - " + p.name for p in self.players))

        def boardGen(): # Combines the 2d array into one string with line breaks, and puts the number emojis along the bottom for indicative use
            return "\n".join("".join(i) for i in boardlist) + "\n" + "".join(numbers)

        def process_selection(column, players, turn, win):
            for row in range(len(boardlist)): # Iterates down the rows and checks for the lowest available position, and places the player's counter there
                if row < len(boardlist)-1 and boardlist[row + 1][column] != assets.darken:
                    # Places the counter if the row below contains anything other than the blank placeholder ("darken")
                    boardlist[row][column] = counters[turn%len(players)][1]
                    break
                elif row >= len(boardlist)-1: # Places the counter if the iterator reaches the bottom row
                    boardlist[row][column] = counters[turn%len(players)][1]
            # Win Detection
            # Horizontal
            for row in boardlist:
                for i in range(len(boardlist[0])-3):
                    if row[i] == row[i+1] == row[i+2] == row[i+3] == counters[turn % len(players)][1]:
                        win = players[turn % len(players)]
                        return players, turn, win
            # Vertical
            for column in range(len(boardlist[0])):
                for row in range(len(boardlist)-3):
                    if boardlist[row][column] == boardlist[row+1][column] == boardlist[row+2][column] == boardlist[row+3][column] == counters[turn % len(players)][1]:
                        win = players[turn % len(players)]
                        return players, turn, win
            # Diagonal
            for column in range(len(boardlist[0])):
                for row in range(len(boardlist)):
                    try:
                        if boardlist[row][column] == boardlist[row+1][column+1] == boardlist[row+2][column+2] == boardlist[row+3][column+3] == counters[turn % len(players)][1]:
                            win = players[turn % len(players)]
                            return players, turn, win
                    except:
                        pass
                    try:
                        if boardlist[row][column] == boardlist[row+1][column-1] == boardlist[row+2][column-2] == boardlist[row+3][column-3] == counters[turn % len(players)][1] and (column - 3) >= 0:
                            win = players[turn % len(players)]
                            return players, turn, win
                    except:
                        pass
            # Draw
            full = True
            for char in boardlist[0]:
                if char == assets.darken:
                    full = False
            if full == True:
                win = "Draw"
            
            return players, turn, win
        
        class ColumnButton(discord.ui.Button):
            def __init__(self, column:int, viewParent, gameParent, row):
                super().__init__(style=discord.ButtonStyle.grey, emoji=numbers[column], row=row)
                self.viewParent = viewParent
                self.parent = gameParent

            async def callback(self, interaction:discord.Interaction):
                if interaction.user.id not in [p.id for p in self.parent.players]:
                    await interaction.response.send_message(content="**You're not in this game!**", ephemeral=True, delete_after=20)
                    return
                elif interaction.user.id != self.parent.players[self.parent.turn % len(self.parent.players)].id:
                    await interaction.response.send_message(content="**Hold on, it's not your turn yet!**", ephemeral=True, delete_after=20)
                    return
                column = numbers.index(str(self.emoji))
                self.parent.players, self.parent.turn, self.parent.win = process_selection(column, self.parent.players, self.parent.turn, self.parent.win)
                if self.parent.win: self.viewParent.stop()
                else:
                    self.disable_if_column_full(column)
                    self.parent.turn += 1
                    self.parent.game_embed = discord.Embed(title=f"{counters[self.parent.turn % len(self.parent.players)][-1]} It's {self.parent.players[self.parent.turn % len(self.parent.players)].name}'s turn! {counters[self.parent.turn % len(self.parent.players)][-1]}", description=boardGen(), colour=counters[self.parent.turn % len(self.parent.players)][0])
                    self.parent.game_embed.set_footer(text="Press the button with the number corresponding to the row you wish to use.")
                    await interaction.response.edit_message(content=None, embeds=[self.parent.players_embed, self.parent.game_embed], view=self.viewParent)
            
            def disable_if_column_full(self, column):
                if boardlist[0][column] != assets.darken:
                    self.disabled = True

        class ColumnSelect(discord.ui.View):
            def __init__(self, gameParent=None):
                super().__init__(timeout=60)
                self.parent = gameParent
                
                for n in numbers:
                    if numbers.index(n) > 7: row = 2
                    elif numbers.index(n) > 3: row = 1
                    else: row = 0
                    self.add_item(ColumnButton(numbers.index(n), self, self.parent, row))
            
            def disable_unusable_buttons(self):
                for button in self.children:
                    button.disable_if_column_full(self.children.index(button))

        timeout = False

        try:
            while self.win == None:
                self.buttons = ColumnSelect(self)
                if not timeout:
                    self.game_embed = discord.Embed(title=f"{counters[self.turn % len(self.players)][-1]} It's {self.players[self.turn % len(self.players)].name}'s turn! {counters[self.turn % len(self.players)][-1]}", description=boardGen(), colour=counters[self.turn % len(self.players)][0])
                    self.game_embed.set_footer(text="Press the button with the number corresponding to the row you wish to use.")
                    await self.msg.edit(content=None, embeds=[self.players_embed, self.game_embed], view=self.buttons)
                else:
                    column = random.randint(0, 6)
                    while boardlist[0][column] != assets.darken:
                        column = random.randint(0, 6)
                    self.players, self.turn, self.win = process_selection(column, self.players, self.turn, self.win)
                    self.buttons.disable_unusable_buttons()
                    if self.win: self.buttons.stop()
                    else:
                        self.turn += 1
                        self.game_embed = discord.Embed(title=f"{counters[self.turn % len(self.players)][-1]} It's {self.players[self.turn % len(self.players)].name}'s turn! {counters[self.turn % len(self.players)][-1]}", description=boardGen(), colour=counters[self.turn % len(self.players)][0])
                        self.game_embed.set_footer(text=f"{self.players[(self.turn-1) % len(self.players)].name} took too long on their last turn, so a random column was selected.\nPress the button with the number corresponding to the row you wish to use.")
                        await self.msg.edit(content=None, embeds=[self.players_embed, self.game_embed], view=self.buttons)
                timeout = await self.buttons.wait()
                del self.buttons
                if self.killing: raise handler.Kill
            if type(self.win) == str:
                self.game_embed=discord.Embed(title="It's a draw!", description=boardGen(), colour=0x311163)
                await self.msg.edit(embeds=[self.players_embed, self.game_embed], view=None)
            else:
                self.game_embed=discord.Embed(title=f"{self.win.name} won!", description=boardGen(), colour=counters[self.turn%len(self.players)][0])
                await self.msg.edit(embeds=[self.players_embed, self.game_embed], view=None)
            
            # if await self.rematch_setup():
            #     print("Rematch confirmed")
            #     if self.gameType == "Connect 4": self.connect4()
            #     else: self.mc4()
            handler.del_from_current_games(self)
        except handler.Kill:
            pass
        except:
            handler.del_from_current_games(self)
            try:
                del buttons
                self.game_embed.title = "Whoops! An error occured."
                self.game_embed.remove_footer()
                await self.msg.edit(embeds=[self.players_embed, self.game_embed], view=None)
            except: pass
    
    async def kill(self):
        self.game_embed.title = "This game was manually stopped"
        self.game_embed.colour = 0x70081d
        self.game_embed.remove_footer()
        await self.msg.edit(content=None, view=None, embeds=[self.players_embed, self.game_embed])

        handler.del_from_current_games(self)