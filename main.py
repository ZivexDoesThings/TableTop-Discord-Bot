import discord, random, asyncio, logging, pickle, itertools
from discord.ext import tasks, commands
from discord import app_commands
from datetime import datetime
from emoji import UNICODE_EMOJI
from languages import Language
# from patrons import Patron, get_patrons   # Unused for now, until I can figure out the issue with Patreon not providing patrons' Discord IDs. The related files are not yet included in this repository. See update_patrons() (line 134)
from games import _handler as handler
import tt_assets as assets

token = open('token.txt', 'r').read() # Be sure to update token.txt with the bot's token if hosting yourself
statuses = [
            #discord.CustomActivity(name="Hosting games in " + str(len(bot.guilds)) + " servers."), # This one will be enabled with v2.0.0's full release
            discord.CustomActivity(name="👀 Beta Testing v2.0 in select servers"),
            discord.CustomActivity(name="✨ New Year, New Me"),
            discord.CustomActivity(name="🫶 Support development on Patreon!")
            ]

# List of guilds in which debug commands will show up
# If the guild has any other members that aren't bot admins you'll want to ensure that per-command permissions are set so that only you (and/or any other bot admins) can use them.
dev_guilds = [
    discord.Object(id=0)
]

# List of guilds that have access to all other commands. This will be removed at full release for a global command tree.
beta_test_guilds = [
    discord.Object(id=0)
]

# Load player statistics file (or creates if no such file exists)
try:
    file = open('storage/windata.pkl', 'rb')
    windata = pickle.load(file)
    file.close()
except:
    windata = {}
    with open('storage/windata.pkl', 'wb') as f: # Creates the file and saves the data (in this case, an empty dict) to it 
        pickle.dump(windata, f, pickle.HIGHEST_PROTOCOL)
        f.close

# Server language storage file
try:
    file = open('storage/lang.pkl', 'rb')
    langs = pickle.load(file)
    file.close()
except:
    langs = {}
    with open('storage/lang.pkl', 'wb') as f: # Creates the file and saves the data (in this case, an empty dict) to it 
        pickle.dump(langs, f, pickle.HIGHEST_PROTOCOL)
        f.close

# Premium-enabled users/servers storage file
try:
    file = open('storage/premium.pkl', 'rb')
    premium = pickle.load(file)
    file.close()
except:
    premium = {
        'permanent_users':[], # Add user IDs here to unlock premium features for them without worrying about Patreon pledges, etc
        'servers':[] # Add server IDs here to unlock premium features for them
        }
    with open('storage/premium.pkl', 'wb') as f: # Creates the file and saves the data to it 
        pickle.dump(premium, f, pickle.HIGHEST_PROTOCOL)
        f.close


intents=discord.Intents.all()
intents.message_content = False

# Sharded Bot
bot = commands.AutoShardedBot(command_prefix="]", intents=intents)

# Non-sharded Bot
#bot = commands.Bot(command_prefix="]", intents=intents)

async def check_allowed(ctx:discord.Interaction):
    "Prevents users that aren't listed as admins/developers of the bot in the Discord Developer Portal from using a command"
    if ctx.user.id not in bot.owner_ids:
        await ctx.response.send_message(content="Oops! You're not supposed to see this command... ( ⚆ _ ⚆ )\n*I was never here...*", ephemeral=True, delete_after=10)

        embed = discord.Embed(title="🚨 Illegal Dev Command Usage 🚨", description=f"**Command:** `{ctx.command.name}`\n**User:** {ctx.user.global_name} (`{ctx.user.name}`)\n{ctx.channel.jump_url}\n{ctx.guild.name} > #{ctx.channel.name}")
        
        for u in bot.owner_ids:
            user = bot.get_user(u)
            await user.send(embed=embed)
        return False
    else: return True

def check_emoji(user:discord.Member): # This isn't actually used anywhere at the moment (it's a remnant of v1) but it might come in useful when properly implementing custom emoji into games so we'll keep it here for now
    "Checks that the bot is able to use certain custom emoji"
    def get_emoji(emoji):
        "Parses a string to get emoji ID"
        colon_count = 0
        id_string = ""
        for char in emoji:
            if colon_count == 2 and char != ">":
                id_string += char
            if char == ":": colon_count += 1
        return bot.get_emoji(int(id_string))

    if user in premium:
        if premium[user][0] in UNICODE_EMOJI: return
        elif type(premium[user][0]) != int:
            if get_emoji(premium[user][0]).is_usable(): return
            else: premium[user][0] = 0

def flatten(x): # Another remnant for flattening lists of lists into one list (if that makes sense)
    return list(itertools.chain(*x))

if __name__ == "__main__":
    logger = logging.getLogger()
    logging.basicConfig(filename='errors.log', level=logging.ERROR, format='\n%(asctime)s - %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')

    @tasks.loop(seconds=15)
    async def change_status():
        global statuses
        # Update number of servers in the status per loop
        #statuses[0] = discord.CustomActivity(name="Hosting games in " + str(len(bot.guilds)) + " servers.") # This status will be enabled with full release
        await bot.change_presence(activity=statuses[(change_status.current_loop % len(statuses))])

    @tasks.loop(hours=2)
    async def prune_users():
        global gamesPlayed
        global windata
        gamesPlayed = {} # Clears the number of games played per person (which resets the triggers for the sendPromo function)
        to_delete = []
        for user in windata:
            if not bot.get_user(user): to_delete.append(user) # Removes the user from the stats when an attempt to find the user returns None, meaning the user no longer exists
            elif bot.get_user(user).bot: to_delete.append(user) # Removes any bot users from the stats
        for u in to_delete:
            del windata[u] # Removes all the users afterwards to prevent RuntimeError: dict changed size during iteration
    
    @tasks.loop(minutes=5)
    async def update_patrons():
        # The below is alternative code that hooks in to the Patreon API directly, but for some reason Patreon seems to send all the user data EXCEPT FOR DISCORD IDS which really sucks

#         patrons = await get_patrons()
#         old_patrons = handler.read_premium_list()

#         new_patrons = []
#         removed_patrons = []
#         declined = []
#         for patron in patrons:
#             if type(patrons[patron]) == Patron:
#                 if patrons[patron].declined: declined.append(patrons[patron])
#                 if patron not in old_patrons: new_patrons.append(patrons[patron])
#         for patron in old_patrons:
#             if type(old_patrons[patron]) == Patron:
#                 if patron not in patrons: removed_patrons.append(patrons[patron])

#         for p in declined:
#             elapsed = p.declined - datetime.now()
#             if elapsed.seconds < 100: # Fresh one
#                 pass # Send first warning
#             elif 518500 >= elapsed.seconds >= 518400: # 6 Days
#                 pass # Send final warning
#             elif elapsed.seconds >= 604800: # 7 days
#                 pass # Revoke access

        old_patrons = handler.read_premium_list() # Stored as {Discord User ID : Patreon Tier Number}
        premium = dict(old_patrons)
        new_patrons = {}
        removed_patrons = []
        del old_patrons['permanent_users'], old_patrons['servers']


        patrons = {}
        tiers = { # Matches Patreon tiers to Discord role IDs - specific to the TableTop Support Server
            1:657395134241177601,
            2:657395291884093450,
            3:657396622359003139,
            4:1140920695019282482
            }

        for m in bot.get_guild(657394368789086218).members: # Guild ID used here is the TableTop Server to match the roles
            for role in m.roles:
                for key in tiers:
                    if role.id == tiers[key]:
                        patrons[m.id] = key

        for p in old_patrons:
            if p not in patrons:
                removed_patrons.append(p)
                del premium[p]
        for p in patrons:
            if p not in old_patrons:
                new_patrons[p], premium[p] = patrons[p]

        new_users = [bot.get_user(u) for u in new_patrons]
        removed_users = [bot.get_user(u) for u in removed_patrons]

        for user in new_users:
            embeds = []
            embeds.append(discord.Embed(description = f"""## Hi {user.global_name},
# Welcome to TableTop Premium!

Your bonus features have been successfully activated.
Here's your comprehensive guide to everything you've just unlocked:""", colour=assets.dark_blue))            
            embeds.append(discord.Embed(description="""# Cosmetics
## Color
Set the color on the sidebar of a game to your own custom color when it's your turn.
To change it, use the `/settings` command, and press the 'Color' button.
You'll be greeted with the color selector, where you can adjust the Hue, Saturation and Brightness values, or type in a hex code or RGB value of the color you want to use.
## Emoji Display
Change the look of your game pieces to any emoji - unicode or custom, including animated emoji!
This is also accessed through the `/settings` command. Press the 'Emoji Display' button """, colour=assets.yellow))
            
            # The below section will be uncommented/edited as features are implemented - note that these are subject to change.

#             if patrons[user.id] >= 2: embeds.append(discord.Embed(description="""# Party Servers
# ## Maximum Players Increase
# Let chaos reign!
# - Mega Connect 4 games can have anywhere from 3 to 6 players.
# - Mastermind games can have up to 8 players
# - Hangman games can have up to 16 players
# ## Adding Party Servers
# To add, remove or replace a server in your party list, use the `/settings` command, and press the 'Party Servers' button.
# From there, you can add the server that the command was run in, or another server by name or ID.
# -# Note: There is a 48-hour cooldown for swapping out servers once you have reached your maximum number of party servers""", colour=assets.red))

#             if patrons[user.id] >= 4: embeds.append(discord.Embed(description="""# Status Message
# Shoutout yourself, your community, or just be funny in the bot's status! Submit one through the settings menu.
# Note: These are manually approved, so may take some time to appear. You'll be notified via DM when your message has been reviewed.""", colour=assets.green))
            embeds.append(discord.Embed(description="And there's plenty more in the development pipeline... Stay tuned!\nThanks again for your support! ✌️", colour=assets.light_blue))
            await user.send(embeds=embeds)

        for user in removed_users:
            if user.id in [m.id for m in bot.get_guild(657394368789086218).members]: # If Patreon role is removed
                embed = discord.Embed(description="## Game Over?\nHey there,\nI just wanted to give one more 'thank you' for your financial support on this project, it's been a great help!\n\nWhether you've intentionally left the Patreon program or this was simply a short-term billing issue (which you'll probably want to fix, by the way), I hope you've enjoyed your time in the Party Zone!\n\nOf course, this is by no means goodbye - all of the free features are still available to you! I'm sure we'll be at the table together soon 🫶", colour=assets.light_grey)
            else: # If user leaves the server
                embed = discord.Embed(description="## Wait up!\nI couldn't help but notice you left the TableTop server recently. In doing so, you'll be missing out on all the benefits you have as part of your Patreon membership.\n\nWhether that was the intention or not, we're sad to see you go! Know that you're always welcome back at the table, whenever you're ready 🫶", colour=assets.light_grey)
            await user.send(embed=embed)

        with open('storage/premium.pkl', 'wb') as f: # Save patrons
            pickle.dump(premium, f, pickle.HIGHEST_PROTOCOL)
            f.close

    @bot.event
    async def on_ready():
        try:
            await bot.load_extension("game_commands")
            await bot.load_extension("utility_commands")
            await bot.load_extension("dev_commands")
            
            for dg in dev_guilds:
                await bot.tree.sync(guild=dg)
            for btg in beta_test_guilds:
                await bot.tree.sync(guild=btg)
            await bot.tree.sync()
            
            change_status.start()
            prune_users.start()
            update_patrons.start()
            
            print("Everything looks good to go!")
        except commands.errors.ExtensionAlreadyLoaded: pass

    @bot.tree.command(guilds=dev_guilds)
    @app_commands.choices(
        sync = [
            app_commands.Choice(name="True", value=1),
            app_commands.Choice(name="False", value=0)])
    async def update(ctx:discord.Interaction, sync:int=0):
        "DEV ONLY: Refreshes all extensions, and syncs command tree (optional)"
        if not await check_allowed(ctx): return

        await bot.reload_extension("game_commands", package='tabletop')
        await bot.reload_extension("utility_commands", package='tabletop')
        await bot.reload_extension("dev_commands", package='tabletop')

        if bool(sync):
            await ctx.response.send_message(content="Extensions reloaded. Syncing global command tree...", ephemeral=True)
            await bot.tree.sync()
            await ctx.edit_original_response(content="Global command tree synced. Syncing guild-specific command trees...")
            for guild in dev_guilds:
                await bot.tree.sync(guild=guild)
            await ctx.edit_original_response(content="Successfully updated all extensions and command trees")

        else: await ctx.response.send_message(content="Successfully updated all extensions", ephemeral=True, delete_after=20)
    
    @bot.tree.command(guilds=dev_guilds)
    @app_commands.checks.has_permissions(administrator=True)
    async def add_status(ctx:discord.Interaction, status:str):
        "DEV ONLY: Adds a phrase to the status loop"
        if not await check_allowed(ctx): return
        global statuses
        statuses.append(discord.CustomActivity(name=status))
        await ctx.response.send_message(content="Successfully added to status loop\n" + status, ephemeral=True)

    @bot.tree.command(guilds=dev_guilds)
    @app_commands.checks.has_permissions(administrator=True)
    async def view_status(ctx:discord.Interaction):
        "DEV ONLY: View all phrases in the status loop"
        if not await check_allowed(ctx): return
        global statuses
        string = ""
        for i in statuses: string += i.name + "\n"
        await ctx.response.send_message(content=string, ephemeral=True)

    @bot.tree.command(guilds=dev_guilds)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_status(ctx:discord.Interaction, status:int):
        "DEV ONLY: Removes a phrase from the status loop"
        if not await check_allowed(ctx): return
        global statuses
        s = statuses.pop(status)
        await ctx.response.send_message(content=f"{s.name}\nSuccessfully removed from status loop", ephemeral=True)

    bot.run(token)
