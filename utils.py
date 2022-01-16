import datetime
import sox
import subprocess
import os


def time_to_str(seconds):
    """Convert a time in seconds to a formatted hh:mm:ss string."""
    outstr = str(datetime.timedelta(seconds=seconds)).split(".")[0]
    if outstr.split(":")[0] == "0":
        return outstr[2:]
    return outstr


def distort_audio(inputdir, inputfile, outputdir, outputfile, magnitude, guildid):
    """Distort an input file to a specified magnitude, returns
    path to the ouput file.
    """
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            inputdir + inputfile,
            outputdir + "___1" + str(guildid) + "-temp.wav",
            "-loglevel",
            "quiet",
        ]
    )
    tfm = sox.Transformer()
    tfm.norm(-1.0)
    tfm.bass(magnitude)
    tfm.treble(magnitude * 0.42)
    tfm.gain(magnitude * 2, normalize=False)
    tfm.compand()
    tfm.build(outputdir + "___1" + str(guildid) + "-temp.wav", outputdir + outputfile)
    os.remove(outputdir + "___1" + str(guildid) + "-temp.wav")
    return outputfile


def letter_pairs(string):
    numPairs = len(string) - 1
    pairs = []

    for i in range(numPairs):
        pairs.append([string[i], string[i + 1]])

    return pairs


def word_letter_pairs(string):
    allpairs = []
    words = string.strip().split(" ")

    for i in words:
        pairsinword = letter_pairs(i)
        for j in pairsinword:
            allpairs.append(j)

    return allpairs


def match_compare(str1, str2):
    """Simon White's 'Strike a Match' algorithm for string similarity.

    More information: http://www.catalysoft.com/articles/strikeamatch.html
    """
    pairs1 = word_letter_pairs(str1)
    pairs2 = word_letter_pairs(str2)
    intersection = 0
    union = len(pairs1) + len(pairs2)

    resultset = []
    for i, pair1 in enumerate(pairs1):
        for j, pair2 in enumerate(pairs2):
            if pair1 == pair2:
                intersection += 1
                pairs2[j] = None
                break
    if union == 0:
        return 0
    return (2 * intersection) / union
