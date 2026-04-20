import discord
from discord.ext import commands
import os
import random
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    print("Error: DISCORD_TOKEN is missing from .env file.")
    exit(1)

# --- Keep-Alive Web Server for Render ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    # Render provides a port via the PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ----------------------------------------

# Setup intents
intents = discord.Intents.default()
intents.message_content = True  # Required to read commands
intents.members = True # Better to have members intent to ensure accurate user information

# Create the bot instance
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('------')
    print('Bot is ready to ping people for wars! ⚔️')

@bot.command(name='warping', help='DM users to ping them for war. Usage: !warping @user1 @user2 [optional message]')
@commands.has_permissions(administrator=True) # Ensure only admins can use this
async def warping(ctx, *args):
    # Delete the original command message so it doesn't ping the channel or clutter it
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass # Bot doesn't have manage_messages permission, which is fine

    # Collect target users dynamically
    targets = set()
    
    # Check if 'all' is passed to avoid Discord's @everyone popup/channel ping
    if 'all' in [str(a).lower() for a in args]:
        targets.update(ctx.guild.members)
        
    if ctx.message.mention_everyone:
        targets.update(ctx.guild.members) # Needs Server Members Intent in portal
    else:
        targets.update(ctx.message.mentions)
        for role in ctx.message.role_mentions:
            targets.update(role.members)

    if not targets:
        await ctx.send("Please mention the user(s), a role, or @everyone you want to ping for war.")
        return

    user_words = ctx.message.content.split()
    custom_msg_words = [
        word for word in user_words 
        if not word.startswith('<@') and word.lower() not in ('!warping', '@everyone', '@here', 'all')
    ]
    
    # Default message
    war_message = f"⚔️ **WAR PING!** ⚔️\nYou are needed for a war in **{ctx.guild.name}**!\n\nPlease check the server immediately."
    
    # If custom message provided
    if custom_msg_words:
        custom_text = ' '.join(custom_msg_words)
        war_message = f"⚔️ **WAR PING!** ⚔️\nYou are needed for a war in **{ctx.guild.name}**!\n\n**Message from {ctx.author.name}:**\n{custom_text}"
        
    success_count = 0
    fail_count = 0
    
    # Loop over targeted users and DM them
    for member in targets:
        if member.bot:
            continue # Don't ping other bots
        try:
            await member.send(war_message)
            success_count += 1
        except discord.Forbidden:
            # Cannot DM the user because they have DMs disabled or blocked the bot
            fail_count += 1
        except Exception as e:
            print(f"Failed to DM {member.name}: {e}")
            fail_count += 1
            
    # Send a confirmation in the channel
    response = f"Sent war pings! ✅ Successfully sent to **{success_count}** user(s)."
    if fail_count > 0:
        response += f" ❌ Failed to send to **{fail_count}** user(s) (They probably have DMs disabled)."
        
    await ctx.send(response)

@warping.error
async def warping_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command. Only administrators can use `!warping`.")
    else:
        await ctx.send(f"An error occurred: {error}")

@bot.command(name='war', help='Suggests the !warping command')
async def war(ctx, *args):
    await ctx.send("Did you mean `!warping`?")

@bot.command(name='hot')
async def hot(ctx):
    await ctx.send("strangesam17 is so hot")

@bot.command(name='ban', help='Ban a user. Usage: !ban @user [reason]')
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    try:
        await member.ban(reason=reason)
        await ctx.send(f"✅ Successfully banned **{member.name}**. Reason: {reason if reason else 'No reason provided.'}")
    except discord.Forbidden:
        await ctx.send("❌ I do not have permission to ban this user. Make sure my bot role is placed HIGHER in the role list than the person you are trying to ban!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")

@bot.command(name='unban', help='Unban a user by their user ID. Usage: !unban <user_id>')
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    try:
        user = discord.Object(id=user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"✅ Successfully unbanned user ID **{user_id}**.")
    except discord.NotFound:
        await ctx.send("❌ That user is not banned.")
    except discord.Forbidden:
        await ctx.send("❌ I do not have permission to unban users.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")

@ban.error
@unban.error
async def moderation_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You do not have permission to use this command.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Could not find that user. Please mention a valid user in the server.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid input. For unbanning, please provide the numeric User ID (e.g. `!unban 123456789`).")
    else:
        await ctx.send(f"❌ An error occurred: {error}")

@bot.command(name='slap', help='Slap a user with a random funny object. Usage: !slap @user')
async def slap(ctx, member: discord.Member):
    phrases = [
        f"{member.mention} just got slapped with a giant wet noodle! 🍜",
        f"{member.mention} was slapped by a flying penguin! 🐧",
        f"{member.mention} got slapped with a massive slice of pizza! 🍕",
        f"{member.mention} was slapped into next week! 🗓️",
        f"{member.mention} got slapped with a rubber chicken! 🐔"
    ]
    await ctx.send(random.choice(phrases))

if __name__ == '__main__':
    keep_alive() # Start the web server
    bot.run(TOKEN)
