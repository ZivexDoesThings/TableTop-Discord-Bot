from typing import Any, Optional
import discord, colorsys, webcolors, pickle, random, importlib, emoji, itertools
from discord import app_commands
from discord.ext import commands
from games import _handler as handler

import tt_assets as assets

def reload_all():
    global discord, colorsys, webcolors, pickle, random, importlib, app_commands, commands, handler, assets
    for module in [discord, colorsys, webcolors, pickle, random, importlib, app_commands, commands, handler, assets]:
        importlib.reload(module)

emoji_blacklist = [ # These emoji specifically can't be used as emoji in discord.ui.Button, for some reason. Thus, they shall be forever banished from this digital realm.
    ":red_hair:",
    ":curly_hair:",
    ":white_hair:",
    ":bald:",
    ":dark_skin_tone:",
    ":medium-dark_skin_tone:",
    ":medium_skin_tone:",
    ":medium-light_skin_tone:",
    ":light_skin_tone:",
    ":eye_in_speech_bubble:",
    ":exclamation_question_mark:",
]

class FailedCheck(Exception):
    pass

class UserSettings:
    class Cosmetics:
        def __init__(self):
            self.colour = None
            self.emoji = None
            
    class Offline:
        def __init__(self):
            self.disabled = False
            self.invis = True
            self.idle = False
            self.dnd = False

        def disable(self):
            self.disabled = True
            self.invis = False
            self.idle = False
            self.dnd = False
        
        def get_value(self):
            if self.disabled: return "Disabled"
            if self.invis and self.idle and self.dnd: return "Enabled; Offline, Idle & Do Not Disturb"
            elif self.invis and self.idle: return "Enabled; Offline & Idle"
            elif self.invis and self.dnd: return "Enabled; Offline & Do Not Disturb"
            elif self.dnd and self.idle: return "Enabled; Idle & Do Not Disturb"
            elif self.idle: return "Enabled; Idle only"
            elif self.dnd: return "Enabled; Do Not Disturb only"
            elif self.invis: return "Enabled (Default)"

    class DisplayName:
        def __init__(self):
            self.set_global_name()

        def set_global_name(self):
            self.global_name = True
            self.nick = False
            self.username = False

        def set_nick(self):
            self.global_name = False
            self.nick = True
            self.username = False

        def set_username(self):
            self.global_name = False
            self.nick = False
            self.username = True
        
        def get_value(self):
            if self.global_name: return "Global Name (Default)"
            elif self.nick: return "Server Nickname"
            else: return "Username"
    
    class Structure:
        def __init__(self):
            self.set_turn()

        def set_turn(self):
            self.turn = True
            self.game = False
            self.simultaneous = False

        def set_game(self):
            self.turn = False
            self.game = True
            self.simultaneous = False

        def set_simultaneous(self):
            self.turn = False
            self.game = False
            self.simultaneous = True

        def get_value(self):
            if self.turn: return "Switch Players per Turn (Default)"
            elif self.game: return "Switch Players per Game"
            else: return "Simultaneous Turns"
        
    class MMDisplay:
        def __init__(self):
            self.set_colour()

        def set_colour(self):
            self.colour = True
            self.number = False
        
        def set_number(self):
            self.colour = False
            self.number = True

        def get_value(self):
            if self.colour: return "Colours (Default)"
            elif self.number: return "Numbers"

    def __init__(self):
        self.cosmetics = self.Cosmetics()
        self.offline = self.Offline()
        self.display_name = self.DisplayName()
        self.structure = self.Structure()
        self.mm_display = self.MMDisplay()
        self.premium_servers = []

class GuildSettings:
    class Structure:
        def __init__(self):
            self.set_turn()

        def set_turn(self):
            self.turn = True
            self.game = False
            self.simultaneous = False

        def set_game(self):
            self.turn = False
            self.game = True
            self.simultaneous = False

        def set_simultaneous(self):
            self.turn = False
            self.game = False
            self.simultaneous = True

        def get_value(self):
            if self.turn: return "Switch Players per Turn (Default)"
            elif self.game: return "Switch Players per Game"
            else: return "Simultaneous Turns"
    
    class Threads:
        def __init__(self):
            self.disable()

        def disable(self):
            self.disabled = True
            self.public = False
            self.private = False

        def set_public(self):
            self.disabled = False
            self.public = True
            self.private = False

        def set_private(self):
            self.disabled = False
            self.public = False
            self.private = True

        def get_value(self):
            if self.disabled: return "Disabled (Default)"
            elif self.public: return "Enabled; Public Threads"
            else: return "Enabled; Private Threads"

    def __init__(self, guild:discord.Guild):
        self.structure = self.Structure()
        self.threads = self.Threads()
        supported_langs = [
            discord.Locale.american_english,
            discord.Locale.british_english,
            discord.Locale.spain_spanish,
            discord.Locale.french,
            discord.Locale.italian,
            discord.Locale.polish,
            discord.Locale.chinese]
        if "COMMUNITY" in guild.features and guild.preferred_locale in supported_langs: self.language = None # Having 'None' as the set language will default to the guild's locale
        else: self.language = "en-US"

class UtilCommands(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

    @app_commands.command()
    async def ping(self, interaction: discord.Interaction):
        "Checks the bot's latency"
        ping = self.bot.latency * 1000
        ping_colour = int(ping/-4)+150
        lightness = 0
        if ping_colour < 0:
            ping_colour = 0
            lightness = int((ping-750)/-10)
            if lightness < -100: lightness = -100
            elif lightness > 0: lightness = 0

        hls = [ping_colour, lightness, 100]
        rgb_dec = colorsys.hls_to_rgb(hls[0]/360, (hls[1]+100)/200, hls[2]/100)
        rgb = (int(rgb_dec[0]*255), int(rgb_dec[1]*255), int(rgb_dec[2]*255))
        rgb_hex = int(webcolors.rgb_to_hex(rgb)[-6:], 16)

        await interaction.response.send_message(content=None, embed=discord.Embed(title="🏓 ***Pong!***", description=f"{round(self.bot.latency * 1000)}ms", colour=rgb_hex), ephemeral=True, delete_after=20)

    @app_commands.command()
    async def settings(self, ctx:discord.Interaction):
        "Adjust preferences such as offline detection, cosmetics, and server-wide settings for admins"

        bot = self.bot # There's a few layers of classes here, so using a static bot object to quickly refer back to without going through parents of parents
        bot_member = ctx.guild.get_member(bot.user.id)

        # Get up-to-date settings
        try: all_settings = handler.read_pickled_dict('storage/settings.pkl')
        except: all_settings = {}

        # Get user's previously saved settings. If none exists, then creates a new UserSettings object for them
        if ctx.user.id in all_settings: settings:UserSettings = all_settings[ctx.user.id]
        else: settings = UserSettings()

        # Get guild's previously saved settings. If none exists, then creates a new GuildSettings object for it
        if ctx.user.guild_permissions.manage_guild and ctx.channel.type != discord.ChannelType.private:
            if ctx.guild.id in all_settings: guild_settings:GuildSettings = all_settings[ctx.guild.id]
            else: guild_settings = GuildSettings(ctx.guild)

        premium = handler.read_premium_list()

        async def save_settings(uid, new_settings, interaction:discord.Interaction, defer=True):
            try: all_settings = handler.read_pickled_dict('storage/settings.pkl')
            except: all_settings = {}
            all_settings[uid] = new_settings
            file = open('storage/settings.pkl', 'wb')
            try:
                pickle.dump(all_settings, file, protocol=pickle.HIGHEST_PROTOCOL)
                if defer: await interaction.response.defer()
            except pickle.PicklingError:
                await interaction.response.send_message(embed=discord.Embed(title="Oops! There was an error saving your settings.", description="Try running the `/settings` command again, and adjust your settings on that one.", colour=0x96110c), ephemeral=True)
            file.close()

        def user_menu_embed():
            embed = discord.Embed(title="Settings")
            premium = handler.read_premium_list()
            try: alt_check = ctx.user.id in premium['permanent_users'][0] # For some reason the premium.pkl file had the 'permanent_users' list encased in a tuple at one stage. alt_check is there just in case that issue rears its ugly head again (in a separate try/except case because an int object is not iterable when the file is stored as intended)
            except: alt_check = False
            if ctx.user.id in premium or ctx.user.id in premium['permanent_users'] or alt_check: 
                if settings.cosmetics.colour == None: colour_str = "Default"
                else: colour_str = f"#{hex(settings.cosmetics.colour)[2:]}"
                embed.add_field(name="🌈 Colour", value=colour_str, inline=False)
                if settings.cosmetics.emoji: 
                    if settings.cosmetics.emoji.id: emoji_name = f":{settings.cosmetics.emoji.name}:" # Grabs the name of the emoji from Discord if it's a custom emoji (with an ID)
                    else: emoji_name = emoji.demojize(str(settings.cosmetics.emoji)) # Grabs the name of the emoji from the unicode library otherwise
                    embed.add_field(name=f"{settings.cosmetics.emoji} Emoji Display", value=f"\{emoji_name}", inline=False)
                else: embed.add_field(name="😍 Emoji Display", value="Default", inline=False)
            embed.add_field(name="📵 Offline Detection", value=settings.offline.get_value(), inline=False)
            embed.add_field(name="🪪 Display Name", value=settings.display_name.get_value(), inline=False)
            embed.add_field(name="🏗️ Preferred Game Structure", value=settings.structure.get_value(), inline=False)
            embed.add_field(name="🔢 Mastermind Display", value=settings.mm_display.get_value(), inline=False)
            if ctx.user.id in premium or ctx.user.id in premium['permanent_users'] and settings.cosmetics.colour != None: embed.colour = settings.cosmetics.colour
            elif ctx.user.colour.value != 0: embed.colour = ctx.user.colour.value
            else: embed.colour = discord.colour.Colour.blurple().value
            return embed
        
        def server_menu_embed():
            if bot_member.colour.value == 0: colour = discord.colour.Colour.blurple().value
            else: colour = bot_member.colour.value
            return discord.Embed(title="Server Settings", colour=colour)

        class ColourMenu(discord.ui.View):
            def __init__(self, ctx:discord.Interaction, colour:int=None):
                super().__init__()
                self.ctx = ctx
                if colour != None:
                    colour = str(hex(colour))
                    hex_code = "#" + ("0"*(6-len(colour[2:]))) + colour[2:]
                    
                    self.rgb = webcolors.hex_to_rgb(hex_code)
                    hsv = colorsys.rgb_to_hsv(int(str(self.rgb.red))/255, int(str(self.rgb.green))/255, int(str(self.rgb.blue))/255)
                    self.hue, self.saturation, self.brightness = int(hsv[0]*360), int(hsv[1]*100), int(hsv[2]*100)
                    
                else: self.hue, self.saturation, self.brightness = 0, 80, 80
            
            async def on_timeout(self):
                await self.ctx.edit_original_response(embed=user_menu_embed, view=UserMenu(self.ctx))
            
            def check_values(self):
                if self.hue < 0: self.hue += 360
                elif self.hue >= 360: self.hue -= 360

                if self.saturation >= 100:
                    self.saturation = 100
                    for i in self.children:
                        if i.label[0] == "+" and i.row == 1: i.disabled = True
                else:
                    for i in self.children:
                        if i.label[0] == "+" and i.row == 1: i.disabled = False
                if self.saturation <= 0:
                    self.saturation = 0
                    for i in self.children:
                        if i.label[0] == "-" and i.row == 1: i.disabled = True
                else:
                    for i in self.children:
                        if i.label[0] == "-" and i.row == 1: i.disabled = False

                if self.brightness >= 100:
                    self.brightness = 100
                    for i in self.children:
                        if i.label[0] == "+" and i.row == 2: i.disabled = True
                else:
                    for i in self.children:
                        if i.label[0] == "+" and i.row == 2: i.disabled = False
                if self.brightness <= 0:
                    self.brightness = 0
                    for i in self.children:
                        if i.label[0] == "-" and i.row == 2: i.disabled = True
                else:
                    for i in self.children:
                        if i.label[0] == "-" and i.row == 2: i.disabled = False

            async def update_msg(self, inter:discord.Interaction, priority="hsv"):
                if priority == "hsv":
                    self.check_values()
                    self.rgb = colorsys.hsv_to_rgb(self.hue/360, self.saturation/100, self.brightness/100)
                    hex_code = webcolors.rgb_to_hex((int(self.rgb[0]*255), int(self.rgb[1]*255), int(self.rgb[2]*255)))
                    rgb_str = f"{int(self.rgb[0]*255)}, {int(self.rgb[1]*255)}, {int(self.rgb[2]*255)}"
                else:
                    hsv = colorsys.rgb_to_hsv(self.rgb[0], self.rgb[1], self.rgb[2])
                    self.hue, self.saturation, self.brightness = int(hsv[0]*360), int(hsv[1]*100), int(hsv[2]/2.55)
                    hex_code = webcolors.rgb_to_hex((self.rgb[0], self.rgb[1], self.rgb[2]))
                    rgb_str = f"{self.rgb[0]}, {self.rgb[1]}, {self.rgb[2]}"
                    self.check_values()
                self.hex_int = int(hex_code[1:], 16)
                if self.hex_int == 0xffffff: self.hex_int = 0xfffffe
                
                await inter.response.edit_message(embed=discord.Embed(title="Edit Colour", description=f"**Hue: {self.hue}**\n0 <:hue1:1133703222406684683><:hue2:1133703244087046196><:hue3:1133703240698036265><:hue4:1133703236927356980><:hue5:1133703235375468575><:hue6:1133703232221347880><:hue7:1133703228329050113><:hue8:1133703224562548746> 360\n{'<:blank:718734451785465977>'*int(self.hue/40)}^\n**Saturation: {self.saturation}**\n0 <:sat1:1133705881251495956><:sat2:1133705901707108427><:sat3:1133705898943062036><:sat4:1133705895231094874><:sat5:1133705893272354896><:sat6:1133705889870782524><:sat7:1133705886884429864><:sat8:1133705884816638003> 100\n{'<:blank:718734451785465977>'*int(self.saturation/11)}^\n**Brightness: {self.brightness}**\n0 <:bright1:1133706652953104394><:bright2:1133706649513754715><:bright3:1133706645600473139><:bright4:1133706643461390367><:bright5:1133706639942357042><:bright6:1133706636423352320><:bright7:1133706634397503488><:bright8:1133706630807179365> 100\n{'<:blank:718734451785465977>'*int(self.brightness/11)}^\n**RGB: **{rgb_str}\n**Hex:** {hex_code}", colour=self.hex_int), view=self)

            @discord.ui.button(label="Hue", row=0, disabled=True, style=discord.ButtonStyle.blurple)
            async def hue_label(self, inter:discord.Interaction, button):
                pass # Since this button is purely for aesthetics and is disabled, no callback function is necessary
            
            @discord.ui.button(label="-10", row=0)
            async def hue_minus_ten(self, inter:discord.Interaction, button):
                self.hue -= 10
                await self.update_msg(inter)
            
            @discord.ui.button(label="+1", row=0)
            async def hue_plus_one(self, inter:discord.Interaction, button):
                self.hue += 1
                await self.update_msg(inter)
            
            @discord.ui.button(label="+10", row=0)
            async def hue_plus_ten(self, inter:discord.Interaction, button):
                self.hue += 10
                await self.update_msg(inter)
            
            @discord.ui.button(label="+100", row=0)
            async def hue_plus_hundred(self, inter:discord.Interaction, button):
                self.hue += 100
                await self.update_msg(inter)
            
            @discord.ui.button(label="Saturation", row=1, disabled=True, style=discord.ButtonStyle.blurple)
            async def sat_label(self, inter:discord.Interaction, button):
                pass
            
            @discord.ui.button(label="-10", row=1)
            async def sat_minus_ten(self, inter:discord.Interaction, button):
                self.saturation -= 10
                await self.update_msg(inter)
            
            @discord.ui.button(label="-1", row=1)
            async def sat_minus_one(self, inter:discord.Interaction, button):
                self.saturation -= 1
                await self.update_msg(inter)
            
            @discord.ui.button(label="+1", row=1)
            async def sat_plus_one(self, inter:discord.Interaction, button):
                self.saturation += 1
                await self.update_msg(inter)
            
            @discord.ui.button(label="+10", row=1)
            async def sat_plus_ten(self, inter:discord.Interaction, button):
                self.saturation += 10
                await self.update_msg(inter)
            
            @discord.ui.button(label="Brightness", row=2, disabled=True, style=discord.ButtonStyle.blurple)
            async def bright_label(self, inter, button):
                pass
            
            @discord.ui.button(label="-10", row=2)
            async def bright_minus_ten(self, inter, button):
                self.brightness -= 10
                await self.update_msg(inter)
            
            @discord.ui.button(label="-1", row=2)
            async def bright_minus_one(self, inter, button):
                self.brightness -= 1
                await self.update_msg(inter)
            
            @discord.ui.button(label="+1", row=2)
            async def bright_plus_one(self, inter, button):
                self.brightness += 1
                await self.update_msg(inter)
            
            @discord.ui.button(label="+10", row=2)
            async def bright_plus_ten(self, inter, button):
                self.brightness += 10
                await self.update_msg(inter)
            
            @discord.ui.button(label="Input Hex Code", style=discord.ButtonStyle.blurple, row=3)
            async def type_hex(self, inter:discord.Interaction, button):
                class HexModal(discord.ui.Modal, title="Input Hex Code"):
                    hex = discord.ui.TextInput(label="Hex Code", required=True, style=discord.TextStyle.short, min_length=6, max_length=7)

                    def __init__(self, parent):
                        super().__init__()
                        self.parent:ColourMenu = parent
                    
                    async def on_submit(self, inter:discord.Interaction):
                        self.hex = str(self.hex)
                        try:
                            if len(self.hex) == 6:
                                test_int = int(self.hex, 16) # Will throw a ValueError if there's anything outside of the hexadecimal scope (i.e. 0-9/a-f)
                                self.hex = "#" + self.hex # webcolors.hex_to_rgb needs a hash at the start of the string for some reason

                            elif len(self.hex) == 7: # No need for any further cases since the TextInput only allows 6-7 characters
                                if self.hex[0] != "#": raise FailedCheck # If the string is 7 long and doesn't have a hash, it's invalid.
                                test_int = int(str(self.hex)[-6:], 16) # Will throw a ValueError if there's anything outside of the hexadecimal scope (i.e. 0-9/a-f)

                            self.parent.rgb = webcolors.hex_to_rgb(self.hex)
                            await self.parent.update_msg(inter, "rgb")
                        except (FailedCheck, ValueError):
                            await inter.response.send_message(embed=discord.Embed(title="⚠️ Invalid Hex Code ⚠️", description="Make sure your code is 6 digits long and only contains 0-9/a-f", colour=0x96110c), ephemeral=True, delete_after=20)


                await inter.response.send_modal(HexModal(self))
            
            @discord.ui.button(label="Input RGB", style=discord.ButtonStyle.blurple, row=3)
            async def type_rgb(self, inter:discord.Interaction, button):
                self.rgb = (0, 0, 0)
                class RGBModal(discord.ui.Modal, title="Input RGB Values"):
                    red = discord.ui.TextInput(label="Red", required=True, style=discord.TextStyle.short, min_length=1, max_length=3)
                    green = discord.ui.TextInput(label="Green", required=True, style=discord.TextStyle.short, min_length=1, max_length=3)
                    blue = discord.ui.TextInput(label="Blue", required=True, style=discord.TextStyle.short, min_length=1, max_length=3)

                    def __init__(self, parent):
                        super().__init__()
                        self.parent:ColourMenu = parent
                    
                    async def on_submit(self, inter:discord.Interaction):
                        try:
                            for colour in (self.red, self.green, self.blue):
                                if not str(colour).isnumeric(): raise FailedCheck
                                if int(str(colour)) < 0 or int(str(colour)) > 255: raise FailedCheck
                            
                            self.parent.rgb = webcolors.IntegerRGB(int(str(self.red)), int(str(self.green)), int(str(self.blue)))

                            await self.parent.update_msg(inter, "rgb")
                        except (FailedCheck, ValueError):
                            await inter.response.send_message(embed=discord.Embed(title="⚠️ Invalid Value(s) ⚠️", description="Make sure you are only entering numbers between 0 and 255", colour=0x96110c), ephemeral=True, delete_after=20)

                await inter.response.send_modal(RGBModal(self))
            
            @discord.ui.button(label="Input HSV", style=discord.ButtonStyle.blurple, row=3)
            async def type_hsv(self, inter:discord.Interaction, button):
                class RGBModal(discord.ui.Modal, title="Input HSV Values"):
                    hue = discord.ui.TextInput(label="Hue", required=True, style=discord.TextStyle.short, min_length=1, max_length=3)
                    saturation = discord.ui.TextInput(label="Saturation", required=True, style=discord.TextStyle.short, min_length=1, max_length=3)
                    brightness = discord.ui.TextInput(label="Brightness", required=True, style=discord.TextStyle.short, min_length=1, max_length=3)

                    def __init__(self, parent):
                        super().__init__()
                        self.parent:ColourMenu = parent
                    
                    async def on_submit(self, inter:discord.Interaction):
                        try:
                            for i in (self.hue, self.saturation, self.brightness):
                                if not str(i).isnumeric(): raise FailedCheck
                                if int(str(i)) < 0 or (int(str(i)) > 360 and i == self.hue) or (int(str(i)) > 100 and i != self.hue): raise FailedCheck

                            self.parent.hue, self.parent.saturation, self.parent.brightness = int(str(self.hue)), int(str(self.saturation)), int(str(self.brightness))
                            await self.parent.update_msg(inter)
                        except (FailedCheck, ValueError):
                            await inter.response.send_message(embed=discord.Embed(title="⚠️ Invalid Value(s) ⚠️", description="Hue must be a number between 0 and 360\nSaturation and Brightness must be numbers between 0 and 100", colour=0x96110c), ephemeral=True, delete_after=20)

                await inter.response.send_modal(RGBModal(self))
            
            @discord.ui.button(label="Save", style=discord.ButtonStyle.green, row=4)
            async def save(self, inter:discord.Interaction, button):
                settings.cosmetics.colour = self.hex_int
                await save_settings(inter.user.id, settings, inter, False)
                premium = handler.read_premium_list()
                if inter.user.id in premium or ctx.user.id in premium['permanent_users']: await inter.response.send_message(embed=discord.Embed(title="Colour Saved", colour=self.hex_int), ephemeral=True, delete_after=10)
                else: await inter.response.send_message(embed=discord.Embed(title="Well this is awkward...", description="You no longer have premium features available to you!\nYour colour and emoji settings have been reset to the default", colour=0x96110c), ephemeral=True, delete_after=15)
                await ctx.edit_original_response(embed=user_menu_embed(), view=UserMenu(ctx))
            
            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, row=4)
            async def cancel(self, inter:discord.Interaction, button):
                premium = handler.read_premium_list()
                if settings.cosmetics.colour == None:
                    await inter.response.send_message(embed=discord.Embed(title="Colour Reset to Game Defaults"), ephemeral=True, delete_after=10)
                elif inter.user.id not in premium and inter.user.id not in premium['permanent_users']:
                    await inter.response.send_message(embed=discord.Embed(title="Well this is awkward...", description="You no longer have premium features available to you!\nYour colour and emoji settings have been reset to the default", colour=0x96110c), ephemeral=True, delete_after=15)
                else:
                    await inter.response.send_message(embed=discord.Embed(title=f"Colour Reverted to #{hex(settings.cosmetics.colour)[2:]}", colour=settings.cosmetics.colour), ephemeral=True, delete_after=10)
                await ctx.edit_original_response(embed=user_menu_embed(), view=UserMenu(ctx))
                
            @discord.ui.button(label="Reset to Default", style=discord.ButtonStyle.red, row=4)
            async def reset(self, inter:discord.Interaction, button):
                settings.cosmetics.colour = None
                await save_settings(inter.user.id, settings, inter, False)
                await inter.response.send_message(embed=discord.Embed(title="Colour Reset to Game Defaults"), ephemeral=True, delete_after=20)
                await ctx.edit_original_response(embed=user_menu_embed(), view=UserMenu(ctx))

        class EmojiMenu(discord.ui.View):
            def __init__(self, ctx:discord.Interaction):
                self.ctx = ctx
                super().__init__()

            @discord.ui.button(label="Search", emoji="🔍", row=3)
            async def search(self, interaction:discord.Interaction, button):
                class SearchInput(discord.ui.Modal, title="Emoji Search"):
                    query = discord.ui.TextInput(label="Search Query", min_length=1, style=discord.TextStyle.short, required=True)
                    def __init__(self, parent):
                        self.parent:EmojiMenu = parent
                        super().__init__()

                    async def on_submit(self, interaction:discord.Interaction):
                        accessible_custom_emoji = []
                        for e in [guild.emojis for guild in interaction.user.mutual_guilds]:
                            accessible_custom_emoji.extend(e)

                        primary_custom_result = [(e, f":{e.name}:", e.guild.name) for e in accessible_custom_emoji if e.name.lower().startswith(str(self.query).lower().replace(' ', '_'))]
                        secondary_custom_result = [(e, f":{e.name}:", e.guild.name) for e in accessible_custom_emoji if str(self.query).lower().replace(" ", "_") in e.name.lower()]
                        primary_unicode_result = [(y, x.lower()) for x, y in emoji.EMOJI_UNICODE_ENGLISH.items() if x.lower().startswith(f":{str(self.query).lower().replace(' ', '_')}") and x not in emoji_blacklist]
                        secondary_unicode_result = [(y, x.lower()) for x, y in emoji.EMOJI_UNICODE_ENGLISH.items() if str(self.query).lower().replace(" ", "_") in x.lower() and x not in emoji_blacklist]
                        # Note: the emoji blacklist exists because while they exist in Unicode, they do not within Discord, and thus can't be used as emojis for buttons

                        flat_results = []
                        [flat_results.append(x) for x in primary_custom_result if x[0] not in [y[0] for y in flat_results]]
                        [flat_results.append(x) for x in secondary_custom_result if x[0] not in [y[0] for y in flat_results]]
                        [flat_results.append(x) for x in primary_unicode_result if x[0] not in [y[0] for y in flat_results]]
                        [flat_results.append(x) for x in secondary_unicode_result if x[0] not in [y[0] for y in flat_results]]
                        
                        self.parent.page = 0
                        self.parent.paged_results = []
                        if len(flat_results) % 15 > 0: total_pages = len(flat_results) // 15 + 1
                        else: total_pages = len(flat_results) // 15
                        [self.parent.paged_results.append([flat_results[a] for a in range(i*15, i*15+15)]) for i in range(total_pages-1)]
                        self.parent.paged_results.append([a for a in flat_results[(total_pages-1)*15:]])

                        self.parent.results_embed = discord.Embed(title=f"Emoji Search Results - '{self.query}'")
                        if len(flat_results) > 0: self.parent.results_embed.set_footer(text=f"Page {self.parent.page+1}/{total_pages}")
                        else: self.parent.results_embed.description = "No results found"
                        for r in self.parent.paged_results[self.parent.page]:
                            if len(r) == 3: self.parent.results_embed.add_field(name=r[0], value=f"**\\{r[1]}**\n*{r[2]}*")
                            else: self.parent.results_embed.add_field(name=r[0], value=f"**\\{r[1]}**")
                        
                        class EmojiButton(discord.ui.Button):
                            def __init__(self, parent, emoji):
                                self.parent = parent
                                super().__init__(emoji=emoji)

                            async def callback(self, interaction:discord.Interaction):
                                settings.cosmetics.emoji = self.emoji
                                await save_settings(interaction.user.id, settings, interaction, False)
                                await interaction.response.edit_message(embed=user_menu_embed(), view=UserMenu(self.parent.ctx))
                                self.parent.stop()

                        class PrevPage(discord.ui.Button):
                            def __init__(self, parent):
                                self.parent:EmojiMenu = parent
                                super().__init__(label="Previous Page", emoji="◀️", row=3)
                            async def callback(self, interaction:discord.Interaction):
                                self.parent.page -= 1
                                if self.parent.page < 0: self.parent.page = total_pages - 1
                                self.parent.results_embed.clear_fields()
                                self.parent.results_embed.set_footer(text=f"Page {self.parent.page+1}/{total_pages}")
                                for r in self.parent.paged_results[self.parent.page]:
                                    if len(r) == 3: self.parent.results_embed.add_field(name=r[0], value=f"**\\{r[1]}**\n*{r[2]}*")
                                    else: self.parent.results_embed.add_field(name=r[0], value=f"**\\{r[1]}**")

                                for i in [i for i in self.parent.children if not i.row]: self.parent.remove_item(i)
                                for r in self.parent.paged_results[self.parent.page]:
                                    self.parent.add_item(EmojiButton(parent=self.parent, emoji=r[0]))
                                try: await interaction.response.edit_message(embed=self.parent.results_embed, view=self.parent)
                                except:
                                    print([i for i in self.parent.children if not i.row])
                                    for i in [i for i in self.parent.children if not i.row]: self.parent.remove_item(i)
                                    await interaction.response.edit_message(embed=self.parent.results_embed, view=self.parent)

                        class NextPage(discord.ui.Button):
                            def __init__(self, parent):
                                self.parent:EmojiMenu = parent
                                super().__init__(label="Next Page", emoji="▶️", row=3)
                            async def callback(self, interaction:discord.Interaction):
                                print(len(self.parent.paged_results))
                                self.parent.page += 1
                                if self.parent.page >= total_pages: self.parent.page = 0
                                self.parent.results_embed.clear_fields()
                                self.parent.results_embed.set_footer(text=f"Page {self.parent.page+1}/{total_pages}")
                                for r in self.parent.paged_results[self.parent.page]:
                                    if len(r) == 3: self.parent.results_embed.add_field(name=r[0], value=f"**\\{r[1]}**\n*{r[2]}*")
                                    else: self.parent.results_embed.add_field(name=r[0], value=f"**\\{r[1]}**")

                                for i in [i for i in self.parent.children if not i.row]: self.parent.remove_item(i)
                                for r in self.parent.paged_results[self.parent.page]:
                                    self.parent.add_item(EmojiButton(parent=self.parent, emoji=r[0]))
                                try: await interaction.response.edit_message(embed=self.parent.results_embed, view=self.parent)
                                except:
                                    print([i for i in self.parent.children if not i.row])
                                    for i in [i for i in self.parent.children if not i.row]: self.parent.remove_item(i)
                                    await interaction.response.edit_message(embed=self.parent.results_embed, view=self.parent)
                                print(len(self.parent.paged_results))
                        
                        if total_pages > 1:
                            row3_buttons = [i for i in self.parent.children if i.row == 3]
                            if len(row3_buttons) == 2:
                                for i in row3_buttons: self.parent.remove_item(i)
                                row3_buttons.insert(0, PrevPage(self.parent))
                                row3_buttons.insert(1, NextPage(self.parent))
                                for i in row3_buttons: self.parent.add_item(i)
                        else:
                            for i in self.parent.children:
                                if i.label in ["Previous Page", "Next Page"]: self.parent.remove_item(i)

                        for i in [i for i in self.parent.children if not i.row]: self.parent.remove_item(i)
                        for r in self.parent.paged_results[self.parent.page]:
                            self.parent.add_item(EmojiButton(parent=self.parent, emoji=r[0]))
                        
                        try: await interaction.response.edit_message(embed=self.parent.results_embed, view=self.parent)
                        except:
                            print([i for i in self.parent.children if not i.row])
                            for i in [i for i in self.parent.children if not i.row]: self.parent.remove_item(i)
                            await interaction.response.edit_message(embed=self.parent.results_embed, view=self.parent)

                await interaction.response.send_modal(SearchInput(self))

            @discord.ui.button(label="Reset to Default", style=discord.ButtonStyle.red, row=3)
            async def reset(self, interaction:discord.Interaction, button):
                settings.cosmetics.emoji = None
                await save_settings(interaction.user.id, settings, interaction, False)
                await interaction.response.send_message(embed=discord.Embed(title="Emoji Reset to Default"), ephemeral=True, delete_after=20)
                await ctx.edit_original_response(embed=user_menu_embed(), view=UserMenu(ctx))
                
            @discord.ui.button(label="Back", emoji="◀️", row=4, style=discord.ButtonStyle.blurple)
            async def back(self, interaction:discord.Interaction, button):
                await interaction.response.edit_message(embed=user_menu_embed(), view=UserMenu(self.ctx))
                self.stop()
            
            async def on_timeout(self):
                await self.ctx.edit_original_response(embed=user_menu_embed(), view=UserMenu(self.ctx))
            
        class PremiumServersMenu(discord.ui.View):
            def __init__(self, ctx):
                self.ctx = ctx
                super().__init__()

        class OfflineDetection(discord.ui.View):
            def __init__(self, ctx:discord.Interaction):
                super().__init__()
                self.ctx = ctx
                
                class DisableButton(discord.ui.Button):
                    def __init__(self, parent:OfflineDetection):
                        self.parent = parent
                        if settings.offline.disabled:
                            style = discord.ButtonStyle.green
                            disabled = True
                            label = "Disabled"
                        else:
                            style = discord.ButtonStyle.grey
                            disabled = False
                            label = "Disable"
                        super().__init__(label=label, style=style, disabled=disabled, emoji="🚫", row=1)
                    
                    async def callback(self, interaction:discord.Interaction):
                        settings.offline.disable()
                        await self.parent.update_msg()
                        await save_settings(interaction.user.id, settings, interaction)
                    
                class OfflineButton(discord.ui.Button):
                    def __init__(self, parent:OfflineDetection):
                        self.parent = parent
                        if settings.offline.invis: style = discord.ButtonStyle.green
                        else: style = discord.ButtonStyle.grey
                        super().__init__(label="Offline/Invisible", style=style, emoji="<:offline:1136864775503093850>")

                    async def callback(self, interaction:discord.Interaction):
                        settings.offline.invis = not settings.offline.invis
                        if settings.offline.invis == settings.offline.idle == settings.offline.dnd == False: settings.offline.disabled = True
                        else: settings.offline.disabled = False
                        await save_settings(interaction.user.id, settings, interaction)
                        await self.parent.update_msg()
                    
                class IdleButton(discord.ui.Button):
                    def __init__(self, parent:OfflineDetection):
                        self.parent = parent
                        if settings.offline.idle: style = discord.ButtonStyle.green
                        else: style = discord.ButtonStyle.grey
                        super().__init__(label="Idle", style=style, emoji="<:idle:1136864771665313862>")

                    async def callback(self, interaction:discord.Interaction):
                        settings.offline.idle = not settings.offline.idle
                        if settings.offline.invis == settings.offline.idle == settings.offline.dnd == False: settings.offline.disabled = True
                        else: settings.offline.disabled = False
                        await save_settings(interaction.user.id, settings, interaction)
                        await self.parent.update_msg()

                class DNDButton(discord.ui.Button):
                    def __init__(self, parent:OfflineDetection):
                        self.parent = parent
                        if settings.offline.dnd: style = discord.ButtonStyle.green
                        else: style = discord.ButtonStyle.grey
                        super().__init__(label="Do Not Disturb", style=style, emoji="<:dnd:1136864777340190861>")

                    async def callback(self, interaction:discord.Interaction):
                        settings.offline.dnd = not settings.offline.dnd
                        if settings.offline.invis == settings.offline.idle == settings.offline.dnd == False: settings.offline.disabled = True
                        else: settings.offline.disabled = False
                        await save_settings(interaction.user.id, settings, interaction)
                        await self.parent.update_msg()
                
                self.add_item(DisableButton(self))
                self.add_item(OfflineButton(self))
                self.add_item(IdleButton(self))
                self.add_item(DNDButton(self))
            
            async def update_msg(self):
                if self.ctx.user.id in premium or self.ctx.user.id in premium['permanent_users'] and settings.cosmetics.colour != None: colour = settings.cosmetics.colour
                else: colour = discord.colour.Colour.blurple().value
                fields = [("🚫 Disable", "Marks you as always available.\nNo game invitations will be turned down on your behalf.\n", settings.offline.disabled),
                          ("<:offline:1136864775503093850> Offline/Invisible", "Marks you as unavailable while you are offline or invisible.\n", settings.offline.invis),
                          ("<:idle:1136864771665313862> Idle", "Marks you as unavailable while your status is set to Idle.\n", settings.offline.idle),
                          ("<:dnd:1136864777340190861> Do Not Disturb", "Marks you as unavailable while your status is set to Do Not Disturb.\n", settings.offline.dnd)
                          ]
                embed = discord.Embed(title="Offline Detection Settings", description="*Select when you are marked as unavailable.\nWhen this happens, other users will not be allowed to send you game invitations, and any ongoing games will have random moves made on your behalf.*", colour=colour)
                embed.set_footer(text="Select all options that you wish to apply.")
                for i in fields:
                    if i[2]: tick = " ✅"
                    else: tick = ""
                    embed.add_field(name=i[0]+tick, value=i[1], inline=False)
                await self.ctx.edit_original_response(embed=embed, view=OfflineDetection(self.ctx))
                self.stop()
                
            @discord.ui.button(label="Back", emoji="◀️", row=2, style=discord.ButtonStyle.blurple)
            async def back(self, interaction:discord.Interaction, button):
                await interaction.response.edit_message(embed=user_menu_embed(), view=UserMenu(self.ctx))
                self.stop()
            
            async def on_timeout(self):
                await self.ctx.edit_original_response(embed=user_menu_embed(), view=UserMenu(self.ctx))

        class DisplayName(discord.ui.View):
            def __init__(self, ctx:discord.Interaction):
                super().__init__()
                self.ctx = ctx

                class GlobalNameButton(discord.ui.Button):
                    def __init__(self, parent:DisplayName):
                        self.parent = parent
                        if settings.display_name.global_name:
                            style = discord.ButtonStyle.green
                            disabled = True
                        else:
                            style = discord.ButtonStyle.grey
                            disabled = False
                        super().__init__(label="Global Display Name", style=style, disabled=disabled)
                    
                    async def callback(self, interaction:discord.Interaction):
                        settings.display_name.set_global_name()
                        await self.parent.update_msg(interaction)
                        await save_settings(interaction.user.id, settings, interaction)

                class NickButton(discord.ui.Button):
                    def __init__(self, parent:DisplayName):
                        self.parent = parent
                        if settings.display_name.nick:
                            style = discord.ButtonStyle.green
                            disabled = True
                        else:
                            style = discord.ButtonStyle.grey
                            disabled = False
                        super().__init__(label="Server Nickname", style=style, disabled=disabled)
                    
                    async def callback(self, interaction:discord.Interaction):
                        settings.display_name.set_nick()
                        await self.parent.update_msg(interaction)
                        await save_settings(interaction.user.id, settings, interaction)

                class UsernameButton(discord.ui.Button):
                    def __init__(self, parent:DisplayName):
                        self.parent = parent
                        if settings.display_name.username:
                            style = discord.ButtonStyle.green
                            disabled = True
                        else:
                            style = discord.ButtonStyle.grey
                            disabled = False
                        super().__init__(label="Username", style=style, disabled=disabled)
                    
                    async def callback(self, interaction:discord.Interaction):
                        settings.display_name.set_username()
                        await self.parent.update_msg(interaction)
                        await save_settings(interaction.user.id, settings, interaction)

                self.add_item(GlobalNameButton(self))
                self.add_item(NickButton(self))
                self.add_item(UsernameButton(self))

            async def update_msg(self, interaction:discord.Interaction):
                if self.ctx.user.id in premium or self.ctx.user.id in premium['permanent_users'] and settings.cosmetics.colour != None: colour = settings.cosmetics.colour
                else: colour = discord.colour.Colour.blurple().value
                # interaction.user is used here for the most up-to-date version of the user (instead of self.ctx.user) in case of name changes between the initial command invocation and showing the display name options.
                fields = [(f"Global Name - {interaction.user.global_name}", "The primary name shown on your main profile.", settings.display_name.global_name),
                          (f"Server Nickname - {interaction.user.display_name}", "Any server-specific nickname you might have. If you don't have one, this will be the same as your global name.", settings.display_name.nick),
                          (f"Username - {interaction.user.name}", "Your unique alphanumeric handle.", settings.display_name.username)
                          ]
                embed = discord.Embed(title="Display Name Settings", description="*Select which name to use when referring to you.*", colour=colour)
                for i in fields:
                    if i[2]: tick = " ✅"
                    else: tick = ""
                    embed.add_field(name=i[0]+tick, value=i[1], inline=False)
                await self.ctx.edit_original_response(embed=embed, view=DisplayName(self.ctx))
                self.stop()
                
            @discord.ui.button(label="Back", emoji="◀️", row=1, style=discord.ButtonStyle.blurple)
            async def back(self, interaction:discord.Interaction, button):
                await interaction.response.edit_message(embed=user_menu_embed(), view=UserMenu(self.ctx))
                self.stop()
            
            async def on_timeout(self):
                await self.ctx.edit_original_response(embed=user_menu_embed(), view=UserMenu(self.ctx))

        class GameStructure(discord.ui.View):
            def __init__(self, ctx:discord.Interaction):
                super().__init__()
                self.ctx = ctx

                class TurnButton(discord.ui.Button):
                    def __init__(self, parent:GameStructure):
                        self.parent = parent
                        if settings.structure.turn:
                            style = discord.ButtonStyle.green
                            disabled = True
                        else:
                            style = discord.ButtonStyle.grey
                            disabled = False
                        super().__init__(label="Per Turn", style=style, disabled=disabled)
                    
                    async def callback(self, inter:discord.Interaction):
                        settings.structure.set_turn()
                        await save_settings(inter.user.id, settings, inter)
                        await self.parent.update_msg()

                class GameButton(discord.ui.Button):
                    def __init__(self, parent:GameStructure):
                        self.parent = parent
                        if settings.structure.game:
                            style = discord.ButtonStyle.green
                            disabled = True
                        else:
                            style = discord.ButtonStyle.grey
                            disabled = False
                        super().__init__(label="Full Game", style=style, disabled=disabled)
                    
                    async def callback(self, inter:discord.Interaction):
                        settings.structure.set_game()
                        await save_settings(inter.user.id, settings, inter)
                        await self.parent.update_msg()

                class SimultaneousButton(discord.ui.Button):
                    def __init__(self, parent:GameStructure):
                        self.parent = parent
                        if settings.structure.simultaneous:
                            style = discord.ButtonStyle.green
                            disabled = True
                        else:
                            style = discord.ButtonStyle.grey
                            disabled = False
                        super().__init__(label="Simultaneous", style=style, disabled=disabled)
                    
                    async def callback(self, inter:discord.Interaction):
                        settings.structure.set_simultaneous()
                        await save_settings(inter.user.id, settings, inter)
                        await self.parent.update_msg()
                
                self.add_item(TurnButton(self))
                self.add_item(GameButton(self))
                self.add_item(SimultaneousButton(self))

            async def update_msg(self):
                if self.ctx.user.id in premium or self.ctx.user.id in premium['permanent_users'] and settings.cosmetics.colour != None: colour = settings.cosmetics.colour
                else: colour = discord.colour.Colour.blurple().value
                fields = [("Per Turn", "Switches between players after each attempt", settings.structure.turn),
                          ("Full Game", "Each player's turn goes for the entire length of the game. For instance, the second player's turn in a Battleship game does not start until the first player sinks all their ships.", settings.structure.game),
                          ("Simultaneous", "All players play at the same time. Useful for fast games.", settings.structure.simultaneous)
                          ]
                embed = discord.Embed(title="Game Structure Preferences", description="*Select the game structure you would prefer to use for Mastermind, Battleship and Hangman.\nNote: This will only come into effect if the majority of players have the same setting. Otherwise, the server's default setting will be used.*", colour=colour)
                for i in fields:
                    if i[2]: tick = " ✅"
                    else: tick = ""
                    embed.add_field(name=i[0]+tick, value=i[1], inline=False)
                await self.ctx.edit_original_response(embed=embed, view=GameStructure(self.ctx))
                self.stop()
                
            @discord.ui.button(label="Back", emoji="◀️", row=1, style=discord.ButtonStyle.blurple)
            async def back(self, interaction:discord.Interaction, button):
                await interaction.response.edit_message(embed=user_menu_embed(), view=UserMenu(self.ctx))
                self.stop()
            
            async def on_timeout(self):
                await self.ctx.edit_original_response(embed=user_menu_embed(), view=UserMenu(self.ctx))

        class MMDisplay(discord.ui.View):
            def __init__(self, ctx:discord.Interaction, example_code:list=None):
                super().__init__()
                self.ctx = ctx
                if example_code == None:
                    self.example_code = [random.randint(0,9) for i in range(6)]
                else: self.example_code = example_code
                self.colour_code = ""
                self.number_code = ""
                code_items = [[assets.black_counter, "0️⃣"], [assets.red_counter, "1️⃣"], [assets.orange_counter, "2️⃣"], [assets.yellow_counter, "3️⃣"], [assets.green_counter, "4️⃣"], [assets.blue_counter, "5️⃣"], [assets.purple_counter, "6️⃣"], [assets.pink_counter, "7️⃣"], [assets.brown_counter, "8️⃣"], [assets.white_counter, "9️⃣"]]
                for i in self.example_code:
                    self.colour_code += code_items[i][0]
                    self.number_code += code_items[i][1]

                class ColourButton(discord.ui.Button):
                    def __init__(self, parent:MMDisplay):
                        self.parent = parent
                        if settings.mm_display.colour:
                            style = discord.ButtonStyle.green
                            disabled = True
                        else:
                            style = discord.ButtonStyle.grey
                            disabled = False
                        super().__init__(label="Colours", emoji="🌈", style=style, disabled=disabled)
                    
                    async def callback(self, inter:discord.Interaction):
                        settings.mm_display.set_colour()
                        await save_settings(inter.user.id, settings, inter)
                        await self.parent.update_msg()

                class NumberButton(discord.ui.Button):
                    def __init__(self, parent:MMDisplay):
                        self.parent = parent
                        if settings.mm_display.number:
                            style = discord.ButtonStyle.green
                            disabled = True
                        else:
                            style = discord.ButtonStyle.grey
                            disabled = False
                        super().__init__(label="Numbers", emoji="🔢", style=style, disabled=disabled)
                    
                    async def callback(self, inter:discord.Interaction):
                        settings.mm_display.set_number()
                        await save_settings(inter.user.id, settings, inter)
                        await self.parent.update_msg()
            
                self.add_item(ColourButton(self))
                self.add_item(NumberButton(self))

            async def update_msg(self):
                if self.ctx.user.id in premium or self.ctx.user.id in premium['permanent_users'] and settings.cosmetics.colour != None: colour = settings.cosmetics.colour
                else: colour = discord.colour.Colour.blurple().value
                fields = [("Colours", f"Displays codes like this:\n{self.colour_code}", settings.mm_display.colour),
                          ("Numbers", f"Displays codes like this:\n{self.number_code}", settings.mm_display.number),
                          ]
                embed = discord.Embed(title="Mastermind Display Settings", description="Select the way you would like to view your codes in Mastermind by default.\nNote: You can switch between the two at any point during a game, but this determines what will show first.", colour=colour)
                for i in fields:
                    if i[2]: tick = " ✅"
                    else: tick = ""
                    embed.add_field(name=i[0]+tick, value=i[1], inline=False)
                await self.ctx.edit_original_response(embed=embed, view=MMDisplay(self.ctx, self.example_code))
                self.stop()

            @discord.ui.button(label="Back", emoji="◀️", row=1, style=discord.ButtonStyle.blurple)
            async def back(self, interaction:discord.Interaction, button):
                await interaction.response.edit_message(embed=user_menu_embed(), view=UserMenu(self.ctx))
                self.stop()
            
            async def on_timeout(self):
                await self.ctx.edit_original_response(embed=user_menu_embed(), view=UserMenu(self.ctx))

        class LanguageMenu(discord.ui.View):
            def __init__(self, ctx:discord.Interaction):
                super().__init__()
                self.ctx = ctx
                self.lang_list = [
                        (discord.Locale.american_english, "English (US)", "🇺🇸", "en-US"),
                        (discord.Locale.british_english, "English (UK)", "🇬🇧", "en-GB"),
                        (discord.Locale.spain_spanish, "Español", "🇪🇸", "es-ES"),
                        (discord.Locale.french, "Français", "🇫🇷", "fr"),
                        (discord.Locale.italian, "Italiano", "🇮🇹", "it"),
                        (discord.Locale.polish, "Polski", "🇵🇱", "pl"),
                        (discord.Locale.chinese, "汉语", "🇨🇳", "zh-CN")]

                class LanguageButton(discord.ui.Button):
                    def __init__(self, language, parent:LanguageMenu):
                        self.parent = parent
                        self.language = language
                        if guild_settings.language == str(self.language[0]):
                            style = discord.ButtonStyle.green
                            disabled = True
                        else:
                            style = discord.ButtonStyle.grey
                            disabled = False
                        if len(self.parent.children) > 3: row = 1
                        else: row = 0
                        super().__init__(label=self.language[1], emoji=self.language[2], style=style, disabled=disabled, row=row)
                    
                    async def callback(self, interaction):
                        guild_settings.language = str(self.language[0])
                        await save_settings(interaction.guild.id, guild_settings, interaction)
                        await self.parent.update_msg(interaction)

                class InheritButton(discord.ui.Button):
                    def __init__(self, parent:LanguageMenu):
                        self.parent = parent
                        if guild_settings.language == None:
                            style = discord.ButtonStyle.green
                            disabled = True
                        else:
                            style = discord.ButtonStyle.grey
                            if self.parent.ctx.guild_locale not in [i[0] for i in self.parent.lang_list]: disabled = True
                            else: disabled = False
                        
                        super().__init__(label="Inherit from server settings", emoji="⬇️", style=style, disabled=disabled, row=2)
                    
                    async def callback(self, interaction):
                        if interaction.guild_locale in [i[0] for i in self.parent.lang_list]:
                            guild_settings.language = None
                            await save_settings(interaction.guild.id, guild_settings, interaction)
                        else: await interaction.response.defer()
                        await self.parent.update_msg(interaction)

                if "COMMUNITY" in ctx.guild.features and self.ctx.guild_locale not in [i[0] for i in self.lang_list] and guild_settings.language == None: guild_settings.language = 'en-US'

                for i in self.lang_list:
                    self.add_item(LanguageButton(i, self))

                if "COMMUNITY" in ctx.guild.features:
                    self.add_item(InheritButton(self))
            
            async def update_msg(self, interaction:discord.Interaction): # Interaction is used here to get the most up-to-date server info, in case the server's primary language is changed between command invocation and loading the language menu
                if bot_member.colour.value == 0: colour = discord.colour.Colour.blurple().value
                else: colour = bot_member.colour.value
                if guild_settings.language != None or interaction.guild_locale in [i[0] for i in self.lang_list]:
                    if guild_settings.language == None: lang = str(interaction.guild_locale)
                    else: lang = guild_settings.language
                    for i in self.lang_list:
                        if i[3] == lang: desc = f"{i[2]} {i[1]}"
                elif interaction.guild_locale not in [i[0] for i in self.lang_list] and guild_settings.language == None:
                    desc = "🇺🇸 English (US)"
                    guild_settings.language = 'en-US'
                else:
                    print(interaction.guild_locale in [i[0] for i in self.lang_list])
                    print(guild_settings.language == None)
                embed = discord.Embed(title="Language", description=desc, colour=colour)
                if "COMMUNITY" in interaction.guild.features:
                    field = ["Inherit From Server Settings", "Syncs the bot's language with the server's primary language (found in Server Settings > Community/Overview > Server Primary Language)"]
                    if guild_settings.language == None: tick = " ✅"
                    else: tick = " ❌"
                    if interaction.guild_locale not in [i[0] for i in self.lang_list]:
                        field[1] += "\n⚠️ **Note: Your server's primary language is currently not supported. Because of this, this setting is currently not available.**"
                    embed.add_field(name=field[0]+tick, value=field[1], inline=False)
                self.stop()
                await self.ctx.edit_original_response(embed=embed, view=LanguageMenu(interaction))

            @discord.ui.button(label="Back", emoji="◀️", row=3, style=discord.ButtonStyle.blurple)
            async def back(self, interaction:discord.Interaction, button):
                await interaction.response.edit_message(embed=server_menu_embed(), view=ServerMenu(self.ctx))
                self.stop()
            
            async def on_timeout(self):
                await self.ctx.edit_original_response(embed=server_menu_embed(), view=ServerMenu(self.ctx))

        class ServerStructure(discord.ui.View):
            def __init__(self, ctx:discord.Interaction):
                super().__init__()
                self.ctx = ctx

                class TurnButton(discord.ui.Button):
                    def __init__(self, parent:ServerStructure):
                        self.parent = parent
                        if guild_settings.structure.turn:
                            style = discord.ButtonStyle.green
                            disabled = True
                        else:
                            style = discord.ButtonStyle.grey
                            disabled = False
                        super().__init__(label="Per Turn", style=style, disabled=disabled)
                    
                    async def callback(self, inter:discord.Interaction):
                        guild_settings.structure.set_turn()
                        await save_settings(inter.guild.id, guild_settings, inter)
                        await self.parent.update_msg()

                class GameButton(discord.ui.Button):
                    def __init__(self, parent:ServerStructure):
                        self.parent = parent
                        if guild_settings.structure.game:
                            style = discord.ButtonStyle.green
                            disabled = True
                        else:
                            style = discord.ButtonStyle.grey
                            disabled = False
                        super().__init__(label="Full Game", style=style, disabled=disabled)
                    
                    async def callback(self, inter:discord.Interaction):
                        guild_settings.structure.set_game()
                        await save_settings(inter.guild.id, guild_settings, inter)
                        await self.parent.update_msg()

                class SimultaneousButton(discord.ui.Button):
                    def __init__(self, parent:ServerStructure):
                        self.parent = parent
                        if guild_settings.structure.simultaneous:
                            style = discord.ButtonStyle.green
                            disabled = True
                        else:
                            style = discord.ButtonStyle.grey
                            disabled = False
                        super().__init__(label="Simultaneous", style=style, disabled=disabled)
                    
                    async def callback(self, inter:discord.Interaction):
                        guild_settings.structure.set_simultaneous()
                        await save_settings(inter.guild.id, guild_settings, inter)
                        await self.parent.update_msg()
                
                self.add_item(TurnButton(self))
                self.add_item(GameButton(self))
                self.add_item(SimultaneousButton(self))
            
            async def update_msg(self):
                if bot_member.colour.value == 0: colour = discord.colour.Colour.blurple().value
                else: colour = bot_member.colour.value
                fields = [("Per Turn", "Switches between players after each attempt", guild_settings.structure.turn),
                          ("Full Game", "Each player's turn goes for the entire length of the game. For instance, the second player's turn in a Battleship game does not start until the first player sinks all their ships.", guild_settings.structure.game),
                          ("Simultaneous", "All players play at the same time. Useful for fast games.", guild_settings.structure.simultaneous)
                          ]
                embed = discord.Embed(title="Game Structure Settings", description="Select the structure to use by default for Mastermind, Battleship and Hangman games in this sever.", colour=colour)
                for i in fields:
                    if i[2]: tick = " ✅"
                    else: tick = ""
                    embed.add_field(name=i[0]+tick, value=i[1], inline=False)
                await self.ctx.edit_original_response(embed=embed, view=ServerStructure(self.ctx))
                self.stop()
                
            @discord.ui.button(label="Back", emoji="◀️", row=1, style=discord.ButtonStyle.blurple)
            async def back(self, interaction:discord.Interaction, button):
                await interaction.response.edit_message(embed=server_menu_embed(), view=ServerMenu(self.ctx))
                self.stop()
            
            async def on_timeout(self):
                await self.ctx.edit_original_response(embed=server_menu_embed(), view=ServerMenu(self.ctx))

        class ThreadsMenu(discord.ui.View):
            def __init__(self, ctx:discord.Interaction):
                super().__init__()
                self.ctx = ctx

                class DisableButton(discord.ui.Button):
                    def __init__(self, parent:ThreadsMenu):
                        self.parent = parent
                        if guild_settings.threads.disabled:
                            style = discord.ButtonStyle.green
                            disabled = True
                            label = "Disabled"
                        else:
                            style = discord.ButtonStyle.grey
                            disabled = False
                            label = "Disable"
                        super().__init__(label=label, style=style, disabled=disabled, emoji="🚫")
                    
                    async def callback(self, inter:discord.Interaction):
                        guild_settings.threads.disable()
                        await save_settings(inter.guild.id, guild_settings, inter)
                        await self.parent.update_msg()

                class PublicButton(discord.ui.Button):
                    def __init__(self, parent:ThreadsMenu):
                        self.parent = parent
                        if guild_settings.threads.public:
                            style = discord.ButtonStyle.green
                            disabled = True
                        else:
                            style = discord.ButtonStyle.grey
                            disabled = False
                        super().__init__(label="Public Threads", style=style, disabled=disabled, emoji="👁️")
                    
                    async def callback(self, inter:discord.Interaction):
                        guild_settings.threads.set_public()
                        await save_settings(inter.guild.id, guild_settings, inter)
                        await self.parent.update_msg()

                class PrivateButton(discord.ui.Button):
                    def __init__(self, parent:ThreadsMenu):
                        self.parent = parent
                        if guild_settings.threads.private:
                            style = discord.ButtonStyle.green
                            disabled = True
                        else:
                            style = discord.ButtonStyle.grey
                            disabled = False
                        super().__init__(label="Private Threads",emoji="🛡️", style=style, disabled=disabled)
                    
                    async def callback(self, inter:discord.Interaction):
                        guild_settings.threads.set_private()
                        await save_settings(inter.guild.id, guild_settings, inter)
                        await self.parent.update_msg()
                
                self.add_item(DisableButton(self))
                self.add_item(PublicButton(self))
                self.add_item(PrivateButton(self))
            
            async def update_msg(self):
                if bot_member.colour.value == 0: colour = discord.colour.Colour.blurple().value
                else: colour = bot_member.colour.value
                fields = [("Disable", "Will not create threads. Posts games directly to the channel the command was invoked in.", guild_settings.threads.disabled),
                          ("Public Threads", "Creates a public thread for every game, allowing anyone to spectate and commentate.", guild_settings.threads.public),
                          ("Private Threads", "Creates a private thread for every game, allowing only the players in the game and chat moderators to see it.\n*Note: Open invitations will still be sent to the parent channel before the game begins in the private thread.*", guild_settings.threads.private)
                          ]
                embed = discord.Embed(title="Threads Settings", description="Select whether you'd like games in this server to be contained in threads.", colour=colour)
                for i in fields:
                    if i[2]: tick = " ✅"
                    else: tick = ""
                    embed.add_field(name=i[0]+tick, value=i[1], inline=False)
                await self.ctx.edit_original_response(embed=embed, view=ThreadsMenu(self.ctx))
                self.stop()
                
            @discord.ui.button(label="Back", emoji="◀️", row=1, style=discord.ButtonStyle.blurple)
            async def back(self, interaction:discord.Interaction, button):
                await interaction.response.edit_message(embed=server_menu_embed(), view=ServerMenu(self.ctx))
                self.stop()
            
            async def on_timeout(self):
                await self.ctx.edit_original_response(embed=server_menu_embed(), view=ServerMenu(self.ctx))


        class UserMenu(discord.ui.View):
            def __init__(self, ctx:discord.Interaction):
                super().__init__(timeout=300)
                self.ctx = ctx

                class ServerButton(discord.ui.Button):
                    def __init__(self, parent:UserMenu):
                        self.parent = parent
                        super().__init__(label="Server Settings", row=4, emoji="🏠", style=discord.ButtonStyle.blurple)

                    async def callback(self, interaction:discord.Interaction):
                        await interaction.response.edit_message(embed=server_menu_embed(), view=ServerMenu(ctx))
                        self.parent.stop()
                
                class ColourButton(discord.ui.Button):
                    def __init__(self, parent:UserMenu):
                        self.parent = parent
                        super().__init__(label="Colour", emoji="🌈", row=0)

                    async def callback(self, interaction:discord.Interaction):
                        menu = ColourMenu(ctx, settings.cosmetics.colour)
                        await menu.update_msg(interaction)
                        self.parent.stop()

                class EmojiButton(discord.ui.Button):
                    def __init__(self, parent:UserMenu):
                        self.parent = parent
                        if settings.cosmetics.emoji: emoji = settings.cosmetics.emoji
                        else: emoji = "😍"
                        super().__init__(label="Emoji Display", emoji=emoji, row=0)

                    async def callback(self, interaction:discord.Interaction):
                        if interaction.channel.type == discord.ChannelType.private:
                            pass
                        else: await interaction.response.edit_message(view=EmojiMenu(ctx))
                        self.parent.stop()

                if ctx.user.guild_permissions.manage_guild and ctx.channel.type != discord.ChannelType.private: self.add_item(ServerButton(self))
                if ctx.user.id in premium or ctx.user.id in premium['permanent_users']:
                    self.add_item(ColourButton(self))
                    self.add_item(EmojiButton(self))

            @discord.ui.button(custom_id="offline", label="Offline Detection", emoji="📵", row=1)
            async def offline(self, interaction:discord.Interaction, button):
                menu = OfflineDetection(self.ctx)
                await interaction.response.defer()
                await menu.update_msg()
                self.stop()

            @discord.ui.button(custom_id="name", label="Display Name", emoji="🪪", row=1)
            async def name(self, interaction:discord.Interaction, button):
                menu = DisplayName(self.ctx)
                await interaction.response.defer()
                await menu.update_msg(self.ctx)
                self.stop()

            @discord.ui.button(custom_id="structure", label="Game Structure", emoji="🏗️", row=2)
            async def structure(self, interaction:discord.Interaction, button):
                menu = GameStructure(self.ctx)
                await interaction.response.defer()
                await menu.update_msg()
                self.stop()

            @discord.ui.button(custom_id="mastermind", label="Mastermind Display", emoji="🔢", row=2)
            async def mastermind(self, interaction:discord.Interaction, button):
                menu = MMDisplay(self.ctx)
                await interaction.response.defer()
                await menu.update_msg()
                self.stop()

            async def on_timeout(self):
                msg = await self.ctx.original_response()
                await msg.delete()
            
        class ServerMenu(discord.ui.View):
            def __init__(self, ctx:discord.Interaction):
                super().__init__()
                self.ctx = ctx

            @discord.ui.button(custom_id="language", label="Language", emoji="🗣️", row=0)
            async def language(self, interaction:discord.Interaction, button):
                menu = LanguageMenu(self.ctx)
                await interaction.response.defer()
                await menu.update_msg(interaction)
                self.stop()

            @discord.ui.button(custom_id="structure", label="Game Structure", emoji="🏗️", row=0)
            async def structure(self, interaction:discord.Interaction, button):
                menu = ServerStructure(self.ctx)
                await interaction.response.defer()
                await menu.update_msg()
                self.stop()

            @discord.ui.button(custom_id="threads", label="Threads", emoji="🧵", row=0)
            async def threads(self, interaction:discord.Interaction, button):
                menu = ThreadsMenu(self.ctx)
                await interaction.response.defer()
                await menu.update_msg()
                self.stop()

            @discord.ui.button(label="User Settings", row=4, emoji="🧑", style=discord.ButtonStyle.blurple)
            async def user(self, interaction:discord.Interaction, button):
                await interaction.response.edit_message(embed=user_menu_embed(), view=UserMenu(self.ctx))
                self.stop()
            
            async def on_timeout(self):
                await self.ctx.edit_original_response(embed=user_menu_embed(), view=UserMenu(self.ctx))

        if ctx.channel.type == discord.ChannelType.private: ephemeral = False
        else: ephemeral = True

        await ctx.response.send_message(embed=user_menu_embed(), view=UserMenu(ctx), ephemeral=ephemeral)

beta_test_guilds = [
            discord.Object(id=620499156368097290), # Testing Server
            discord.Object(id=657394368789086218), # TableTop Support Server
            discord.Object(id=454129794284519434), # Zivex Zone
            discord.Object(id=654316563679412274), # Kuba's Very Baller Area
            discord.Object(id=620479099948761089), # JCTheFluteFam
            discord.Object(id=577287230125506580), # Kool Beans
            discord.Object(id=467842457879576596), # TSTA
            discord.Object(id=875581905741938758) # Ripoff VIP
            ]

async def setup(bot:commands.Bot):
    reload_all()
    uc = UtilCommands(bot)
    bot.tree.add_command(uc.ping, guilds=beta_test_guilds)
    bot.tree.add_command(uc.settings, guilds=beta_test_guilds)
    print("Utility Commands Loaded")