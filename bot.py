import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    print("Error: DISCORD_TOKEN is missing from .env file.")
    exit(1)

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
    # Collect target users dynamically
    targets = set()
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
        if not word.startswith('<@') and word not in ('!warping', '@everyone', '@here')
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

if __name__ == '__main__':
    bot.run(TOKEN)
