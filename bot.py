import discord
from discord.ext import commands
import os
import random
import asyncio
import datetime
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

# --- Training Ticket Settings ---
APPLY_CHANNEL_NAME = "apply-for-training"
TICKET_CATEGORY_NAME = "Training Tickets"
TRAINER_ROLE_NAME = "Trainer"
ADMIN_ROLE_NAMES = {"Leader", "Subowner"}
LOG_CHANNEL_NAME = "training-log"
TICKET_PREFIX = "ticket-"
# -------------------------------

def _get_role_by_name(guild: discord.Guild, role_name: str):
    return discord.utils.get(guild.roles, name=role_name)

def _member_has_role(member: discord.Member, role_names: set[str]):
    member_role_names = {role.name.lower() for role in member.roles}
    return any(role_name.lower() in member_role_names for role_name in role_names)

def _is_ticket_channel(channel: discord.TextChannel):
    if not isinstance(channel, discord.TextChannel):
        return False
    if not channel.name.startswith(TICKET_PREFIX):
        return False
    if channel.category is None:
        return False
    return channel.category.name == TICKET_CATEGORY_NAME

def _is_member_applicant(member: discord.Member):
    return not _member_has_role(member, {TRAINER_ROLE_NAME} | ADMIN_ROLE_NAMES)

async def _get_or_create_ticket_category(guild: discord.Guild):
    category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
    if category is None:
        category = await guild.create_category(TICKET_CATEGORY_NAME)
    return category

def _find_existing_ticket(guild: discord.Guild, applicant_id: int):
    category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
    if category is None:
        return None

    topic_marker = f"applicant:{applicant_id}"
    for channel in category.text_channels:
        if channel.topic == topic_marker:
            return channel

    fallback_name = f"{TICKET_PREFIX}{guild.get_member(applicant_id).name.lower()}"
    return discord.utils.get(category.text_channels, name=fallback_name)

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
    
    # Loop over targeted users and DM them with a small delay to avoid rate limits
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
        # Basic rate limiting to prevent hitting DM creation limits
        await asyncio.sleep(1.0 + random.random() * 0.5)
            
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

@bot.command(name='apply', help='Open a training ticket. Use in #apply-for-training.')
async def apply(ctx):
    if ctx.guild is None:
        return
    if not isinstance(ctx.channel, discord.TextChannel) or ctx.channel.name != APPLY_CHANNEL_NAME:
        await ctx.send(f"Please use this command in #{APPLY_CHANNEL_NAME}.")
        return

    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

    category = await _get_or_create_ticket_category(ctx.guild)

    existing = _find_existing_ticket(ctx.guild, ctx.author.id)
    if existing is not None:
        await ctx.send(f"You already have an open ticket: {existing.mention}")
        return

    trainer_role = _get_role_by_name(ctx.guild, TRAINER_ROLE_NAME)
    admin_roles = [
        _get_role_by_name(ctx.guild, role_name)
        for role_name in ADMIN_ROLE_NAMES
    ]

    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        ctx.author: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    }

    if trainer_role is not None:
        overwrites[trainer_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    for role in admin_roles:
        if role is not None:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True
            )

    ticket_channel = await ctx.guild.create_text_channel(
        name=f"{TICKET_PREFIX}{ctx.author.name.lower()}",
        category=category,
        overwrites=overwrites,
        topic=f"applicant:{ctx.author.id}"
    )

    trainer_mention = trainer_role.mention if trainer_role else "Trainer"
    await ticket_channel.send(
        f"Welcome {ctx.author.mention}! {trainer_mention}, a new training ticket has been created."
    )
    await ctx.send(f"Your ticket has been created: {ticket_channel.mention}")

@bot.command(name='claim', help='Claim a training ticket (Trainer/Admin only).')
async def claim(ctx):
    if ctx.guild is None:
        return
    if not _is_ticket_channel(ctx.channel):
        await ctx.send("This command can only be used inside a training ticket.")
        return

    if not _member_has_role(ctx.author, {TRAINER_ROLE_NAME} | ADMIN_ROLE_NAMES):
        await ctx.send("You do not have permission to claim this ticket.")
        return

    await ctx.send(f"Ticket claimed by {ctx.author.mention}.")

@bot.command(name='close', help='Close a training ticket (Trainer/Admin only).')
async def close(ctx):
    if ctx.guild is None:
        return
    if not _is_ticket_channel(ctx.channel):
        await ctx.send("This command can only be used inside a training ticket.")
        return

    if not _member_has_role(ctx.author, {TRAINER_ROLE_NAME} | ADMIN_ROLE_NAMES):
        await ctx.send("You do not have permission to close this ticket.")
        return

    log_channel = discord.utils.get(ctx.guild.text_channels, name=LOG_CHANNEL_NAME)
    if log_channel is not None:
        applicant_name = "Unknown"
        if ctx.channel.topic and ctx.channel.topic.startswith("applicant:"):
            applicant_id = int(ctx.channel.topic.split(":", 1)[1])
            applicant = ctx.guild.get_member(applicant_id)
            if applicant is not None:
                applicant_name = applicant.name

        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        await log_channel.send(
            f"Ticket closed | Player: {applicant_name} | Closed by: {ctx.author.mention} | Time: {timestamp}"
        )

    await ctx.channel.delete()

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
