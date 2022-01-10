import os
import random
import re
import time
import subprocess
import asyncio

import discord
from discord.ext import commands
from discord.ext import tasks

from utils import *
from queueclass import musicQueue
from statecontainer import guildStateContainer

global client
global songitems
global songdir
global guildstates

# setup intents to ensure bot has required permissions
intents = discord.Intents.default()
intents.members = True

# initialize the client object
client = commands.Bot(command_prefix=".", intents=intents)
client.remove_command("help")

# initialize a dictionary to store state for each guild
guildstates = {}

# open the song directory and make a list of song files
with open("songdir.txt", "r") as songfile:
    songdir = songfile.read().strip()
songitems = os.listdir(songdir)


"""HELPER FUNCTIONS"""


def is_connected(guild):
    """A simple check to see if the bot is in a voice channel"""
    voice = discord.utils.get(client.voice_clients, guild=guild)
    return voice


def getVoiceClient(guildid):
    """Find a voice client by guild id, or return false if not found."""
    for i in client.voice_clients:
        if i.guild.id == guildid:
            return i
    return None


def playSong(guildid, song, timestamp, stopflag=True, ffmpegoptions="", settitle=True):
    """Set state for the guild in question, then start the FFMPEG player object."""

    if settitle:  # set the display title or not, used when playing an altered sound file
        guildstates[guildid].title = song
    guildstates[guildid].now_playing = song
    guildstates[guildid].timestamp = timestamp

    if stopflag:  # if we should stop the currently playing song immediately or not
        getVoiceClient(guildid).stop()
    print("NP:\t" + song + "\t|\t" + str(guildid))
    getVoiceClient(guildid).play(
        discord.FFmpegPCMAudio(songdir + song, before_options=ffmpegoptions),
        after=lambda e: print("FINISHED:\t" + str(guildid)),
    )
    getVoiceClient(guildid).source = discord.PCMVolumeTransformer(getVoiceClient(guildid).source)


async def disconnectGuild(guild):
    """Disconnect from a guild."""
    if not is_connected(guild):
        return
    getVoiceClient(guild.id).stop()
    await getVoiceClient(guild.id).disconnect()
    await asyncio.sleep(1)  # to make sure the disconnect finishes before removing the state
    if guild.id in guildstates.keys():
        guildstates.pop(guild.id)
    print("DISCONNECTED:\t" + str(guild.id))


async def connectGuild(ctx):
    """Connect to a guild."""
    connected = ctx.author.voice
    if not connected:
        await ctx.send("♂GET♂YOUR♂ASS♂IN♂A♂VOICE♂CHANNEL♂")
        return
    vc = await connected.channel.connect()

    if ctx.guild.id not in guildstates.keys():
        guildstates[ctx.guild.id] = guildStateContainer()
        guildstates[ctx.guild.id].id = ctx.guild.id
        guildstates[ctx.guild.id].init_channel = ctx
    print("CONNECTED:\t" + str(ctx.guild.id))


"""EVENT HANDLERS"""


@client.event
async def on_voice_state_update(member, before, after):
    """Disconnect if alone in the channel."""
    if not getVoiceClient(member.guild.id):
        return

    await asyncio.sleep(1)  # discord's member list updates slowly
    channels = client.get_all_channels()
    for channel in channels:
        if channel.type == discord.ChannelType.voice:
            members = channel.members
            if len(members) == 1:
                flag = False
                for chanmem in members:
                    # if channel the bot is in is empty, disconnect
                    if chanmem.id == client.user.id:
                        flag = True
                if flag:
                    await disconnectGuild(member.guild)


@client.event
async def on_ready():
    """Login event, set status and cleanup old temp files, start background tasks"""
    print("Logged in as {0.user}".format(client))
    await client.change_presence(activity=discord.Game(name="try .help"))

    for song in songitems:
        if song[:3] == "___" and song[-8:] == "temp.wav":
            os.remove(songdir + song)  # delete leftover temp files
            print("DELETED OLD TEMP:" + song)
    if not shuffle_loop.is_running():
        shuffle_loop.start()


"""COMMAND HANDLERS"""


@client.command(aliases=["getoverhere", "c"])
async def join(ctx):
    """Connect the bot to a voice channel."""
    print("CONNECT\t|\t" + str(ctx.guild.id))
    if not is_connected(ctx.guild):
        await connectGuild(ctx)


@client.command(aliases=["fuckyou", "dc"])
async def leave(ctx):
    """Disconnect the bot from a voice channel."""
    print("DISCONNECT\t|\t" + str(ctx.guild.id))
    if is_connected(ctx.guild):
        await disconnectGuild(ctx.guild)


@tasks.loop(seconds=1)
async def shuffle_loop():
    """Background task to continuously play random songs, one instance handles all guilds"""
    remove = []
    for key in guildstates.keys():
        guild = guildstates[key]
        if not is_connected(client.get_guild(guild.id)):
            remove.append(key)  # to avoid inconsistent state from unexpected disconnection
        else:
            if getVoiceClient(guild.id) and guild.is_shuffling:
                if getVoiceClient(guild.id).is_playing() is not None:
                    if (
                        not getVoiceClient(guild.id).is_playing()
                        and not getVoiceClient(guild.id).is_paused()
                    ):
                        songchoice = ""
                        while songchoice == "" or songchoice[-8:] == "temp.wav":
                            songchoice = random.choice(songitems)  # avoid altered files

                        if guildstates[guild.id].is_louder:
                            distorted_file = distort_audio(
                                songdir + songchoice,
                                songdir,
                                guildstates[guild.id].louder_magnitude,
                                guild.id,
                            )
                            guildstates[guild.id].title = songchoice
                            playSong(
                                guild.id,
                                distorted_file,
                                int(time.time()),
                                stopflag=False,
                                settitle=False,
                            )
                        else:
                            playSong(guild.id, songchoice, int(time.time()), stopflag=False)
                        await guildstates[guild.id].init_channel.send(
                            "**♂NOW♂PLAYING♂:** " + guildstates[guild.id].title
                        )

    for key in remove:
        guildstates.pop(key)


@client.command(aliases=["shuffle", "s"])
async def randomplay(ctx):
    """Continuously play random songs in the guild."""
    print("SHUFFLE\t|\t" + str(ctx.guild.id))
    if not is_connected(ctx.guild):
        await connectGuild(ctx)
    guildstates[ctx.guild.id].is_shuffling = True


@client.command(aliases=["stop", "st"])
async def deactivate(ctx):
    """Stop the current song, and cancel shuffle/queue loops."""
    print("STOP\t|\t" + str(ctx.guild.id))
    if is_connected(ctx.guild):
        if getVoiceClient(ctx.guild.id) is not None:
            if getVoiceClient(ctx.guild.id).is_playing or getVoiceClient(ctx.guild.id).is_paused:
                getVoiceClient(ctx.guild.id).stop()
                guildstates[ctx.guild.id].is_shuffling = False


@client.command(aliases=["sk"])
async def skip(ctx):
    """Skip the current song."""
    print("SKIP\t|\t" + str(ctx.guild.id))
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return
    getVoiceClient(ctx.guild.id).stop()


@client.command(aliases=["p"])
async def pause(ctx):
    """Pause the current song."""
    print("PAUSE\t|\t" + str(ctx.guild.id))
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return

    if not getVoiceClient(ctx.guild.id).is_paused():
        getVoiceClient(ctx.guild.id).pause()


@client.command(aliases=["r"])
async def resume(ctx):
    """Resume a paused song, if there is one."""
    print("RESUME\t|\t" + str(ctx.guild.id))
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return

    if getVoiceClient(ctx.guild.id).is_paused():
        getVoiceClient(ctx.guild.id).resume()


@client.command(aliases=["v"])
async def volume(ctx, arg):
    """Set the volume to a float value 0.01 to 1.00."""
    print("VOLUME\t|\t" + str(ctx.guild.id) + "\t|\t" + str(arg))
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
            await ctx.send("♂FUCK♂YOU♂ (Use a decimal 0.01 to 1.00, make sure the bot is playing)")


@client.command(aliases=["re"])
async def replay(ctx):
    """Restart the currently playing or most recently played song."""
    print("REPLAY\t|\t" + str(ctx.guild.id))
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return

    if guildstates[ctx.guild.id].now_playing is not None:
        playSong(
            ctx.guild.id,
            guildstates[ctx.guild.id].now_playing,
            int(time.time()),
            settitle=False,
        )
        await ctx.send("**♂NOW♂PLAYING♂:** " + guildstates[ctx.guild.id].title)
    else:
        await ctx.send("♂NOTHING♂PLAYING♂")


@client.command(aliases=["se"])
async def seek(ctx, *args):
    """Seek to an integer timestamp in seconds."""
    print("SEEK\t|\t" + str(ctx.guild.id) + "\t|\t" + str(args))
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

    if guildstates[ctx.guild.id].now_playing is not None:
        playSong(
            ctx.guild.id,
            guildstates[ctx.guild.id].now_playing,
            int(time.time()) - int(args[0]),
            ffmpegoptions="-ss " + args[0],
            settitle=False,
        )  # Subtract the amount of seconds seeked to from the current time to simulate an earlier start time
        await ctx.send("**♂SEEKING♂TO♂:** " + args[0] + " SECONDS♂")
    else:
        await ctx.send("♂NOTHING♂PLAYING♂")


@client.command(aliases=["np"])
async def nowplaying(ctx):
    """Display a progress bar for the currently playing song."""
    print("NOWPLAYING\t|\t" + str(ctx.guild.id))
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return

    if (
        guildstates[ctx.guild.id].now_playing is not None
        and guildstates[ctx.guild.id].timestamp is not None
    ):
        stringduration = subprocess.check_output(
            [
                "ffprobe",
                "-show_entries",
                "format=duration",
                "-v",
                "quiet",
                "-of",
                "csv=%s" % ("p=0"),
                songdir + guildstates[ctx.guild.id].now_playing,
            ]
        )
        duration = int(float(stringduration.strip().decode("utf-8")))
        currenttime = time.time() - guildstates[ctx.guild.id].timestamp
        filled = int((currenttime / duration) * 25)  # how much of progress bar to fill
        await ctx.send(
            "**♂NOW♂PLAYING♂:** "
            + guildstates[ctx.guild.id].title
            + "\n```"
            + timetostr(currenttime)
            + " | ▶️"
            + "=" * filled
            + "-" * (25 - filled)
            + "🔊 | "
            + timetostr(duration)
            + "```"
        )
    else:
        await ctx.send("♂NOTHING♂PLAYING♂")


@client.command(aliases=["LOUDER"])
async def distort(ctx, *args):
    """Toggle a mode to heavily distort played songs."""
    """Optionally takes an integer 5-50 as an argument to set magnitude."""
    print("DISTORT\t|\t" + str(ctx.guild.id) + "\t|\t" + str(args))
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return

    if guildstates[ctx.guild.id].now_playing is None:
        await ctx.send("♂NOTHING♂PLAYING♂")
        return

    if len(args) == 0:
        guildstates[ctx.guild.id].louder_magnitude = 16
    if len(args) > 0:
        try:
            test = int(args[0])
            if test < 5 or test > 50:
                raise ValueError
            guildstates[ctx.guild.id].louder_magnitude = test
        except:
            await ctx.send("♂MAGNITUDE♂MUST♂BE♂A♂POSITIVE♂INTEGER♂BETWEEN♂5♂AND♂50♂")
            return

    guildstates[ctx.guild.id].is_louder = not guildstates[ctx.guild.id].is_louder  # toggle mode

    if guildstates[ctx.guild.id].now_playing is not None:
        if guildstates[ctx.guild.id].is_louder:
            distorted_file = distort_audio(
                songdir + guildstates[ctx.guild.id].now_playing,
                songdir,
                guildstates[ctx.guild.id].louder_magnitude,
                ctx.guild.id,
            )
            currenttime = int(time.time() - guildstates[ctx.guild.id].timestamp)
            playSong(
                ctx.guild.id,
                distorted_file,
                int(time.time()) - currenttime,
                ffmpegoptions="-ss " + str(currenttime),
                settitle=False,
            )
            await ctx.send("**♂LOUDER♂SIR♂**")
        else:
            currenttime = int(time.time() - guildstates[ctx.guild.id].timestamp)
            playSong(
                ctx.guild.id,
                guildstates[ctx.guild.id].title,
                int(time.time()) - currenttime,
                ffmpegoptions="-ss " + str(currenttime),
            )  # use title of currently playing song to find the original file and replay it
            await ctx.send("♂quieter♂sir♂")
    else:
        await ctx.send("♂NOTHING♂PLAYING♂")


@client.command(aliases=["f"])
async def fuzzy(ctx, *args):
    """Perform a fuzzy search for the string given by the user."""
    """Uses Simon White's 'Strike a match' algorithm, as it is more length agnostic than most."""
    """More information: http://www.catalysoft.com/articles/strikeamatch.html"""
    print("FUZZY\t|\t" + str(ctx.guild.id) + "\t|\t" + str(args))
    if not is_connected(ctx.guild):
        await connectGuild(ctx)

    keywords = " ".join(args[:]).lower()
    max = -1
    match = None
    for i in songitems:
        if not i[-8:] == "temp.wav":
            score = matchCompare(
                re.sub(r"[^a-zA-Z0-9♂ ]+", "", i.lower().split(".")[0]).replace("♂", " "), keywords
            )
            if score > max:
                max = score
                match = i

    if match:
        guildstates[ctx.guild.id].is_shuffling = False
        if guildstates[ctx.guild.id].is_louder:
            distorted_file = distort_audio(
                songdir + match, songdir, guildstates[ctx.guild.id].louder_magnitude, ctx.guild.id
            )
            guildstates[ctx.guild.id].title = match
            playSong(ctx.guild.id, distorted_file, int(time.time()), settitle=False)
        else:
            playSong(ctx.guild.id, match, int(time.time()))
        await ctx.send("**♂NOW♂PLAYING♂:** " + guildstates[ctx.guild.id].title)


@client.command(aliases=["key"])
async def keyword(ctx, *args):
    """Perform a keyword search for matches including all keywords given as arguments."""
    """If multiple matches are found, they are displayed to the user."""
    print("KEYWORD\t|\t" + str(ctx.guild.id) + "\t|\t" + str(args))
    if not is_connected(ctx.guild):
        await connectGuild(ctx)

    keywords = " ".join(args[:]).lower().split(" ")
    matches = []

    for i in songitems:
        flag = True
        item = re.sub(r"[^a-zA-Z0-9♂ ]+", "", i.lower().split(".")[0]).replace("♂", " ")

        for word in keywords:
            if word not in item:
                flag = False
        if flag and not i[-8:] == "temp.wav":
            matches.append(i)

    if len(matches) == 1:
        guildstates[ctx.guild.id].is_shuffling = False
        if guildstates[ctx.guild.id].is_louder:
            distorted_file = distort_audio(
                songdir + matches[0],
                songdir,
                guildstates[ctx.guild.id].louder_magnitude,
                ctx.guild.id,
            )
            guildstates[ctx.guild.id].title = matches[0]
            playSong(ctx.guild.id, distorted_file, int(time.time()), settitle=False)
        else:
            playSong(ctx.guild.id, matches[0], int(time.time()))
        await ctx.send("**♂NOW♂PLAYING♂:** " + guildstates[ctx.guild.id].title)
    elif len(matches) > 1:
        outstr = "♂MULTIPLE♂MATCHES♂FOUND♂:\n"
        count = 0
        for i in matches:
            outstr += str(count) + "\t|\t" + i + "\n"
            count += 1
        if len(outstr) > 1999:
            await ctx.send("♂TOO♂MANY♂MATCHES♂TO♂DISPLAY♂")
        else:
            await ctx.send(outstr)
    else:
        await ctx.send("♂NO♂MATCHES♂")


@client.command()
async def help(ctx):
    """Help command, displays command information."""
    separator = "\n\-\-\-\n"
    await ctx.send(
        "\n\t\t**\-\-\-\-\-\-\-\-\-♂MALE♂BOT♂HELP♂\-\-\-\-\-\-\-\-\-**\n"
        "\t\t*COMMANDS (case sensitive):*\n"
        "**Join**\t|\t(aliases: 'getoverhere', 'join', 'c')\n"
        "Connects the bot to the voice channel the author is connected to."
        + separator
        + "**Leave**\t|\t(aliases: 'fuckyou', 'leave', 'dc')\n"
        "Disconnects the bot from voice."
        + separator
        + "**Shuffle Play**\t|\t(aliases: 'shuffle', 's')\n"
        "Plays random song on loop until stopped."
        + separator
        + "**Stop**\t|\t(aliases: 'stop', 'st')\n"
        "Stops the current shuffle queue." + separator + "**Skip**\t|\t(aliases: 'skip', 'sk')\n"
        "Skips the current song and picks a new random one."
        + separator
        + "**Pause**\t|\t(aliases: 'pause', 'p')\n"
        "Pauses the currently playing song."
        + separator
        + "**Resume**\t|\t(aliases: 'resume', 'r')\n"
        "Resumes the currently playing song."
        + separator
        + "**Volume**\t|\t(aliases: 'volume', 'v')\n"
        "Sets the volume to a decimal value 0.01 to 1.00."
        + separator
        + "**Seek**\t|\t(aliases: 'seek', 'se')\n"
        "Seek to time given an integer value in seconds."
        + separator
        + "**Now Playing**\t|\t(aliases: 'nowplaying', 'np')\n"
        "Show a progress bar for the current song."
        + separator
        + "**Replay**\t|\t(aliases: 'replay', 're')\n"
        "Replays current song." + separator + "**Distort**\t|\t(aliases: 'distort', 'LOUDER')\n"
        "Heavily distorts current song, and toggles distorted mode on or off."
        " Optionally takes an integer 5-50 as an argument to set magnitude."
        + separator
        + "**Fuzzy**\t|\t(aliases: 'fuzzy', 'f')\n"
        "Does a simple fuzzy search for the argument in quotes."
        + separator
        + "**Keyword Search**\t|\t(aliases: 'keyword', 'key')\n"
        "Searches for matches containing all keywords." + separator
    )


with open("key.txt", "r") as keyfile:
    client.run(keyfile.read().strip())
