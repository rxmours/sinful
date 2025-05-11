import sys, types
import html
cgi_module = types.ModuleType("cgi")
cgi_module.escape = html.escape
sys.modules["cgi"] = cgi_module

import discord, aiohttp
from discord.ext import commands, tasks
import random
import re
import os
import string
import time
import asyncio
import requests
import io
import time

prefix = '*'
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=prefix, self_bot=True, intents=intents)

token = "enter_token_here"

#variables
snipe_messages = {}
afk_users = {}
stream_url = 'https://www.twitch.tv/discord'
reacting_to = {}
status_changing_task = None
status_rotation_active = False
emoji_rotation_active = False
current_status = ""
current_emoji = ""
status_rotate_task = None
rotating_status = False
whitelisted_ids = set()
start_time = time.time()
hush_active = False
target_user = None
user_emoji_lists = {}
user_emoji_index = {}
target_user_ids = set()
single_react_users = {}
reacting_to = {}
emoji_indices = {}
stop_event = asyncio.Event()
purge_tasks = {}

@bot.remove_command('help')
@bot.event
async def on_ready():
    print(
        f'[Success] bot logged in as {bot.user.name}'
    )
    
    stream = discord.Streaming(name="Sinful Selfbot by Rxmours", url=stream_url)
    await bot.change_presence(activity=stream)

    # Start the task only once
    if status_task is None or status_task.done():
        status_task = asyncio.create_task(cycle_status())


@bot.event
async def on_message(message):
    user_id = message.author.id

    if user_id in reacting_to:
        data = reacting_to[user_id]
        
        # Ensure data is a dictionary with required keys
        if isinstance(data, dict) and "emojis" in data:
            try:
                emoji = data["emojis"][data["index"]]
                await message.add_reaction(emoji)
            except Exception as e:
                print(f"Failed to react with {emoji}: {e}")
            
            if data.get("rotate", False):
                data["index"] = (data["index"] + 1) % len(data["emojis"])
                
    if message.mentions:
        for user in message.mentions:
            if user.id in afk_users:
                await message.channel.send(f"```{user.name} is away: {afk_users[user.id]}```")

    await bot.process_commands(message)
    
@bot.command(name='prefix')
async def prefix(ctx, new_prefix=None):
    await ctx.message.delete()
    if new_prefix is None:
        await ctx.send(
            f'```[Invalid]: Its {bot.command_prefix}prefix <new_prefix>```')
            return
    bot.command_prefix = str(new_prefix)
    await ctx.send(f'```Prefix changed to {new_prefix}```')

@bot.command(name="rotatereact", aliases=['rreact', 'rr', 'react'])
async def set_emojis(ctx, *args):
    await ctx.message.delete()
    mentions = ctx.message.mentions
    emojis = [arg for arg in args if not arg.startswith("<@")]

    if not mentions:
        await ctx.send("```[Error] Invalid user mention```")
        return

    if emojis:
        for user in mentions:
            reacting_to[user.id] = {"emojis": emojis, "index": 0, "rotate": True}
        await ctx.send(f"```Now reacting to: {user.display_name}```")
    else:
        missing = [m for m in mentions if m.id not in reacting_to or not reacting_to[m.id]["emojis"]]
        if missing:
            await ctx.message.edit(content="```[Error] One or more mentioned users don't have emoji lists set yet```")
            return
        for user in mentions:
            reacting_to[user.id]["rotate"] = True
        await ctx.send(f"```Now rotating reactions for: {user.display_name}```")


@bot.command()
async def listreacts(ctx):
    await ctx.message.delete()
    if not reacting_to:
        await ctx.send("```No users are currently being reacted to.```")
        return

    lines = ["Current reactions set:"]
    for user_id, emojis in reacting_to.items():
        user = bot.get_user(user_id)
        name = user.name if user else f"User ID {user_id}"
        lines.append(f"- {name}: {' '.join(emojis)}")

    message = "```" + "\n".join(lines) + "```"
    await ctx.send(message)

@bot.command()
async def stopreact(ctx, user_mention: str = None):
    try:
        await ctx.message.delete()
    except:
        pass

    if user_mention is None:
        await ctx.send(f"```[Error]: It's {bot.command_prefix}stopreact <@user>```")
        return

    match = re.match(r'<@!?(\d+)>', user_mention)
    if not match:
        await ctx.send("```[Error]: Invalid user mention.```")
        return

    user_id = int(match.group(1))
    removed = False

    # Remove from emoji rotation tracking
    if user_id in reacting_to:
        del reacting_to[user_id]
        removed = True
    if user_id in emoji_indices:
        del emoji_indices[user_id]
        removed = True
    if user_id in user_emoji_lists:
        del user_emoji_lists[user_id]
        removed = True
    if user_id in user_emoji_index:
        del user_emoji_index[user_id]
        removed = True

    if removed:
        await ctx.send(f"```Stopped reacting to that user's messages.```")
    else:
        await ctx.send("```That user wasn't being reacted to.```")

@bot.command()
async def stopreactall(ctx):
    try:
        await ctx.message.delete()
    except:
        pass

    reacting_to.clear()
    emoji_indices.clear()
    user_emoji_lists.clear()
    user_emoji_index.clear()

    await ctx.send("```Stopped reacting to all users.```")

@bot.command()
async def ping(ctx):
    await ctx.message.delete()
    before = time.monotonic()
    message = await ctx.send("```Pinging...```")
    ping = (time.monotonic() - before) * 1000
    await message.edit(content=f"```{int(ping)}ms to ping servers```")


@bot.command(name='say', aliases=['spam'])
async def spam(ctx, times: int = None, *, message=None):
    await ctx.message.delete()
    if times is None:
        await ctx.send(
            f'[Invalid]: Command: {bot.command_prefix}spam <times> <message>')
        return
        if message is None:
            await ctx.send(
                f'[Invalid]: Command: {bot.command_prefix}spam <times> <message>'
            )
            return
    for _ in range(times):
        await ctx.send(message)
        await asyncio.sleep(0.25)


@bot.event
async def on_message_delete(message):
    channel_id = message.channel.id
    if channel_id not in snipe_messages:
        snipe_messages[channel_id] = []
    snipe_messages[channel_id].insert(0, message)
    if len(snipe_messages[channel_id]) > 50:
        snipe_messages[channel_id].pop()

@bot.command(aliases=["s"])
async def snipe(ctx, index: int = 1):
    
    channel_id = ctx.channel.id
    messages = snipe_messages.get(channel_id, [])
    if 1 <= index <= len(messages):
        msg = messages[index - 1]
        content = msg.content or "```[No text content]```"
        author = msg.author
        await ctx.send(f"```{author} said: {content}```")
    else:
        await ctx.send("```no deleted message```")

@bot.command()
async def help(ctx):
    await ctx.message.delete()
    help = f"‎ Add [@Rxmours](https://discord.gg/kf2hqD8A) for more help```{bot.command_prefix}prefix (new prefix here) for new prefix\n\n{bot.command_prefix}menu to view command catagories```"
    await ctx.send(help, delete_after=30)

@bot.command(name='menu', aliases=[''])
async def menu(ctx):
    await ctx.message.delete()
    menu = f"```catagory commands:\n{bot.command_prefix}(catagory) to view catagory commands```""```catagories:\nInfo         -   bot info\nTools        -   bot tools\nPresence     -   presence commands\nServer       -   server utility\nFun          -   entertainment\nNSFW         -   all nsfw commands```""```made by: Rxmours \nversion: 1.0```"
    await ctx.send(menu, delete_after=30)
    
@bot.command(name="info", aliases=['Info', ])
async def info(ctx):
    await ctx.message.delete()

    uptime_seconds = int(time.time() - start_time)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime = f"{days}d {hours}h {minutes}m {seconds}s"

    ping = round(bot.latency * 1000)
    visible_commands = [cmd for cmd in bot.commands if not cmd.hidden]
    command_count = len(visible_commands)

    info_message = (
        "Sinful Selfbot V0.5 | BOT INFO\n"
        "───────────────────────────\n"
        "Owner:          Rxmours\n"
        f"Commands:       {command_count}\n"
        f"Current prefix: {bot.command_prefix}\n"
        f"Uptime:         {uptime}\n"
        f"Ping:           {ping}ms\n"
        "Version:        v1.0\n"
    )

    await ctx.send(f"```{info_message}```", delete_after=30)
    
@bot.command(name='tools', aliases=['Tools'])
async def tools(ctx):
    await ctx.message.delete()
    tools = "```Tool Commands\nmassdm      - dms all friends\nmassunadd   - unadds all friends\nfriends     - shows friend count\nservers     - shows server list\npfp         - shows users pfp\nbanner      - shows (users banner\nreact       - sets a user react\nrotatereact - sets rotating reacts\nstopreact   - stops reacting to user\nafk         - sets afk status\nunafk       - stops afk status\nsnipe       - snipes a message\nping        - shows the bots ping\nspam        - spams a message```"
    await ctx.send(tools, delete_after=30)
  
@bot.command(name='nsfw', aliases=['NSFW'])
async def nsfw(ctx):
    await ctx.message.delete()
    nsfw = "```" "NSFW Commands\nhentai   -   sends any hentai\nuniform  -   sends uniform hentai\nselfies  -   sends selfie hentai\noppai    -   sends oppai hentai\necchi    -   sends ecchi hentai\npussy    -   sends pussy content\nboobs    -   sends boob content\nanal     -   sends anal content\nblowjob  -   sends blowjob content" "```"
    await ctx.send(nsfw, delete_after=30)

@bot.command(name='presence', aliases=['Presence'])
async def presence(ctx):
    await ctx.message.delete()
    status = "```Status commands\nrstatus       - rotates your status\nstopstatus    - clears your status\nrstream       - rotates streams\nstream        - sets a stream status\nplay          - sets a play status\nwatch         - sets a watch status\nlisten        - sets a listen status\nstopactivity  - stops your activity```"
    await ctx.send(status, delete_after=30)
    
@bot.command(name='server', aliases=['Server'])
async def server(ctx):
    await ctx.message.delete()
    server = "```Mass Server Commands\nmasskick          - kicks everyone\nmassban           - bans everyone\nmassunban         - unbans everyone\nmassroledelete    - deletes roles\nmasschanneldelete - deletes channels```"
    await ctx.send(server, delete_after=30)
    
@bot.command(name='fun', aliases=['Fun'])
async def fun(ctx):
    await ctx.message.delete()
    fun = "```Fun Commands\ncum         -   cumming\n9/11        -   plane crash\ndick        -   show users dick size\ngay         -   shows users %gay\nswat        -   swat someone\nesex        -   esex someone\nhack        -   hack someone\npack        -   rapid insults\nphc         -   pornhub comment\nnitro       -   generates nitro```"
    await ctx.send(fun, delete_after=30)
        
   
@bot.command(name='pack', help='throws random insults on mentioned user')
async def pack(ctx, user_mention=None):
    await ctx.message.delete()
    if user_mention is None:
        await ctx.send('```[Invalid]: mention a user```')
        return

    match = re.match(r'<@!?(\d+)>', user_mention)
    if not match:
        await ctx.send('```[Invalid]: invalid mention format```')
        return

    user_id = int(match.group(1))
    try:
        user = ctx.message.mentions[0]
        insults = [
        "SHUT THE FUCKUP YOU NASTY NIGGA ", "UR MY BITCH",
        "LOL WHY THIS NO NAME TALKING SM", "SHUT YO LAME ASS UP NIGGA",
        "DONT TALK", "DORK ASS CUNT", "BLA BLA BLA GTFO NIGGA",
        "SHUT THE FUCK UP YOU NASTY BITCH YOUR MY SON I RUN YOU FAT ASS WHORE GO KYS DUMB ASS FAGGG LMFOAOAOO",
        "UR MY BITCH", "DUMB ASS NIGGA", "?", "UR MY WHORE",
        "NIGGA GETTING SMOKED:rofl:", "NIGGA U DIED TO ME",
        "I NUTTED ON YO MOTHER AND CUMMED INSIDE HER AND U WAS BORN SON",
        "UR A NERD", "🤓", "YAPPER:rofl:", "NIGGA FOLDED TO ME",
        "PIPE THE FUCK DOWN", "I OWN U SON", "YOUR SLOW ASFUCK BITCH",
        "UR MY DOG", "LMFAO",
        "I DONT KNOW U, NO ONE KNOWS YOU UNKNOWN ASS NIGGA",
        "FAT ASS CUNT ", "NIGGA TRIED STEPPING",
        "HOW DID U GET HOED LIKE THAT", "FAT ASS PIG LMFAO", "DONT FOLD",
        "SHUT THE FUCK UP", "TRY STEPPING AGAIN", "UR A BITCH",
        "DUMB ASS NIGGA", "YOU GOT IN HERE TO GET FUCKED BY ME BITCHASS NIGGA",
        "SHUT THE FUCKUP YOU NASTY NIGGA ", "UR MY BITCH", "LOL",
        "SHUT YO LAME ASS UP NIGGA", "DONT TALK", "DORK ASS CUNT",
        "BLA BLA BLA GTFO NIGGA",
        "SHUT THE FUCK UP YOU NASTY BITCH YOUR MY SON I RUN YOU FAT ASS WHORE GO KYS DUMB ASS FAGGG LMFAO",
        "UR MY BITCH", "DUMB ASS NIGGA", "?", "UR MY WHORE",
        "NIGGA GETTING SMOKED:rofl:", "NIGGA SMD", "GAY ASS FAG:skull:",
        "I OWN YO MOTHER", "🤓", "YAPPER:laughing:", "NIGGA STOP THIS YAP",
        "LMAOFAOO WHY YOU YAPPING", "I OWN U", "SON",
        "YOUR GETTING SONNED LMFAOO", "🤣", "GAY ASS BITCH", "FAT FUCK",
        "DONT TALK BACK YOU LOSIN", "IMAGINE BEING YOU (DONT WANNA IMAGINE)",
        "R U GONNA LET DAT SLIDE ASSHOLE?",
        "LMAOOO YOUR GETTING SMOKED REAL HARD", "DONT TYPE PUSSY", "YAP?",
        "MY WHORE", "OK BITCH", "STFU ASSHOLE"
    ]
    except:
        await ctx.send('```[Error]: Could not fetch user```')
        return

    while not stop_event.is_set():
        try:
            msg = f'# {user.mention}' if not insults else f'# {user.mention} {random.choice(insults)}'
            await ctx.send(msg)
            await asyncio.sleep(0.1)
        except Exception as e:
            print(f'Error: {e}')
            await asyncio.sleep(2)

@bot.command(name='stoppack', help='```stops the pack command```')
async def stoppack(ctx):
    await ctx.message.delete()
    stop_event.set()
    await ctx.send('```Stopping the pack command...```')

@bot.command(aliases=["twitch"])
async def stream(ctx, *, message=None):
    await ctx.message.delete()
    if message is None:
        await ctx.send(
            f'[invalid]: bro this is the command: {bot.command_prefix}stream <message>'
        )
        return
    stream = discord.Streaming(name=message, url=stream_url)
    await bot.change_presence(activity=stream)
    await ctx.send(f"```now streaming: {message}```")


@bot.command(aliases=["rotatestream"])
async def rstream(ctx, *, statuses=None):
    global rotating_status
    await ctx.message.delete()

    if not statuses:
        await ctx.send("```Please provide at least one status to rotate, separated by commas.```")
        return

    status_texts = [text.strip() for text in statuses.split(",") if text.strip()]

    if not status_texts:
        await ctx.send(f"```[Invalid] Use: {bot.command_prefix}rotatestream status1, status2, status3```")
        return

    rotating_status = True
    await ctx.send(f"```Rotating statuses: {', '.join(status_texts)} every 5 seconds.```")

    while rotating_status:
        for text in status_texts:
            if not rotating_status:
                break
            await bot.change_presence(activity=discord.Streaming(name=text, url="https://twitch.tv/discord"))
            await asyncio.sleep(5)

@bot.command(aliases=["cancelstream", "stopstream"])
async def endstream(ctx):
    await ctx.message.delete()
    await bot.change_presence(activity=None)
    await ctx.send("```streaming status cleared```")


@bot.command()
async def test(ctx):
    await ctx.message.delete()
    await ctx.send(
        f"```@{bot.user.name} test complete, Type {bot.command_prefix}help to preview all the commands.```"
    )
    
@bot.command()
async def start(ctx):
    await ctx.message.delete()
    message = await ctx.send("```[Currently] attempting to hack account```")
    await asyncio.sleep(3)
    await message.edit(content= "```3```")
    await asyncio.sleep(0.35)
    await message.edit(content="```3.```")
    await asyncio.sleep(0.35)
    await message.edit(content="```3..```")
    await asyncio.sleep(0.35)
    await message.edit(content="```3...```")
    await asyncio.sleep(0.35)
    await message.edit(content="```3... 2```")
    await asyncio.sleep(0.35)
    await message.edit(content="```3... 2.```")
    await asyncio.sleep(0.35)
    await message.edit(content="```3... 2..```")
    await asyncio.sleep(0.35)
    await message.edit(content="```3... 2...```")
    await asyncio.sleep(0.35)
    await message.edit(content="```3... 2... 1```")
    await asyncio.sleep(0.35)
    await message.edit(content="```3... 2... 1.```")
    await asyncio.sleep(0.35)
    await message.edit(content="```3... 2... 1..```")
    await asyncio.sleep(0.35)
    await message.edit(content="```3... 2... 1...```")
    await asyncio.sleep(0.5)
    await message.edit(content=f"```[Success] @{bot.user.name} bot active, Type {bot.command_prefix}menu to preview all catagories```")
    

@bot.command()
async def nitro(ctx, amount: int = None):
    await ctx.message.delete()
    if amount is None:
        await ctx.send(
            f'[Invalid]: dawg Its {bot.command_prefix}nitro <amount>')
        return
    for _ in range(amount):
        code = ''.join(
            random.choices(string.ascii_letters + string.digits, k=16))
        await ctx.send(f'https://discord.gift/{code}')
        await asyncio.sleep(0.50)


@bot.command()
async def dick(ctx, *, user: discord.Member = None):
    await ctx.message.delete()
    if user is None:
        user = member.name
    size = random.randint(1, 15)
    dong = ""
    for _i in range(0, size):
        dong += "="
    await ctx.send(f"```{user}'s Dick size\n8{dong}D```")

@bot.command() 
async def gay(ctx, member: discord.Member = None):
    await ctx.message.delete()
    if member is None:
        await ctx.send("```[Error] failed to mention a user```")
        return

    gay_percent = random.randint(1, 100)
    response = f"```{member.name} is {gay_percent}% gay```"
    await ctx.send(response)


@bot.command(aliases=['qpurge', 'qc', 'quickclear', 'qclear'])
async def quickpurge(ctx, amount: int = None):
    await ctx.message.delete()
    if amount is None:
        await ctx.send(
            f'```[invalid]: Command: {bot.command_prefix}purge <amount>```')
        return
    async for message in ctx.message.channel.history(limit=amount).filter(
            lambda m: m.author == bot.user).map(lambda m: m):
        try:
            await message.delete()
            await asyncio.sleep(0.3)
        except:
            pass


@bot.command(aliases=['clear', 'c'])
async def purge(ctx, amount: int = None):
    await ctx.message.delete()

    if amount is None:
        await ctx.send(f'```[invalid]: Command: {bot.command_prefix}purge <amount>```')
        return

    async def purge_messages():
        deleted_count = 0

        try:
            async for message in ctx.channel.history(limit=amount):
                if message.author != bot.user:
                    continue
                try:
                    await message.delete()
                    deleted_count += 1
                    print(f"[console] Deleted {deleted_count}/{amount} messages...")
                    await asyncio.sleep(1)
                except:
                    pass
            print(f"[console] Finished: Deleted {deleted_count} messages.")
        except asyncio.CancelledError:
            print("[console] Purge operation was cancelled.")
        finally:
            purge_tasks.pop(ctx.channel.id, None)

    if ctx.channel.id in purge_tasks:
        purge_tasks[ctx.channel.id].cancel()

    task = asyncio.create_task(purge_messages())
    purge_tasks[ctx.channel.id] = task

@bot.command(aliases=['cstop', 'stoppurge', 'purgestop', 'pstop', 'stopc'])
async def stopclear(ctx):
    await ctx.message.delete()
    task = purge_tasks.get(ctx.channel.id)
    if task and not task.done():
        task.cancel()
        await ctx.send("```[info]: Purge stopped```")
    else:
        await ctx.send("```[info]: No active purge task to stop```")

@bot.command(aliases=['watch'])
async def watching(ctx, *, message=None):
    await ctx.message.delete()
    if message is None:
        await ctx.send(
            f'```[invalid]: Command: {bot.command_prefix}watch <message>```')
        return
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, name=message))
    await ctx.send(f'```watching status set to: {message}```')


@bot.command(aliases=['listen'])
async def listening(ctx, *, message=None):
    await ctx.message.delete()
    if message is None:
        await ctx.send(
            f'```[invalid]: Command: {bot.command_prefix}listening <message>```')
        return
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, name=message))
    await ctx.send(f'```listening status set to: {message}```')


@bot.command(aliases=['play'])
async def playing(ctx, *, message=None):
    await ctx.message.delete()
    if message is None:
        await ctx.send(
            f'```[invalid>: Command: {bot.command_prefix}playing <message>```')
        return
    game = discord.Game(name=message)
    await bot.change_presence(activity=game)
    await ctx.send(f'```playing status set to: {message}')

@bot.command()
async def gcnuke(ctx, user: discord.Member = None):
    await ctx.message.delete()
    if user is None:
        await ctx.send(f'```[Invalid]: Command: {bot.command_prefix}gctrap <user>```'
                       )
        return
    count = 0
    while True:
        count += 1
        await ctx.channel.edit(name=f"{user.display_name} got owned {count}")
        await asyncio.sleep(0.50)


@bot.command(aliases=["av", "pfp"])
async def avatar(ctx, member: discord.Member = None):
    await ctx.message.delete()
    if member is None:
        member = ctx.author

    avatar_url = member.avatar_url
    await ctx.send(f"```{member.display_name}'s avatar:```\n[avatar]({avatar_url})")


@bot.command(name="banner")
async def banner(ctx, user: discord.User):
    await ctx.message.delete()
    headers = {
        "Authorization": bot.http.token,
        "Content-Type": "application/json"
    }
    
    url = f"https://discord.com/api/v9/users/{user.id}/profile"
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            banner_hash = data.get("user", {}).get("banner")
            
            if banner_hash:
                banner_format = "gif" if banner_hash.startswith("a_") else "png"
                banner_url = f"https://cdn.discordapp.com/banners/{user.id}/{banner_hash}.{banner_format}?size=1024"
                await ctx.send(f"```{user.display_name}'s banner:```\n[banner]({banner_url})")
            else:
                await ctx.send(f"```{user.display_name} does not have a banner set```")
        else:
            await ctx.send(f"Failed to retrieve banner: {response.status_code} - {response.text}")
    
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
        
        
@bot.command(name='massgc')
async def massgc(ctx, *, message=None):
    await ctx.message.delete()
    if message is None:
        await ctx.send(
            f'[Invalid]: Nuh, Command: {bot.command_prefix}massgc <message>')
        return
    await ctx.send('Sending message to all group chats...')
    for channel in bot.private_channels:
        if isinstance(channel, discord.GroupChannel):
            try:
                await channel.send(message)
                print(f'Message sent to {channel.name}')
            except discord.Forbidden:
                print(f'Forbidden to send message to {channel.name}')
            except discord.HTTPException as e:
                print(f'Error sending message to {channel.name}: {e.text}')
    await ctx.send('Message sent to all group chats!')
    await asyncio.sleep(4)


@bot.command(aliases=['mdm'])
async def massdm(ctx, *, message=None):
    await ctx.message.delete()
    if message is None:
        await ctx.send(f'```[Invalid]: It\'s, {bot.command_prefix}mdm <message>```')
        return
    for friend in bot.user.friends:
        if friend.id in whitelisted_ids:
            print(f"Skipped {friend.name}#{friend.discriminator} (whitelisted)")
            continue
        try:
            await friend.send(message)
            print(f"Message sent to {friend.name}#{friend.discriminator}")
        except discord.Forbidden:
            print(f"Failed to send message to {friend.name}#{friend.discriminator} (blocked or dms are off)")
        except Exception as e:
            print(f"Error sending message to {friend.name}#{friend.discriminator}: {e}")
        await asyncio.sleep(7.5)


@bot.command(aliases=['9/11'])
async def nineeleven(ctx):
    await ctx.message.delete()
    invis = ""  # char(173)
    message = await ctx.send(f'''
{invis}:man_wearing_turban::airplane:    :office:           
''')
    await asyncio.sleep(0.5)
    await message.edit(content=f'''
{invis} :man_wearing_turban::airplane:   :office:           
''')
    await asyncio.sleep(0.5)
    await message.edit(content=f'''
{invis}  :man_wearing_turban::airplane:  :office:           
''')
    await asyncio.sleep(0.5)
    await message.edit(content=f'''
{invis}   :man_wearing_turban::airplane: :office:           
''')
    await asyncio.sleep(0.5)
    await message.edit(content=f'''
{invis}    :man_wearing_turban::airplane::office:           
''')
    await asyncio.sleep(0.5)
    await message.edit(content='''
        :boom::boom::boom:    
        ''')


@bot.command()
async def cum(ctx):
    await ctx.message.delete()
    message = await ctx.send('''
            :ok_hand:            :smile:
   :eggplant: :zzz: :necktie: :eggplant: 
                   :oil:     :nose:
                 :zap: 8=:punch:=D 
             :trumpet:      :eggplant:''')
    await asyncio.sleep(0.5)
    await message.edit(content='''
                      :ok_hand:            :smiley:
   :eggplant: :zzz: :necktie: :eggplant: 
                   :oil:     :nose:
                 :zap: 8==:punch:D 
             :trumpet:      :eggplant:  
     ''')
    await asyncio.sleep(0.5)
    await message.edit(content='''
                      :ok_hand:            :grimacing:
   :eggplant: :zzz: :necktie: :eggplant: 
                   :oil:     :nose:
                 :zap: 8=:punch:=D 
             :trumpet:      :eggplant:  
     ''')
    await asyncio.sleep(0.5)
    await message.edit(content='''
                      :ok_hand:            :persevere:
   :eggplant: :zzz: :necktie: :eggplant: 
                   :oil:     :nose:
                 :zap: 8==:punch:D 
             :trumpet:      :eggplant:   
     ''')
    await asyncio.sleep(0.5)
    await message.edit(content='''
                      :ok_hand:            :confounded:
   :eggplant: :zzz: :necktie: :eggplant: 
                   :oil:     :nose:
                 :zap: 8=:punch:=D 
             :trumpet:      :eggplant: 
     ''')
    await asyncio.sleep(0.5)
    await message.edit(content='''
                       :ok_hand:            :tired_face:
   :eggplant: :zzz: :necktie: :eggplant: 
                   :oil:     :nose:
                 :zap: 8==:punch:D 
             :trumpet:      :eggplant:    
             ''')
    await asyncio.sleep(0.5)
    await message.edit(contnet='''
                       :ok_hand:            :weary:
   :eggplant: :zzz: :necktie: :eggplant: 
                   :oil:     :nose:
                 :zap: 8=:punch:= D:sweat_drops:
             :trumpet:      :eggplant:        
     ''')
    await asyncio.sleep(0.5)
    await message.edit(content='''
                       :ok_hand:            :dizzy_face:
   :eggplant: :zzz: :necktie: :eggplant: 
                   :oil:     :nose:
                 :zap: 8==:punch:D :sweat_drops:
             :trumpet:      :eggplant:                 :sweat_drops:
     ''')
    await asyncio.sleep(0.5)
    await message.edit(content='''
                       :ok_hand:            :drooling_face:
   :eggplant: :zzz: :necktie: :eggplant: 
                   :oil:     :nose:
                 :zap: 8==:punch:D :sweat_drops:
             :trumpet:      :eggplant:                 :sweat_drops:
     ''')


@bot.command()
async def hack(ctx, user: discord.Member = None):
    await ctx.message.delete()
    gender = ["Male", "Female", "Trans", "Other", "Retard"]
    age = str(random.randrange(10, 25))
    height = [
        '4\'6\"', '4\'7\"', '4\'8\"', '4\'9\"', '4\'10\"', '4\'11\"', '5\'0\"',
        '5\'1\"', '5\'2\"', '5\'3\"', '5\'4\"', '5\'5\"', '5\'6\"', '5\'7\"',
        '5\'8\"', '5\'9\"', '5\'10\"', '5\'11\"', '6\'0\"', '6\'1\"', '6\'2\"',
        '6\'3\"', '6\'4\"', '6\'5\"', '6\'6\"', '6\'7\"', '6\'8\"', '6\'9\"',
        '6\'10\"', '6\'11\"'
    ]
    weight = str(random.randrange(60, 300))
    hair_color = ["Black", "Brown", "Blonde", "White", "Gray", "Red"]
    skin_color = ["White", "Pale", "Brown", "Black", "Light-Skin"]
    religion = [
        "Christian", "Muslim", "Atheist", "Hindu", "Buddhist", "Jewish"
    ]
    sexuality = [
        "Straight", "Gay", "Homo", "Bi", "Bi-Sexual", "Lesbian", "Pansexual"
    ]
    education = [
        "High School", "College", "Middle School", "Elementary School",
        "Pre School", "Retard never went to school LOL"
    ]
    ethnicity = [
        "White", "African American", "Asian", "Latino", "Latina", "American",
        "Mexican", "Korean", "Chinese", "Arab", "Italian", "Puerto Rican",
        "Non-Hispanic", "Russian", "Canadian", "European", "Indian"
    ]
    occupation = [
        "Retard has no job LOL", "Certified discord retard", "Janitor",
        "Police Officer", "Teacher", "Cashier", "Clerk", "Waiter", "Waitress",
        "Grocery Bagger", "Retailer", "Sales-Person", "Artist", "Singer",
        "Rapper", "Trapper", "Discord Thug", "Gangster", "Discord Packer",
        "Mechanic", "Carpenter", "Electrician", "Lawyer", "Doctor",
        "Programmer", "Software Engineer", "Scientist"
    ]
    salary = [
        "Retard makes no money LOL", "$" + str(random.randrange(0, 1000)),
        '<$50,000', '<$75,000', "$100,000", "$125,000", "$150,000", "$175,000",
        "$200,000+"
    ]
    location = [
        "Retard lives in his mom's basement LOL", "America", "United States",
        "Europe", "Poland", "Mexico", "Russia", "Pakistan", "India",
        "Some random third world country", "Canada", "Alabama", "Alaska",
        "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
        "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois",
        "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine",
        "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
        "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
        "New Jersey", "New Mexico", "New York", "North Carolina",
        "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
        "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas",
        "Utah", "Vermont", "Virginia", "Washington", "West Virginia",
        "Wisconsin", "Wyoming"
    ]
    email = [
        "@gmail.com", "@yahoo.com", "@hotmail.com", "@outlook.com",
        "@protonmail.com", "@disposablemail.com", "@aol.com", "@edu.com",
        "@icloud.com", "@gmx.net", "@yandex.com"
    ]
    dob = f'{random.randrange(1, 13)}/{random.randrange(1, 32)}/{random.randrange(1950, 2021)}'
    phone = f'({random.randrange(0, 10)}{random.randrange(0, 10)}{random.randrange(0, 10)})-{random.randrange(0, 10)}{random.randrange(0, 10)}{random.randrange(0, 10)}-{random.randrange(0, 10)}{random.randrange(0, 10)}{random.randrange(0, 10)}{random.randrange(0, 10)}'
    if user is None:
        user = ctx.author
        password = [
            'password', '123', 'mypasswordispassword', user.name + "iscool123",
            user.name + "isdaddy", "daddy" + user.name, "ilovediscord",
            "i<3discord", "furryporn456", "secret", "123456789", "apple49",
            "redskins32", "princess", "dragon", "password1", "1q2w3e4r",
            "ilovefurries"
        ]
        message = await ctx.send(f"`Hacking {user}...\n`")
        await asyncio.sleep(1)
        await message.edit(
            content=f"`Hacking {user}...\nHacking into the mainframe...\n`")
        await asyncio.sleep(1)
        await message.edit(
            content=
            f"`Hacking {user}...\nHacking into the mainframe...\nCaching data...`"
        )
        await asyncio.sleep(1)
        await message.edit(
            content=
            f"`Hacking {user}...\nHacking into the mainframe...\nCaching data...\nCracking SSN information...\n`"
        )
        await asyncio.sleep(1)
        await message.edit(
            content=
            f"`Hacking {user}...\nHacking into the mainframe...\nCaching data...\nCracking SSN information...\nBruteforcing love life details...`"
        )
        await asyncio.sleep(1)
        await message.edit(
            content=
            f"`Hacking {user}...\nHacking into the mainframe...\nCaching data...\nCracking SSN information...\nBruteforcing love life details...\nFinalizing life-span dox details\n`"
        )
        await asyncio.sleep(1)
        await message.edit(
            content=
            f"```Successfully hacked {user}\nName: {random.choice(name)}\nGender: {random.choice(gender)}\nAge: {age}\nHeight: {random.choice(height)}\nWeight: {weight}\nHair Color: {random.choice(hair_color)}\nSkin Color: {random.choice(skin_color)}\nDOB: {dob}\nLocation: {random.choice(location)}\nPhone: {phone}\nE-Mail: {user.name + random.choice(email)}\nPasswords: {random.choices(password, k=3)}\nOccupation: {random.choice(occupation)}\nAnnual Salary: {random.choice(salary)}\nEthnicity: {random.choice(ethnicity)}\nReligion: {random.choice(religion)}\nSexuality: {random.choice(sexuality)}\nEducation: {random.choice(education)}```"
        )
    else:
        password = [
            'password', '123', 'mypasswordispassword', user.name + "iscool123",
            user.name + "isdaddy", "daddy" + user.name, "ilovediscord",
            "i<3discord", "furryporn456", "secret", "123456789", "apple49",
            "redskins32", "princess", "dragon", "password1", "1q2w3e4r",
            "ilovefurries"
        ]
        message = await ctx.send(f"`Hacking {user}...\n`")
        await asyncio.sleep(1)
        await message.edit(
            content=f"`Hacking {user}...\nHacking into the mainframe...\n`")
        await asyncio.sleep(1)
        await message.edit(
            content=
            f"`Hacking {user}...\nHacking into the mainframe...\nCaching data...`"
        )
        await asyncio.sleep(1)
        await message.edit(
            content=
            f"`Hacking {user}...\nHacking into the mainframe...\nCaching data...\nCracking SSN information...\n`"
        )
        await asyncio.sleep(1)
        await message.edit(
            content=
            f"`Hacking {user}...\nHacking into the mainframe...\nCaching data...\nCracking SSN information...\nBruteforcing love life details...`"
        )
        await asyncio.sleep(1)
        await message.edit(
            content=
            f"`Hacking {user}...\nHacking into the mainframe...\nCaching data...\nCracking SSN information...\nBruteforcing love life details...\nFinalizing life-span dox details\n`"
        )
        await asyncio.sleep(1)
        await message.edit(
            content=f"```Successfully hacked {user}\n"
            f"Name: {user.name}\n"
            f"Gender: {random.choice(gender)}\n"
            f"Age: {age}\n"
            f"Height: {random.choice(height)}\n"
            f"Weight: {weight}\n"
            f"Hair Color: {random.choice(hair_color)}\n"
            f"Skin Color: {random.choice(skin_color)}\n"
            f"DOB: {dob}\n"
            f"Location: {random.choice(location)}\n"
            f"Phone: {phone}\n"
            f"E-Mail: {user.name + random.choice(email)}\n"
            f"Passwords: {', '.join(random.choices(password, k=3))}\n"
            f"Occupation: {random.choice(occupation)}\n"
            f"Annual Salary: {random.choice(salary)}\n"
            f"Ethnicity: {random.choice(ethnicity)}\n"
            f"Religion: {random.choice(religion)}\n"
            f"Sexuality: {random.choice(sexuality)}\n"
            f"Education: {random.choice(education)}\n"
            "```")
            
@bot.command()
async def swat(ctx, user: discord.Member = None):
    await ctx.message.delete()
    if user is None:
        user = ctx.author

    location = ["1305 Tarragon Dr Flower Mound, Texas(TX), 75028", "28261 W Thome Rd Rock Falls, Illinois(IL), 61071", "1508 2nd St NW Bowman, North Dakota(ND), 58623", "60 Gertrude Rd Dalton, Massachusetts(MA), 01226",]
    
    await ctx.send(f"`swatting {user.name}...`")
    await asyncio.sleep(1)

    await ctx.send(f"Dispatcher: This is 9-1-1 what\'s your emergency")
    await asyncio.sleep(1)

    await ctx.send(f"{user.mention}: my name is {user.mention}. I'm scared, my parents were fighting and then I heard what sounded like a gunshot. . . ")
    await asyncio.sleep(1)
    
    await ctx.send(f"Dispatcher: okay calm down, get somewhere safe, and tell me where you live.")
    await asyncio.sleep(1)

    await ctx.send(f"{user.mention}: I- I live at {random.choice(location)}", delete_after=5)
    await asyncio.sleep(1)
    
    await ctx.send(f"Please send help fast...")
    await asyncio.sleep(1)

    await ctx.send(f"Dispatcher: A team will be coming shortly, remain safe until they arrive")
    await asyncio.sleep(1)


    await ctx.send(f"SWAT: starts breaking down {user.mention} door")
    await asyncio.sleep(1)

    await ctx.send(f"https://media.discordapp.net/attachments/1310177406732075101/1312274470504890421/b9b7b37cb0cf5e495d6512d30c56a4fb.gif?ex=674be656&is=674a94d6&hm=139874281c9b4d402eab13afd0669cd07505a18147aea95fa75277706ca32da5&=")
    await asyncio.sleep(1)
                        
    await ctx.send(f"SWAT: YOURE UNDER ARREST {user.mention}")
    await asyncio.sleep(1)

    await ctx.send(f"SWAT: *targets {user.mention}*")
    await asyncio.sleep(1)

    await ctx.send(f"{user.mention}: SAVE ME I NEED HELP \n")
    await asyncio.sleep(1)

    await ctx.send(f"SWAT: GET DOWN ON THE FLOOR {user.mention}")
    await asyncio.sleep(1)

    await ctx.send(f"{user.mention} I DIDNT DO ANYTHING \n")
    await asyncio.sleep(1)


    await ctx.send(f"SWAT: *locks up {user.mention}*")
    await asyncio.sleep(1)

    await ctx.send(f"`Successfully swatted {user.name}`")
    await asyncio.sleep(1)
  
            
@bot.command(name="phc", aliases=["phcomment", "pornhubcomment"])
async def phc(ctx, user: discord.User, *, comment: str):
    try:
        await ctx.message.delete()

        username = user.name
        user_avatar_url = str(user.avatar_url_as(format="png"))

        endpoint = (
            f"https://nekobot.xyz/api/imagegen?"
            f"type=phcomment&text={comment}&username={username}&image={user_avatar_url}"
        )

        response = requests.get(endpoint)
        res = response.json()

        if "message" in res and res["message"].startswith("http"):
            async with aiohttp.ClientSession() as session:
                async with session.get(res["message"]) as resp:
                    image = await resp.read()
                    with io.BytesIO(image) as file:
                        await ctx.send(file=discord.File(file, "phc.png"))
        else:
            await ctx.send("`Error: Image generation failed.`")

    except Exception as e:
        await ctx.send(f"`An error occurred: {str(e)}`")
            
@bot.command()
async def massban(ctx):
    await ctx.message.delete()

    await ctx.send("```[Starting] mass ban of all members...```", delete_after=5)
    
    try:
        await ctx.guild.chunk()
    except:
        pass
        
    members = [m for m in ctx.guild.members if m != ctx.guild.me]
    banned_count = 0
    
    async def ban_member(member):
        for attempt in range(3):  
            try:
                await member.ban(reason="get nuked lol")
                print(f"[Success] Banned {member.name} on attempt {attempt + 1}")
                return True
            except:
                if attempt < 2:  
                    print(f"[Error]Failed to ban {member.name}, attempt {attempt + 1}/3")
                    await asyncio.sleep(1)  
                else:
                    print(f"[Error] Failed to ban {member.name} after 3 attempts")
                    return False
    
    tasks = [ban_member(member) for member in members]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    banned_count = sum(1 for r in results if r is True)

    await ctx.send(f"```[Success] banned {banned_count} members.```")
    
@bot.command()
async def massunban(ctx):
    await ctx.message.delete()

    await ctx.send("```[Starting] mass unban of all banned users...```", delete_after=5)

    try:
        bans = await ctx.guild.bans()
    except Exception as e:
        await ctx.send(f"```[Error] Failed to fetch ban list: {e}```")
        return

    unbanned_count = 0

    async def unban_user(ban_entry):
        user = ban_entry.user
        for attempt in range(3):
            try:
                await ctx.guild.unban(user, reason="Mass unban initiated")
                print(f"[Success] Unbanned {user.name} on attempt {attempt + 1}")
                return True
            except Exception as e:
                if attempt < 2:
                    print(f"[Error] Failed to unban {user.name}, attempt {attempt + 1}/3: {e}")
                    await asyncio.sleep(1)
                else:
                    print(f"[Error] Failed to unban {user.name} after 3 attempts")
                    return False

    tasks = [unban_user(ban) for ban in bans]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    unbanned_count = sum(1 for r in results if r is True)

    await ctx.send(f"```[Success] unbanned {unbanned_count} users.```")

@bot.command()
async def masskick(ctx):
    await ctx.message.delete()

    await ctx.send("```[Starting] mass kick of all members...```", delete_after=5)
    
    try:
        await ctx.guild.chunk()
    except:
        pass
        
    members = [m for m in ctx.guild.members if m != ctx.guild.me]
    kicked_count = 0
    
    async def kick_member(member):
        for attempt in range(3):  
            try:
                await member.kick(reason="get kicked lol")
                print(f"[Success] Kicked {member.name} on attempt {attempt + 1}")
                return True
            except:
                if attempt < 2:  
                    print(f"[Error]Failed to kick {member.name}, attempt {attempt + 1}/3")
                    await asyncio.sleep(1)  
                else:
                    print(f"[Error]Failed to kick {member.name} after 3 attempts")
                    return False
    
    tasks = [kick_member(member) for member in members]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    kicked_count = sum(1 for r in results if r is True)

    await ctx.send(f"```[Success] kicked {kicked_count} members```")

@bot.command()
async def massroledelete(ctx):
    await ctx.message.delete()

    await ctx.send("```[Starting] mass role delete....```")

    deleted = 0
    
    for role in ctx.guild.roles:
        if role.name != "@everyone" and not role.managed and role < ctx.guild.me.top_role:
            try:
                await role.delete(reason="Mass role deletion")
                deleted += 1
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass
    
    await ctx.send(f"```[Success] deleted {deleted} roles```")
    
@bot.command()
async def masschanneldelete(ctx):
    await ctx.message.delete()
    
    if ctx.author.id != bot.user.id:
        return

    await ctx.send("```[Starting] mass channel delete...```")

    print(f"Deleting all channels in: {ctx.guild.name}")
    for channel in ctx.guild.channels:
        try:
            await channel.delete()
            print(f"Deleted: {channel.name}")
        except Exception as e:
            print(f"Failed to delete {channel.name}: {e}")
    
    await ctx.send("```[Success] deleted all channels```")
    
import asyncio

@bot.command()
async def masschannelcreate(ctx):
    await ctx.message.delete()

    if ctx.author.id != bot.user.id:
        return

    await ctx.send("```[Starting] mass channel creation...```")

    for i in range(50):
        try:
            await ctx.guild.create_text_channel("test")
            print(f"Created channel {i+1}/50")
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Failed to create channel {i+1}: {e}")
            await asyncio.sleep(5)

    await ctx.send("```[Success] created 50 channels```")()
    
import asyncio

@bot.command()
async def nuke(ctx):
    await ctx.message.delete()

    if ctx.author.id != bot.user.id:
        return

    await ctx.send("```[Starting] nuke...```")

    for channel in list(ctx.guild.channels):
        try:
            await channel.delete()
            print(f"[Success] Deleted: {channel.name}")
            await asyncio.sleep(0)
        except Exception as e:
            print(f"[Error] Failed to delete {channel.name}: {e}")
            await asyncio.sleep(5)

    created_channels = []
    for i in range(15):
        try:
            channel = await ctx.guild.create_text_channel("RUN BY SWATTINGZ")
            created_channels.append(channel)
            print(f"[Success] Created channel {i+1}/15")
            await asyncio.sleep(0.25)
        except Exception as e:
            print(f"[Error] Failed to create channel {i+1}: {e}")
            await asyncio.sleep(5)

    for channel in created_channels:
        for i in range(25):
            try:
                await channel.send("# @everyone SWATTINGZ RUNS U")
                print(f"[Success] Sent message {i+1}/10 in {channel.name}")
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[Error] Failed to send message in {channel.name}: {e}")
                await asyncio.sleep(5)
    
@bot.command()
async def afk(ctx, *, reason="AFK"):
    await ctx.message.delete()
    afk_users[ctx.author.id] = reason
    await ctx.send(f"```{ctx.author.name} is now afk: {reason}```", delete_after=3)

@bot.command()
async def unafk(ctx):
    await ctx.message.delete()
    if ctx.author.id in afk_users:
        del afk_users[ctx.author.id]
        await ctx.send(f"```{ctx.author.name} is no longer afk```", delete_after=3)
    else:
        await ctx.send("```You're not afk.```", delete_after=3)
    
@bot.command(name='rotatestatus', aliases=["rstatus"])
async def rotate_status(ctx, *, statuses: str):
    global status_rotation_active, current_status, current_emoji
    await ctx.message.delete()

    status_list = [s.strip() for s in statuses.split(',') if s.strip()]

    if not status_list:
        await ctx.send("```Please separate statuses with commas```", delete_after=5)
        return

    current_index = 0
    status_rotation_active = True

    async def update_status_emoji():
        json_data = {
            'custom_status': {
                'text': current_status,
                'emoji_name': current_emoji
            }
        }

        custom_emoji_match = re.match(r'<a?:(\w+):(\d+)>', current_emoji)
        if custom_emoji_match:
            name, emoji_id = custom_emoji_match.groups()
            json_data['custom_status']['emoji_name'] = name
            json_data['custom_status']['emoji_id'] = emoji_id
        else:
            json_data['custom_status']['emoji_name'] = current_emoji

        async with aiohttp.ClientSession() as session:
            try:
                async with session.patch(
                    'https://discord.com/api/v9/users/@me/settings',
                    headers={
                        'Authorization': token,
                        'Content-Type': 'application/json'
                    },
                    json=json_data
                ) as resp:
                    await resp.read()
            except Exception as e:
                print(f"Failed to update status: {e}")

    await ctx.send("```Status rotation started```", delete_after=3)

    try:
        while status_rotation_active:
            current_status = status_list[current_index]
            await update_status_emoji()
            await asyncio.sleep(4)
            current_index = (current_index + 1) % len(status_list)
    finally:
        current_status = ""
        await update_status_emoji()
        status_rotation_active = False


@bot.command(name='stopstatus')
async def stopstatus(ctx):
    global status_rotation_active
    await ctx.message.delete()
    status_rotation_active = False
    await ctx.send("```Status rotation stopped```", delete_after=3)
        
@bot.command(name='massunadd')
async def massunadd(ctx):

    try:
        
        friends = bot.user.friends

        if not friends:
            await ctx.send("```[Error] You have no friends to unadd```")
            return

        await ctx.send(f"```Starting to unfriend {len(friends)} users...```")

        
        for friend in friends:
            await friend.remove_friend() 
            await asyncio.sleep(1)  
        
        await ctx.send("```Successfully unfriended all users.```")

    except Exception as e:
        await ctx.send(f"[Error] {str(e)}")
        
@bot.command(name='leaveservers')
async def massleave(ctx):
    try:
        guilds = bot.guilds

        if not guilds:
            await ctx.send("```The bot is not in any servers.```")
            return

        await ctx.send(f"```Leaving {len(guilds)} servers...```")

        for guild in guilds:
            await guild.leave()
            await asyncio.sleep(1)

        await ctx.send("```Successfully left all servers.```")

    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")
        
@bot.command()
async def servers(ctx):
    await ctx.message.delete()
    server_names = [guild.name for guild in bot.guilds]
    
 
    if server_names:
        server_count = len(server_names)
        server_list_message = "\n> ".join(server_names)  
        await ctx.send(f"```You are in {server_count} servers:\n> {server_list_message}```")
    else:
        await ctx.send("```You are not in any servers.```")


@bot.command()
async def friendslist(ctx):
    await ctx.message.delete()
    friends = ctx.bot.user.friends 
    friend_names = [friend.name for friend in friends]

    if friend_names:
        friend_count = len(friend_names)
        friend_list_message = "\n> ".join(friend_names)
        await ctx.send(f"```You have {friend_count} friends:\n> {friend_list_message}```")
    else:
        await ctx.send("```You have no friends added.```")
        
@bot.command()
async def friends(ctx):
    await ctx.message.delete()
    friends = ctx.bot.user.friends 
    friend_names = [friend.name for friend in friends]

    if friend_names:
        friend_count = len(friend_names)
        friend_list_message = "\n> ".join(friend_names)
        await ctx.send(f"```You have {friend_count} friends```")
    else:
        await ctx.send("```You have no friends added.```")


@bot.command(name="esex", help="Fucks with the mentioned user", usage="@user or user ID")
async def esex(ctx, *, user_input=None):
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

    if not user_input:
        await ctx.send("```You need to mention someone or provide a user ID```")
        return

    user = None

    if ctx.message.mentions:
        user = ctx.message.mentions[0]
    else:
        
        cleaned_input = user_input.strip().replace("<", "").replace(">", "").replace("@", "").replace("!", "")
        try:
            user_id = int(cleaned_input)
            user = await bot.fetch_user(user_id)
        except:
            await ctx.send("```couldn't find that user```")
            return

    author = ctx.author
    await ctx.send(f"{user.mention if isinstance(user, discord.User) else user.mention}")
    await asyncio.sleep(0.1)
    await ctx.send("https://cdn.discordapp.com/attachments/1337167039722160189/1337827104342933544/attachment.gif")
        
@bot.command()
async def serverdm(ctx, *, message):
    await ctx.message.delete()
    await ctx.send("`starting mass server dm...`")
    guild = ctx.guild
    count = 0
    failed = 0

    for member in guild.members:
        if member.bot:
            continue
        try:
            await member.send(message)
            count += 1
            await asyncio.sleep(7) 
        except discord.Forbidden:
            failed += 1  
        except discord.HTTPException:
            failed += 1 

    await ctx.send(f"Sent message to {count} members. Failed to dm {failed} users.`")
    
@bot.command(name="quickdelete", aliases=["qd", "delete"])
async def quickdelete(ctx):
    await ctx.message.delete()

@bot.command(aliases=['firstmsg'])
async def firstmessage(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel  
    try:

        first_message = await channel.history(limit=1, oldest_first=True).flatten()
        if first_message:
            msg = first_message[0]  
            response = f"```first message here```"

            await msg.reply(response)  
        else:
            await ctx.send("```No messages found in this channel.```")
    except Exception as e:
        await ctx.send(f"```Error: {str(e)}```")
        
@bot.command(hidden=True)
async def crash(ctx):
    await ctx.message.delete()
    message = await ctx.send("```Crashing selfbot.exe```")
    await asyncio.sleep(0.5)
    await message.edit(content= "```3```")
    await asyncio.sleep(0.25)
    await message.edit(content="```3.```")
    await asyncio.sleep(0.25)
    await message.edit(content="```3..```")
    await asyncio.sleep(0.25)
    await message.edit(content="```3...```")
    await asyncio.sleep(0.25)
    await message.edit(content="```3... 2```")
    await asyncio.sleep(0.25)
    await message.edit(content="```3... 2.```")
    await asyncio.sleep(0.25)
    await message.edit(content="```3... 2..```")
    await asyncio.sleep(0.25)
    await message.edit(content="```3... 2...```")
    await asyncio.sleep(0.25)
    await message.edit(content="```3... 2... 1```")
    await asyncio.sleep(0.25)
    await message.edit(content="```3... 2... 1.```")
    await asyncio.sleep(0.25)
    await message.edit(content="```3... 2... 1..```")
    await asyncio.sleep(0.25)
    await message.edit(content="```3... 2... 1...```")
    await asyncio.sleep(0.5)
    await message.edit(content="```[Success] Crashed selfbot.exe```")
    
    await bot.close()
    sys.exit(0)
    
@bot.command(hidden=True)
async def debug(ctx):
    await ctx.message.delete()
    message = await ctx.send("```[Currently] Attempting to debug selfbot```")
    await asyncio.sleep(0.5)
    await message.edit(content="```[Currently] Attempting to debug selfbot.```")
    await asyncio.sleep(0.5)
    await message.edit(content="```[Currently] Attempting to debug selfbot..```")
    await asyncio.sleep(0.5)
    await message.edit(content="```[Currently] Attempting to debug selfbot...```")
    await asyncio.sleep(0.5)
    await message.edit(content="```[Currently] Restarting selfbot```")
    await asyncio.sleep(2)
    await message.edit(content=f"```[Success] selfbot has been debugged```")
    os.execv(sys.executable, ['python'] + sys.argv)
    

@bot.command()
async def hush(ctx, user: discord.User):
    await ctx.message.delete()
    global target_user, hush_active
    if hush_active:
        await ctx.message.delete()
        await ctx.send("  ")
        return
    
    target_user = user
    hush_active = True
    
    await ctx.send(f"```Hush mode active```", delete_after=3)
    
    delete_future_messages.start(ctx)

@tasks.loop(seconds=0.0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001)  
async def delete_future_messages(ctx):
    global target_user
    if target_user:
        async for message in ctx.channel.history(limit=1):
            if message.author == target_user:
                try:
                    await message.delete()
                    print(f"Deleted future message from {target_user}: {message.content}")
                except discord.Forbidden:
                    print(f"Failed to delete future message from {target_user}")

@bot.command()
async def endhush(ctx):
    await ctx.message.delete()
    global hush_active
    if not hush_active:
        await ctx.send("")
        return
    
    hush_active = False
    delete_future_messages.stop()  
    await ctx.send("```Hush mode stopped``` ", delete_after=3)

@bot.command(name="hentai")
async def hentai(ctx, member: discord.Member = None):
    await ctx.message.delete()
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.waifu.im/search/?included_tags=hentai&is_nsfw=true') as response:
            if response.status == 200:
                data = await response.json()
                image_url = data['images'][0]['url']
                await ctx.send(f"[hentai]({image_url})")
            else:
                await ctx.send("```Failed to fetch image```")

@bot.command(name="ecchi")
async def ecchi(ctx, member: discord.Member = None):
    
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.waifu.im/search/?included_tags=ecchi&is_nsfw=true') as response:
            if response.status == 200:
                data = await response.json()
                image_url = data['images'][0]['url']
                await ctx.send(f"\n[ecchi]({image_url})")
            else:
                await ctx.send("```Failed to fetch image```")

@bot.command(name="uniform")
async def uniform(ctx, member: discord.Member = None):
    await ctx.message.delete()
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.waifu.im/search/?included_tags=uniform&is_nsfw=true') as response:
            if response.status == 200:
                data = await response.json()
                image_url = data['images'][0]['url']
                await ctx.send(f"[uniform]({image_url})")
            else:
                await ctx.send("```Failed to fetch image```")

@bot.command(name="maid")
async def maid(ctx, member: discord.Member = None):
    await ctx.message.delete()
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.waifu.im/search/?included_tags=maid&is_nsfw=true') as response:
            if response.status == 200:
                data = await response.json()
                image_url = data['images'][0]['url']
                await ctx.send(f"[maid]({image_url})")
            else:
                await ctx.send("```Failed to fetch image```")

@bot.command(name="oppai")
async def oppai(ctx, member: discord.Member = None):
    await ctx.message.delete()
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.waifu.im/search/?included_tags=oppai&is_nsfw=true') as response:
            if response.status == 200:
                data = await response.json()
                image_url = data['images'][0]['url']
                await ctx.send(f"[oppai]({image_url})")
            else:
                await ctx.send("```Failed to fetch image```")

@bot.command(name="selfies")
async def selfies(ctx, member: discord.Member = None):
    await ctx.message.delete()
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.waifu.im/search/?included_tags=selfies&is_nsfw=true') as response:
            if response.status == 200:
                data = await response.json()
                image_url = data['images'][0]['url']
                await ctx.send(f"[selfies]({image_url})")
            else:
                await ctx.send("```Failed to fetch image```")

@bot.command(aliases=["vagina"])
async def pussy(ctx):
    await ctx.message.delete()
    async with aiohttp.ClientSession() as session:
        async with session.get("https://nekobot.xyz/api/image?type=pussy") as resp:
            if resp.status != 200:
                return await ctx.send("```[Invalid]: Failed to fetch image```")
            data = await resp.json()
            if "message" not in data:
                return await ctx.send(f"Unexpected response: {data}")

            image_url = data["message"]

        async with session.get(image_url) as img_resp:
            if img_resp.status != 200:
                return await ctx.send("```Failed to load image```")
            image = await img_resp.read()

    with io.BytesIO(image) as file:
        await ctx.send(file=discord.File(file, "pussy.gif"))


@bot.command()
async def blowjob(ctx):
    await ctx.message.delete()
    async with aiohttp.ClientSession() as session:
        async with session.get("https://nekobot.xyz/api/image?type=blowjob") as resp:
            data = await resp.json()
            if "message" not in data:
                return await ctx.send("```Failed to fetch image```")
            image_url = data["message"]

        async with session.get(image_url) as img_resp:
            image = await img_resp.read()

    with io.BytesIO(image) as file:
        await ctx.send(file=discord.File(file, "blowjob.gif"))
        
@bot.command()
async def anal(ctx):
    await ctx.message.delete()
    async with aiohttp.ClientSession() as session:
        async with session.get("https://nekobot.xyz/api/image?type=anal") as resp:
            data = await resp.json()
            if "message" not in data:
                return await ctx.send("```Failed to fetch image```")
            image_url = data["message"]

        async with session.get(image_url) as img_resp:
            image = await img_resp.read()

    with io.BytesIO(image) as file:
        await ctx.send(file=discord.File(file, "nsfw.gif"))

@bot.command(aliases=['boobs'])
async def tits(ctx):
    await ctx.message.delete()
    async with aiohttp.ClientSession() as session:
        async with session.get("https://nekobot.xyz/api/image?type=boobs") as resp:
            data = await resp.json()
            if "message" not in data:
                return await ctx.send("```Failed to fetch image```")
            image_url = data["message"]

    await ctx.send(image_url)
    
    
    
 
 




bot.run(token, bot=False)
