# MALEBOT
A simple discord music bot to stream from a local library of files


__MALE BOT HELP__
__REQUIREMENTS__

Python Libraries: discord.py, pysox (https://github.com/rabitt/pysox , requires sox to be installed)

Binaries: ffmpeg.exe, ffprobe.exe

A discord bot authentication token. The bot requires both messages and server members intents.

Add your client ID into this link to invite your bot: https://discord.com/oauth2/authorize?client_id=YOUR_APPLICATION_ID&permissions=274881432640&scope=bot


__SETUP__

Create 'songdir.txt', and enter a windows URL pointing to the directory containing your music files.

Create 'key.txt', and enter your bot's authentication key from the discord developer portal.

Place these files in the same directory as the bot.


__COMMANDS (case sensitive)__
        
Join    |    (aliases: 'getoverhere', 'join', 'c')
Connects the bot to the voice channel the author is connected to.
---
Leave    |    (aliases: 'fuckyou', 'leave', 'dc')
Disconnects the bot from voice.
---
Shuffle Play    |    (aliases: 'shuffle', 's')
Plays random song on loop until stopped.
---
Stop    |    (aliases: 'stop', 'st')
Stops the current shuffle queue.
---
Skip    |    (aliases: 'skip', 'sk')
Skips the current song and picks a new random one.
---
Pause    |    (aliases: 'pause', 'p')
Pauses the currently playing song.
---
Resume    |    (aliases: 'resume', 'r')
Resumes the currently playing song.
---
Volume    |    (aliases: 'LOUDER', 'volume', 'v')
Sets the volume to a decimal value 0.01 to 1.00.
---
Seek    |    (aliases: 'seek', 'se')
Seek to time given an integer value in seconds.
---
Now Playing    |    (aliases: 'nowplaying', 'np')
Show a progress bar for the current song.
---
Replay    |    (aliases: 'twoplay', 'replay', 're')
Replays current song.
---
Fuzzy    |    (aliases: 'fuzzy', 'f')
Does a simple fuzzy search for the argument in quotes.
---
Keyword Search    |    (aliases: 'keyword', 'key')
Searches for matches containing all keywords.
---
