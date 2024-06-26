import os
import sys
import random
import re
import time
import subprocess
import asyncio

import discord
from discord.ext import commands
from discord.ext import tasks

from utils import *
from queueclass import MusicQueue
from statecontainer import GuildStateContainer

global client
global songitems
global songdir
global guildstates

# setup intents to ensure bot has required permissions
intents = discord.Intents.all()
intents.members = True

# initialize the client object
client = commands.Bot(command_prefix=".", intents=intents)
client.remove_command("help")

# initialize a dictionary to store state for each guild
guildstates = {}


"""HELPER FUNCTIONS"""


def is_connected(guild):
    """A simple check to see if the bot is in a voice channel"""
    voice = discord.utils.get(client.voice_clients, guild=guild)
    return voice


def get_voice_client(guildid):
    """Find a voice client by guild id, or return false if not found."""
    for i in client.voice_clients:
        if i.guild.id == guildid:
            return i
    return None


def play_song(guildid, song, timestamp, stopflag=True, ffmpegoptions="", settitle=True):
    """Set state for the guild in question, then start the FFMPEG player object."""
    if settitle:
        guildstates[guildid].title = song
    guildstates[guildid].timestamp = timestamp
    guildstates[guildid].now_playing = song

    if stopflag:  # if we should stop the currently playing song immediately or not
        get_voice_client(guildid).stop()

    checknp = guildstates[guildid].now_playing
    if guildstates[guildid].is_louder:
        if not checknp.startswith("___") and not checknp.endswith("temp.wav"):
            song = distort_audio(
                songdir,
                song,
                songdir,
                "___" + str(guildid) + "-temp.wav",
                guildstates[guildid].louder_magnitude,
                guildid,
            )

    # set file again AFTER potential distort
    guildstates[guildid].now_playing = song
    print("NP:\t" + song + "\t|\t" + str(guildid))
    get_voice_client(guildid).play(
        discord.FFmpegPCMAudio(songdir + song, before_options=ffmpegoptions),
        after=lambda e: print("FINISHED:\t" + str(guildid)),
    )
    get_voice_client(guildid).source = discord.PCMVolumeTransformer(
        get_voice_client(guildid).source
    )


async def disconnect_guild(guild):
    """Disconnect from a guild."""
    if not is_connected(guild):
        return
    get_voice_client(guild.id).stop()
    await get_voice_client(guild.id).disconnect()
    # to make sure the disconnect finishes before removing the state
    await asyncio.sleep(1)
    if guild.id in guildstates.keys():
        guildstates.pop(guild.id)
    print("DISCONNECTED:\t" + str(guild.id))


async def connect_guild(ctx):
    """Connect to a guild."""
    connected = ctx.author.voice
    if not connected:
        await ctx.send("♂GET♂YOUR♂ASS♂IN♂A♂VOICE♂CHANNEL♂")
        return
    vc = await connected.channel.connect()

    if ctx.guild.id not in guildstates.keys():
        guildstates[ctx.guild.id] = GuildStateContainer()
        guildstates[ctx.guild.id].id = ctx.guild.id
        guildstates[ctx.guild.id].init_channel = ctx
    print("CONNECTED:\t" + str(ctx.guild.id))


"""EVENT HANDLERS"""


@client.event
async def on_voice_state_update(member, before, after):
    """Disconnect if alone in the channel."""
    if not get_voice_client(member.guild.id):
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
                    await disconnect_guild(member.guild)


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
        await connect_guild(ctx)


@client.command(aliases=["fuckyou", "dc"])
async def leave(ctx):
    """Disconnect the bot from a voice channel."""
    print("DISCONNECT\t|\t" + str(ctx.guild.id))
    if is_connected(ctx.guild):
        await disconnect_guild(ctx.guild)


@tasks.loop(seconds=1)
async def shuffle_loop():
    """Background task to continuously play random songs, one instance handles all guilds"""
    remove = []
    for key in guildstates.keys():
        guild = guildstates[key]
        if not is_connected(client.get_guild(guild.id)):
            # to avoid inconsistent state from unexpected disconnection
            remove.append(key)
        else:
            if get_voice_client(guild.id) and guild.is_looping:
                if get_voice_client(guild.id).is_playing() is not None:
                    if (
                        not get_voice_client(guild.id).is_playing()
                        and not get_voice_client(guild.id).is_paused()
                    ):
                        play_song(guild.id, guild.now_playing,
                                  int(time.time()), settitle=False)
                        await guild.init_channel.send("**♂NOW♂PLAYING♂:\t** " + guild.title)
            elif get_voice_client(guild.id) and guild.is_shuffling and not guild.is_queueing:
                if get_voice_client(guild.id).is_playing() is not None:
                    if (
                        not get_voice_client(guild.id).is_playing()
                        and not get_voice_client(guild.id).is_paused()
                    ):
                        songchoice = ""
                        while songchoice == "" or songchoice[-8:] == "temp.wav":
                            songchoice = random.choice(
                                songitems)  # avoid altered files
                        play_song(guild.id, songchoice, int(
                            time.time()), stopflag=False)
                        await guild.init_channel.send("**♂NOW♂PLAYING♂:\t** " + guild.title)
            elif get_voice_client(guild.id) and guild.is_queueing:
                if get_voice_client(guild.id).is_playing() is not None:
                    if (
                        not get_voice_client(guild.id).is_playing()
                        and not get_voice_client(guild.id).is_paused()
                    ):
                        if not guild.queue.is_empty():
                            play_song(
                                guild.id,
                                guild.queue.playsong(),
                                int(time.time()),
                                stopflag=False,
                            )
                            await guild.init_channel.send("**♂NOW♂PLAYING♂:\t** " + guild.title)
                        if guild.queue.is_empty():
                            guild.is_queueing = False

    for key in remove:
        guildstates.pop(key)


@client.command(aliases=["shuffle", "s"])
async def randomplay(ctx):
    """Continuously play random songs in the guild."""
    print("SHUFFLE\t|\t" + str(ctx.guild.id))
    if not is_connected(ctx.guild):
        await connect_guild(ctx)
    guildstates[ctx.guild.id].is_shuffling = True
    guildstates[ctx.guild.id].is_queueing = False
    guildstates[ctx.guild.id].queue.clear()


@client.command(aliases=["stop", "st"])
async def deactivate(ctx):
    """Stop the current song, and cancel shuffle/queue loops."""
    print("STOP\t|\t" + str(ctx.guild.id))
    if is_connected(ctx.guild):
        if get_voice_client(ctx.guild.id) is not None:
            if (
                get_voice_client(ctx.guild.id).is_playing
                or get_voice_client(ctx.guild.id).is_paused
            ):
                get_voice_client(ctx.guild.id).stop()
                guildstates[ctx.guild.id].is_shuffling = False
                guildstates[ctx.guild.id].is_queueing = False
                guildstates[ctx.guild.id].queue.clear()


@client.command(aliases=["sk"])
async def skip(ctx):
    """Skip the current song."""
    print("SKIP\t|\t" + str(ctx.guild.id))
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return
    get_voice_client(ctx.guild.id).stop()


@client.command(aliases=["p"])
async def pause(ctx):
    """Pause the current song."""
    print("PAUSE\t|\t" + str(ctx.guild.id))
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return

    if not get_voice_client(ctx.guild.id).is_paused():
        get_voice_client(ctx.guild.id).pause()


@client.command(aliases=["r"])
async def resume(ctx):
    """Resume a paused song, if there is one."""
    print("RESUME\t|\t" + str(ctx.guild.id))
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return

    if get_voice_client(ctx.guild.id).is_paused():
        get_voice_client(ctx.guild.id).resume()


@client.command(aliases=["v"])
async def volume(ctx, arg):
    """Set the volume to a float value 0.01 to 1.00."""
    print("VOLUME\t|\t" + str(ctx.guild.id) + "\t|\t" + str(arg))
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return

    if get_voice_client(ctx.guild.id).is_playing or get_voice_client(ctx.guild.id).is_paused:
        try:
            floatvol = round(float(arg), 2)
            if floatvol > 0 and floatvol <= 1.0:
                get_voice_client(ctx.guild.id).source.volume = floatvol
            else:
                raise ValueError
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
        play_song(
            ctx.guild.id, guildstates[ctx.guild.id].now_playing, int(time.time()), settitle=False
        )
        await ctx.send("**♂NOW♂PLAYING♂:\t** " + guildstates[ctx.guild.id].title)
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
        play_song(
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
        # how much of progress bar to fill
        filled = int((currenttime / duration) * 25)
        await ctx.send(
            "**♂NOW♂PLAYING♂:\t** "
            + guildstates[ctx.guild.id].title
            + "\n```"
            + time_to_str(currenttime)
            + " | ▶️"
            + "=" * filled
            + "-" * (25 - filled)
            + "🔊 | "
            + time_to_str(duration)
            + "```"
        )
    else:
        await ctx.send("♂NOTHING♂PLAYING♂")


@client.command(aliases=["LOUDER"])
async def distort(ctx, *args):
    """Toggle a mode to heavily distort played songs.
    Optionally takes an integer 5-50 as an argument to set magnitude.
    """
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

    # toggle mode
    guildstates[ctx.guild.id].is_louder = not guildstates[ctx.guild.id].is_louder

    if guildstates[ctx.guild.id].now_playing is not None:
        currenttime = int(time.time() - guildstates[ctx.guild.id].timestamp)
        if guildstates[ctx.guild.id].is_louder:
            play_song(
                ctx.guild.id,
                guildstates[ctx.guild.id].now_playing,
                int(time.time()) - currenttime,
                ffmpegoptions="-ss " + str(currenttime),
            )
            await ctx.send("**♂LOUDER♂SIR♂**")
        else:
            play_song(
                ctx.guild.id,
                guildstates[ctx.guild.id].title,
                int(time.time()) - currenttime,
                ffmpegoptions="-ss " + str(currenttime),
            )
            await ctx.send("♂quieter♂sir♂")
    else:
        await ctx.send("♂NOTHING♂PLAYING♂")


@client.command(aliases=["f"])
async def fuzzy(ctx, *args):
    """Perform a fuzzy search for the string given by the user. Queues the result.
    Uses Simon White's 'Strike a Match' algorithm, as it is more length agnostic than most.

    More information: http://www.catalysoft.com/articles/strikeamatch.html
    """
    print("FUZZY\t|\t" + str(ctx.guild.id) + "\t|\t" + str(args))
    if not is_connected(ctx.guild):
        await connect_guild(ctx)

    keywords = " ".join(args[:]).lower()
    max = -1
    match = None
    for i in songitems:
        if not i[-8:] == "temp.wav":
            score = match_compare(
                re.sub(r"[^a-zA-Z0-9♂ ]+", "", i.lower().split(".")
                       [0]).replace("♂", " "), keywords
            )
            if score > max:
                max = score
                match = i

    if match:
        guildstates[ctx.guild.id].is_shuffling = False
        guildstates[ctx.guild.id].is_queueing = True
        guildstates[ctx.guild.id].queue.add(match)
        await ctx.send("**♂QUEUED♂:** " + match)


@client.command(aliases=["kw"])
async def keyword(ctx, *args):
    """Perform a keyword search for matches including all keywords given as arguments. Queues the result.
    If multiple matches are found, they are displayed to the user.
    """
    print("KEYWORD\t|\t" + str(ctx.guild.id) + "\t|\t" + str(args))
    if not is_connected(ctx.guild):
        await connect_guild(ctx)

    keywords = " ".join(args[:]).lower().split(" ")
    matches = []

    for i in songitems:
        flag = True
        item = re.sub(r"[^a-zA-Z0-9♂ ]+", "",
                      i.lower().split(".")[0]).replace("♂", " ")

        for word in keywords:
            if word not in item:
                flag = False
        if flag and not i[-8:] == "temp.wav":
            matches.append(i)

    if len(matches) == 1:
        guildstates[ctx.guild.id].is_shuffling = False
        guildstates[ctx.guild.id].is_queueing = True
        guildstates[ctx.guild.id].queue.add(matches[0])
        await ctx.send("**♂QUEUED♂:** " + matches[0])
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


@client.command(aliases=["l"])
async def loop(ctx):
    """Toggle loop mode for a guild."""
    print("LOOP\t|\t" + str(ctx.guild.id))
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return

    if guildstates[ctx.guild.id].now_playing:
        guildstates[ctx.guild.id].is_looping = not guildstates[ctx.guild.id].is_looping
    else:
        await ctx.send("♂NOTHING♂PLAYING♂")
        return

    if guildstates[ctx.guild.id].is_looping:
        await ctx.send("**♂LOOP TOGGLED♂:\tON**")
    else:
        await ctx.send("**♂LOOP TOGGLED♂:\tOFF**")


@client.command(aliases=["qr"])
async def qremove(ctx, *args):
    """Clear the song queue for a guild."""
    print("QREMOVE\t|\t" + str(ctx.guild.id) + "\t|\t" + str(args))
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return

    if len(args) == 0:
        await ctx.send("♂ENTER♂AN♂INTEGER♂POSITION♂")
        return
    try:
        test = int(args[0])
        if test < 1 or test > guildstates[ctx.guild.id].queue.size():
            raise ValueError
    except:
        await ctx.send("♂INVALID♂POSITION♂")
        return
    removed = guildstates[ctx.guild.id].queue.remove(int(args[0]) - 1)
    await ctx.send("**♂REMOVED♂:\t**" + removed)


@client.command(aliases=["qc"])
async def qclear(ctx):
    """Clear the song queue for a guild."""
    print("QCLEAR\t|\t" + str(ctx.guild.id))
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return

    guildstates[ctx.guild.id].queue.clear()
    await ctx.send("♂CLEARED♂QUEUE♂")


@client.command(aliases=["qs"])
async def qswap(ctx, *args):
    """Swap 2 songs at positions given as arguments in the queue."""
    print("QSWAP\t|\t" + str(ctx.guild.id) + "\t|\t" + str(args))
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return

    if len(args) < 2:
        await ctx.send("♂GIVE♂TWO♂INTEGER♂POSITIONS♂TO♂SWAP♂")
        return
    try:
        test1 = int(args[0])
        if test1 < 1 or test1 > guildstates[ctx.guild.id].queue.size():
            raise ValueError

        test2 = int(args[1])
        if test2 < 1 or test2 > guildstates[ctx.guild.id].queue.size():
            raise ValueError
    except:
        await ctx.send("♂INVALID♂POSITIONS♂")
        return

    removed = guildstates[ctx.guild.id].queue.swap(test1 - 1, test2 - 1)
    await ctx.send(
        "**♂SWAPPED♂:\t**"
        + guildstates[ctx.guild.id].queue.songlist[test1 - 1]
        + "\n**♂WITH♂:\t**"
        + guildstates[ctx.guild.id].queue.songlist[test2 - 1]
    )
    print(guildstates[ctx.guild.id].queue.songlist)


@client.command(aliases=["qv"])
async def qview(ctx):
    """Display the song queue for a guild."""
    print("QVIEW\t|\t" + str(ctx.guild.id))
    if not is_connected(ctx.guild):
        await ctx.send("♂NOT♂CONNECTED♂OR♂PLAYING♂")
        return

    if guildstates[ctx.guild.id].queue.is_empty():
        await ctx.send("♂QUEUE♂IS♂EMPTY♂")
        return

    qstring = "\n\t\t**\-\-\-\-\-\-\-\-\-♂QUEUE♂\-\-\-\-\-\-\-\-\-**\n"
    songn = 1
    for song in guildstates[ctx.guild.id].queue.songlist:
        qstring += str(songn) + "\t|\t" + song + "\n"
        songn += 1
    await ctx.send(qstring)


@client.command()
async def help(ctx):
    """Help command, displays command information."""
    separator = "\n\-\-\-\n"
    await ctx.send(
        "\n\t\t# ♂MALE♂BOT♂HELP♂\n"
        "\t\t*COMMANDS (case sensitive):*\n"
        "**Join**\t|\t(getoverhere, join, c)\n"
        "Connects the bot to the voice channel the author is connected to."
        + separator
        + "**Leave**\t|\t(fuckyou, leave, dc)\n"
        "Disconnects the bot from voice."
        + separator
        + "**Shuffle Play**\t|\t(shuffle, s)\n"
        "Plays random song on loop until stopped, clears the queue on activation."
        + separator
        + "**Stop**\t|\t(stop, st)\n"
        "Stops shuffling and clears the queue."
        + separator
        + "**Skip**\t|\t(skip, sk)\n"
        "Skips the current song." + separator +
        "**Pause**\t|\t(pause, p)\n"
        "Pauses the currently playing song."
        + separator
        + "**Resume**\t|\t(resume, r)\n"
        "Resumes the currently playing song."
        + separator
        + "**Volume**\t|\t(volume, v)\n"
        "Sets the volume to a decimal value 0.01 to 1.00."
        + separator
        + "**Seek**\t|\t(seek, se)\n"
        "Seek to time given an integer value in seconds."
        + separator
        + "**Now Playing**\t|\t(nowplaying, np)\n"
        "Show a progress bar for the current song."
        + separator
        + "**Replay**\t|\t(replay, re)\n"
        "Replays current song." + separator +
        "**Distort**\t|\t(distort, LOUDER)\n"
        "Heavily distorts current song, and toggles distorted mode on or off."
        " Optionally takes an integer 5-50 as an argument to set magnitude."
        + separator
        + "**Loop**\t|\t(loop, l)\n"
        "Toggle continuous playback of the currently playing song on or off."
        + separator
        + "**Fuzzy**\t|\t(fuzzy, f)\n"
        "Does a simple fuzzy search for the argument in quotes, adds the result to the queue and stops shuffling."
        + separator
        + "**Keyword Search**\t|\t(keyword, kw)\n"
        "Searches for matches containing all keywords, adds the result to the queue and stops shuffling."
        + separator
        + "**Queue Remove**\t|\t(qremove, qr)\n"
        "Removes the song at the specified integer position in the queue."
        + separator
        + "**Queue Clear**\t|\t(qclear, qc)\n"
        "Clears the queue." + separator +
        "**Queue Swap**\t|\t(qswap, qs)\n"
        "Swaps the positions of 2 songs in the queue given their integer positions as arguments."
        + separator
        + "**Queue View**\t|\t(qview, qv)\n"
        "Display all songs currently in queue and their positions." + separator
    )


"""Check for dependencies"""

try:
    subprocess.check_output(["ffmpeg", "-version"])
except:
    print("Error: missing ffmpeg binary, make sure it is in your OS path.")
    sys.exit(0)

try:
    subprocess.check_output(["ffprobe", "-version"])
except:
    print("Error: missing ffprobe binary, make sure it is in your OS path.")
    sys.exit(0)

try:
    subprocess.check_output(["sox", "-h"])
except:
    print("Error: missing sox binary, make sure it is in your OS path.")
    sys.exit(0)

"""Check for valid configuration files"""

try:
    with open("songdir.txt", "r") as songfile:
        songdir = songfile.read().strip()
    if not songdir.endswith("/"):
        songdir = songdir + "/"
    tempitems = os.listdir(songdir)
except:
    print(
        "Error: Problem with songdir.txt configuration. Please ensure it is a valid OS URL on a single line."
    )
    sys.exit(0)

songitems = []
validmediatypes = ["wav", "webm", "mp4", "mp3", "avi", "mkv", "ogg"]
# extract only media files from the song directory
for i in tempitems:
    suffix = i.split(".")[-1]
    if suffix in validmediatypes:
        songitems.append(i)

if len(songitems) < 1:
    print("Error: No valid media files in specified directory.")
    sys.exit(0)

"""Run the client"""
try:
    with open("key.txt", "r") as keyfile:
        client.run(keyfile.read().strip())
except:
    print(
        "Error: problem opening the client with specified auth key, possibly an issue with key.txt configuration."
    )
    sys.exit(0)
