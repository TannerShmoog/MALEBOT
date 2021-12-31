import discord, os, random, re, time, subprocess, asyncio
from discord.ext import commands
from discord.ext import tasks
from strikeamatch import matchCompare
from queueclass import musicQueue
from statecontainer import guildStateContainer

intents = discord.Intents.default()
intents.messages = True
intents.reactions = True
intents.members = True
intents.voice_states = True

global client
client = commands.Bot(command_prefix='.', intents=intents)
client.remove_command('help')


global songitems
global songhist
global timestamp

#store the voice client and some variables per guild
songhist = {}
timestamp = {}
#songs directory
with open('songdir.txt', 'r') as songfile:
    songdir = songfile.read()
songitems = os.listdir(songdir)

#simple check to see if the bot is in a voice channel
def is_connected(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    return voice

#find a voice client by guild id, or return false if not found
def getVoiceClient(guildid):
    for i in client.voice_clients:
        if i.guild.id == guildid:
            return i
    return None

#disconnect from a guild    
async def disconnectGuild(guild):
    getVoiceClient(guild.id).stop()
    await getVoiceClient(guild.id).disconnect()
    await asyncio.sleep(1)
    timestamp.pop(guild)
    songhist.pop(guild)
    
#connect to a guild
async def connectGuild(ctx):
    connected = ctx.author.voice
    #check that the command user is in a channel
    if not connected:
        await ctx.send("♂GET♂YOUR♂ASS♂IN♂A♂VOICE♂CHANNEL♂")
        return 
    vc = await connected.channel.connect()
    
    #populate dictionaries if needed
    if not ctx.guild in songhist.keys():
        songhist[ctx.guild] = None
        timestamp[ctx.guild] = None
        
#disconnect if alone in the channel
@client.event
async def on_voice_state_update(member, before, after):
    #if no voice client in this server
    if not getVoiceClient(member.guild.id):
        return
    
    await asyncio.sleep(1)
    channels = client.get_all_channels()
    for channel in channels:
        #if channel the bot is in is empty, disconnect
        if channel.type == discord.ChannelType.voice:
            members = channel.members
            if len(members) == 1:  
                flag = False
                for chanmem in members:
                    if chanmem.id == client.user.id:
                        flag = True
                if flag:
                    await disconnectGuild(member.guild)
   
@client.event
#login event, set status
async def on_ready():
    print('Logged in as {0.user}'.format(client))
    await client.change_presence(activity=discord.Game(name="try .help"))

@client.command(aliases=['getoverhere', 'c'])
#connect the bot to a voice channel
async def join(ctx):
    if not is_connected(ctx):
        await connectGuild(ctx)
    
@client.command(aliases=['fuckyou', 'dc'])
async def leave(ctx):
    if is_connected(ctx):
        await disconnectGuild(ctx.guild)

@tasks.loop(seconds=1)
#loop task for playing random songs until cancelled
async def shuffle_loop(ctx):
    if getVoiceClient(ctx.guild.id):
        if getVoiceClient(ctx.guild.id).is_playing() != None:
            print(1)
            if not getVoiceClient(ctx.guild.id).is_playing() and not getVoiceClient(ctx.guild.id).is_paused():
                print(2)
                songchoice = random.choice(songitems)
                songhist[ctx.guild] = songchoice
                timestamp[ctx.guild] = int(time.time())
                getVoiceClient(ctx.guild.id).play(discord.FFmpegPCMAudio(songdir+songchoice), after=lambda e: print(songchoice, ctx.guild))
                getVoiceClient(ctx.guild.id).source = discord.PCMVolumeTransformer(getVoiceClient(ctx.guild.id).source)
                await ctx.send("**♂NOW♂PLAYING♂:** "+songchoice)
        
@client.command(aliases=['shuffle', 's'])
async def randomplay(ctx):    
    if not is_connected(ctx):     
        await connectGuild(ctx)
        
    if not shuffle_loop.is_running():
        shuffle_loop.start(ctx)
       
@client.command(aliases=['stop', 'st'])
async def deactivate(ctx):
    if is_connected(ctx):
        if getVoiceClient(ctx.guild.id) != None:
            if getVoiceClient(ctx.guild.id).is_playing or getVoiceClient(ctx.guild.id).is_paused:
                getVoiceClient(ctx.guild.id).stop()
                shuffle_loop.cancel()
  
@client.command(aliases=['sk'])
async def skip(ctx):
    getVoiceClient(ctx.guild.id).stop()
 
@client.command(aliases=['p'])
async def pause(ctx):
    if not getVoiceClient(ctx.guild.id).is_paused():
        getVoiceClient(ctx.guild.id).pause() 
        
@client.command(aliases=['r'])
async def resume(ctx):
    if getVoiceClient(ctx.guild.id).is_paused():
        getVoiceClient(ctx.guild.id).resume()      

@client.command(aliases=['LOUDER', 'v'])
async def volume(ctx, arg):
    try:
        floatvol = round(float(arg), 2)
        if floatvol > 0 and floatvol <= 1.0:
            getVoiceClient(ctx.guild.id).source.volume = floatvol
        else:
            await ctx.send("♂FUCK♂YOU♂ (use a decimal number 0.01 to 1.00)")
    except:
        await ctx.send("♂FUCK♂YOU♂ (use a decimal number 0.01 to 1.00 and make sure the bot is connected and playing)")
        
@client.command(aliases=['twoplay', 're'])
async def replay(ctx):
    if songhist[ctx.guild]:
        getVoiceClient(ctx.guild.id).stop()
        timestamp[ctx.guild] = int(time.time())
        getVoiceClient(ctx.guild.id).play(discord.FFmpegPCMAudio(songdir+songhist[ctx.guild]), after=lambda e: print(songhist[ctx.guild], ctx.guild))
        getVoiceClient(ctx.guild.id).source = discord.PCMVolumeTransformer(getVoiceClient(ctx.guild.id).source)
        await ctx.send("**♂NOW♂PLAYING♂:** "+songhist[ctx.guild])
    else:
        await ctx.send("♂NOTHING♂PLAYING♂")

@client.command(aliases=['se'])
async def seek(ctx, *args):
    if len(args) == 0:
        await ctx.send("♂ENTER♂A♂TIMESTAMP♂IN♂SECONDS♂")
        return
    try:
        test = int(args[0])
        if test <= 0:
            raise ValueError
    except:
        await ctx.send("♂TIMESTAMP♂MUST♂BE♂A♂POSITIVE♂INTEGER♂")
        return
    
    if songhist[ctx.guild]:
        getVoiceClient(ctx.guild.id).stop()
        timestamp[ctx.guild] = int(time.time())-int(args[0])
        getVoiceClient(ctx.guild.id).play(discord.FFmpegPCMAudio(songdir+songhist[ctx.guild], before_options="-ss "+args[0]), after=lambda e: print(songhist[ctx.guild], ctx.guild))
        getVoiceClient(ctx.guild.id).source = discord.PCMVolumeTransformer(getVoiceClient(ctx.guild.id).source)
        await ctx.send("**♂SEEKING♂TO♂:** "+args[0]+" SECONDS♂")
    else:
        await ctx.send("♂NOTHING♂PLAYING♂")

@client.command(aliases=['np'])
async def nowplaying(ctx): 
    if songhist[ctx.guild] and timestamp[ctx.guild]:
        stringduration = subprocess.check_output(['ffprobe', '-show_entries', 'format=duration', '-v', 'quiet', '-of', 'csv=%s' % ("p=0"), songdir+songhist[ctx.guild]])
        duration = int(float(stringduration.strip().decode("utf-8")))
        currenttime = time.time() - timestamp[ctx.guild]
        filled = int((currenttime/duration)*25)
        await ctx.send("**♂NOW♂PLAYING♂:** "+songhist[ctx.guild]+"\n```▶️"+"="*filled+"-"*(25-filled)+"🔊```")
    else:
        await ctx.send("♂NOTHING♂PLAYING♂")        

@client.command(aliases=['f'])
async def fuzzy(ctx, *args):
    if not is_connected(ctx):
        await connectGuild(ctx)
    
    keywords = " ".join(args[:]).lower()
    max = -1
    match = None
    for i in songitems:
        score = matchCompare(re.sub(r'[^a-zA-Z0-9♂ ]+', '', i.lower().split('.')[0]).replace('♂', ' '), keywords)
        if score > max:
            max = score
            match = i
            
    if match:
        songhist[ctx.guild] = match
        timestamp[ctx.guild] = int(time.time())
        getVoiceClient(ctx.guild.id).stop()
        getVoiceClient(ctx.guild.id).play(discord.FFmpegPCMAudio(songdir+match), after=lambda e: print(match, ctx.guild))
        getVoiceClient(ctx.guild.id).source = discord.PCMVolumeTransformer(getVoiceClient(ctx.guild.id).source)
        await ctx.send("**♂NOW♂PLAYING♂:** "+match)

@client.command(aliases=['key'])
async def keyword(ctx, *args):
    if not is_connected(ctx):
        await connectGuild(ctx)
            
    keywords = " ".join(args[:]).lower().split(' ')
    matches = []
    
    for i in songitems:
        flag = True            
        item = re.sub(r'[^a-zA-Z0-9♂ ]+', '', i.lower().split('.')[0]).replace('♂', ' ')

        for word in keywords:
            if word not in item:
                flag = False
        if flag:
            matches.append(i)
    
    if len(matches) == 1:
        songhist[ctx.guild] = matches[0]
        timestamp[ctx.guild] = int(time.time())
        getVoiceClient(ctx.guild.id).stop()
        getVoiceClient(ctx.guild.id).play(discord.FFmpegPCMAudio(songdir+matches[0]), after=lambda e: print(matches[0], ctx.guild))
        getVoiceClient(ctx.guild.id).source = discord.PCMVolumeTransformer(getVoiceClient(ctx.guild.id).source)
        await ctx.send("**♂NOW♂PLAYING♂:** "+matches[0])
    elif len(matches) > 1:
        outstr = "♂MULTIPLE♂MATCHES♂FOUND♂:\n"
        count = 0
        for i in matches:
            outstr += str(count)+"\t|\t"+i+"\n"
            count += 1
        if len(outstr) > 3999:
            await ctx.send("♂TOO♂MANY♂MATCHES♂TO♂DISPLAY♂")
        else:
            await ctx.send(outstr)
    else:
        await ctx.send("♂NO♂MATCHES♂")
        
@client.command()      
async def help(ctx):  
    await ctx.send("\n\t\t**\-\-\-\-\-\-\-\-\-♂MALE♂BOT♂HELP♂\-\-\-\-\-\-\-\-\-**\n\t\t*COMMANDS (case sensitive):*\n"\
    "**Join**\t|\t(aliases: 'getoverhere', 'join', 'c')\nConnects the bot to the voice channel the author is connected to.\n\-\-\-\n"\
    "**Leave**\t|\t(aliases: 'fuckyou', 'leave', 'dc')\nDisconnects the bot from voice.\n\-\-\-\n"\
    "**Shuffle Play**\t|\t(aliases: 'shuffle', 's')\nPlays random song on loop until stopped.\n\-\-\-\n"\
    "**Stop**\t|\t(aliases: 'stop', 'st')\nStops the current shuffle queue.\n\-\-\-\n"\
    "**Skip**\t|\t(aliases: 'skip', 'sk')\nSkips the current song and picks a new random one.\n\-\-\-\n"\
    "**Pause**\t|\t(aliases: 'pause', 'p')\nPauses the currently playing song.\n\-\-\-\n"\
    "**Resume**\t|\t(aliases: 'resume', 'r')\nResumes the currently playing song.\n\-\-\-\n"\
    "**Volume**\t|\t(aliases: 'LOUDER', 'volume', 'v')\nSets the volume to a decimal value 0.01 to 1.00.\n\-\-\-\n"\
    "**Seek**\t|\t(aliases: 'seek', 'se')\nSeek to time given an integer value in seconds.\n\-\-\-\n"\
    "**Now Playing**\t|\t(aliases: 'nowplaying', 'np')\nShow a progress bar for the current song.\n\-\-\-\n"\
    "**Replay**\t|\t(aliases: 'twoplay', 'replay', 're')\nReplays current song.\n\-\-\-\n"\
    "**Fuzzy**\t|\t(aliases: 'fuzzy', 'f')\nDoes a simple fuzzy search for the argument in quotes.\n\-\-\-\n"\
    "**Keyword Search**\t|\t(aliases: 'keyword', 'key')\nSearches for matches containing all keywords.\n\-\-\-\n")

#timestamp, nowplaying, isqueueing, isshuffling all into 1 object to keep track of state
#change shuffletask to run on start, and loop through all guilds to see if they are shuffling, then add all shuffling logic as needed
#intents/perms issues, isconnected/isnotconnected in all routines
#comments, readme format

#searches add to bottom of queue and cancel shuffle loop, start queue loop if wasnt already
#show queue, delete from queue, move x to y position, clear

#dl new gachi
#maybe, store volume preferences/history in db, display history

with open('key.txt', 'r') as keyfile:
    client.run(keyfile.read())