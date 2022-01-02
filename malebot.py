import discord, os, random, re, time, subprocess, asyncio
from discord.ext import commands
from discord.ext import tasks
from utils import *
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
global songdir
global guildstates
#initialize a dictionary to store state for each guild
guildstates = {}
#songs directory
with open('songdir.txt', 'r') as songfile:
    songdir = songfile.read()
songitems = os.listdir(songdir)


'''HELPER FUNCTIONS'''    
#simple check to see if the bot is in a voice channel
def is_connected(guild):
    voice = discord.utils.get(client.voice_clients, guild=guild)
    return voice

#find a voice client by guild id, or return false if not found
def getVoiceClient(guildid):
    for i in client.voice_clients:
        if i.guild.id == guildid:
            return i
    return None
    
def playSong(guildid, song, timestamp, stopflag=False, ffmpegoptions=None):
    guildstates[guildid].now_playing = song
    guildstates[guildid].timestamp = timestamp
    if stopflag:
        getVoiceClient(guildid).stop()
        
    print("NP:\t"+song+"\t|\t"+str(guildid))
        
    if ffmpegoptions == None:
        getVoiceClient(guildid).play(discord.FFmpegPCMAudio(songdir+song), after=lambda e: print("FINISHED:\t"+str(guildid)))
    #special case for seek, but accepts any ffmpeg before_options
    else:
        getVoiceClient(guildid).play(discord.FFmpegPCMAudio(songdir+song, before_options=ffmpegoptions), after=lambda e: print("FINISHED:\t"+str(guildid)))
    getVoiceClient(guildid).source = discord.PCMVolumeTransformer(getVoiceClient(guildid).source)

#disconnect from a guild    
async def disconnectGuild(guild):
    if not is_connected(guild):
        return
    getVoiceClient(guild.id).stop()
    await getVoiceClient(guild.id).disconnect()
    await asyncio.sleep(1)
    if guild.id in guildstates.keys():
        guildstates.pop(guild.id)
    print("DISCONNECTED:\t"+str(guild.id))
    
#connect to a guild
async def connectGuild(ctx):
    connected = ctx.author.voice
    #check that the command user is in a channel
    if not connected:
        await ctx.send("♂GET♂YOUR♂ASS♂IN♂A♂VOICE♂CHANNEL♂")
        return 
    vc = await connected.channel.connect()
    
    #populate dictionaries if needed
    if not ctx.guild.id in guildstates.keys():
        guildstates[ctx.guild.id] = guildStateContainer() 
        guildstates[ctx.guild.id].id = ctx.guild.id
        guildstates[ctx.guild.id].init_channel = ctx
    print("CONNECTED:\t"+str(ctx.guild.id))

'''EVENT HANDLERS'''    
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
    if not shuffle_loop.is_running():
        shuffle_loop.start()

'''COMMAND HANDLERS'''
@client.command(aliases=['getoverhere', 'c'])
#connect the bot to a voice channel
async def join(ctx):
    if not is_connected(ctx.guild):
        await connectGuild(ctx)
    
@client.command(aliases=['fuckyou', 'dc'])
async def leave(ctx):
    if is_connected(ctx.guild):
        await disconnectGuild(ctx.guild)

@tasks.loop(seconds=1)
#loop task for playing random songs until cancelled
async def shuffle_loop():
    remove = []
    for key in guildstates.keys():
        guild = guildstates[key]
        if not is_connected(client.get_guild(guild.id)):
            remove.append(key)
        else:
            if getVoiceClient(guild.id) and guild.is_shuffling:
                if getVoiceClient(guild.id).is_playing() != None:
                    if not getVoiceClient(guild.id).is_playing() and not getVoiceClient(guild.id).is_paused():
                        songchoice = random.choice(songitems)
                        playSong(guild.id, songchoice, int(time.time()))
                        await guildstates[guild.id].init_channel.send("**♂NOW♂PLAYING♂:** "+songchoice)
    
    for key in remove:
        guildstates.pop(key)
        
@client.command(aliases=['shuffle', 's'])
async def randomplay(ctx):    
    if not is_connected(ctx.guild):     
        await connectGuild(ctx)
    guildstates[ctx.guild.id].is_shuffling = True
               
@client.command(aliases=['stop', 'st'])
async def deactivate(ctx):
    if is_connected(ctx.guild):
        if getVoiceClient(ctx.guild.id) != None:
            if getVoiceClient(ctx.guild.id).is_playing or getVoiceClient(ctx.guild.id).is_paused:
                getVoiceClient(ctx.guild.id).stop()
                guildstates[ctx.guild.id].is_shuffling = False
  
@client.command(aliases=['sk'])
async def skip(ctx):
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return      
    getVoiceClient(ctx.guild.id).stop()
 
@client.command(aliases=['p'])
async def pause(ctx):
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return
        
    if not getVoiceClient(ctx.guild.id).is_paused():
        getVoiceClient(ctx.guild.id).pause() 
        
@client.command(aliases=['r'])
async def resume(ctx):
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return
        
    if getVoiceClient(ctx.guild.id).is_paused():
        getVoiceClient(ctx.guild.id).resume()      

@client.command(aliases=['v'])
async def volume(ctx, arg):
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return
    
    if getVoiceClient(ctx.guild.id).is_playing or getVoiceClient(ctx.guild.id).is_paused:
        try:
            floatvol = round(float(arg), 2)
            if floatvol > 0 and floatvol <= 1.0:
                getVoiceClient(ctx.guild.id).source.volume = floatvol
            else:
                await ctx.send("♂FUCK♂YOU♂ (use a decimal number 0.01 to 1.00)")
        except:
            await ctx.send("♂FUCK♂YOU♂ (use a decimal number 0.01 to 1.00 and make sure the bot is connected and playing)")
        
@client.command(aliases=['re'])
async def replay(ctx):
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return
        
    if guildstates[ctx.guild.id].now_playing != None:
        playSong(ctx.guild.id, guildstates[ctx.guild.id].now_playing, int(time.time()), stopflag=True)
        await ctx.send("**♂NOW♂PLAYING♂:** "+guildstates[ctx.guild.id].now_playing)
    else:
        await ctx.send("♂NOTHING♂PLAYING♂")

@client.command(aliases=['se'])
async def seek(ctx, *args):
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return
        
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
    
    if guildstates[ctx.guild.id].now_playing != None:
        playSong(ctx.guild.id, guildstates[ctx.guild.id].now_playing, int(time.time())-int(args[0]), stopflag=True, ffmpegoptions="-ss "+args[0])
        await ctx.send("**♂SEEKING♂TO♂:** "+args[0]+" SECONDS♂")
    else:
        await ctx.send("♂NOTHING♂PLAYING♂")

@client.command(aliases=['np'])
async def nowplaying(ctx):
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return
        
    if guildstates[ctx.guild.id].now_playing != None and guildstates[ctx.guild.id].timestamp != None:
        stringduration = subprocess.check_output(['ffprobe', '-show_entries', 'format=duration', '-v', 'quiet', '-of', 'csv=%s' % ("p=0"), songdir+guildstates[ctx.guild.id].now_playing])
        duration = int(float(stringduration.strip().decode("utf-8")))
        currenttime = time.time() - guildstates[ctx.guild.id].timestamp
        filled = int((currenttime/duration)*25)
        await ctx.send("**♂NOW♂PLAYING♂:** "+guildstates[ctx.guild.id].now_playing+"\n```"+timetostr(currenttime)+" | ▶️"+"="*filled+"-"*(25-filled)+"🔊 | "+timetostr(duration)+"```")
    else:
        await ctx.send("♂NOTHING♂PLAYING♂")        

@client.command(aliases=['LOUDER'])
async def distort(ctx, *args):
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return
    '''TODO: TAKE MAGNITUDE AS ARGUMENT 
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
    '''
    if guildstates[ctx.guild.id].now_playing != None:
        distort_audio(songdir+guildstates[ctx.guild.id].now_playing, songdir, 15, ctx.guild.id)
        currenttime = int(time.time() - guildstates[ctx.guild.id].timestamp)
        playSong(ctx.guild.id, "___"+str(ctx.guild.id)+"temp1.wav", int(time.time())-currenttime, stopflag=True, ffmpegoptions="-ss "+str(currenttime))
        await ctx.send("**♂LOUDER♂SIR♂** ")
    else:
        await ctx.send("♂NOTHING♂PLAYING♂")
        
@client.command(aliases=['f'])
async def fuzzy(ctx, *args):
    if not is_connected(ctx.guild):
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
        guildstates[ctx.guild.id].is_shuffling = False
        playSong(ctx.guild.id, match, int(time.time()), stopflag=True)
        await ctx.send("**♂NOW♂PLAYING♂:** "+match)

@client.command(aliases=['key'])
async def keyword(ctx, *args):
    if not is_connected(ctx.guild):
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
        guildstates[ctx.guild.id].is_shuffling = False
        playSong(ctx.guild.id, matches[0], int(time.time()), stopflag=True)
        await ctx.send("**♂NOW♂PLAYING♂:** "+matches[0])
    elif len(matches) > 1:
        outstr = "♂MULTIPLE♂MATCHES♂FOUND♂:\n"
        count = 0
        for i in matches:
            outstr += str(count)+"\t|\t"+i+"\n"
            count += 1
        if len(outstr) > 1999:
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
    "**Volume**\t|\t(aliases: 'volume', 'v')\nSets the volume to a decimal value 0.01 to 1.00.\n\-\-\-\n"\
    "**Seek**\t|\t(aliases: 'seek', 'se')\nSeek to time given an integer value in seconds.\n\-\-\-\n"\
    "**Now Playing**\t|\t(aliases: 'nowplaying', 'np')\nShow a progress bar for the current song.\n\-\-\-\n"\
    "**Replay**\t|\t(aliases: 'replay', 're')\nReplays current song.\n\-\-\-\n"\
    "**Fuzzy**\t|\t(aliases: 'fuzzy', 'f')\nDoes a simple fuzzy search for the argument in quotes.\n\-\-\-\n"\
    "**Keyword Search**\t|\t(aliases: 'keyword', 'key')\nSearches for matches containing all keywords.\n\-\-\-\n")


with open('key.txt', 'r') as keyfile:
    client.run(keyfile.read())