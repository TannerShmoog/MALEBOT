import datetime
import sox
import subprocess
import os

# convert time in seconds to a hh:mm:ss string
def time_to_str(seconds):
    outstr = str(datetime.timedelta(seconds=seconds)).split(".")[0]
    if outstr.split(":")[0] == "0":
        return outstr[2:]
    return outstr


def distort_audio(inputpath, outputdir, magnitude, guildid):
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            inputpath,
            outputdir + "___" + str(guildid) + "-temp.wav",
            "-loglevel",
            "quiet",
        ]
    )
    output_file = "___1-" + str(guildid) + "-temp.wav"
    tfm = sox.Transformer()
    tfm.norm(-1.0)
    tfm.bass(magnitude)
    tfm.treble(magnitude * 0.42)
    tfm.gain(magnitude * 2, normalize=False)
    tfm.compand()
    tfm.build(outputdir + "___" + str(guildid) + "-temp.wav", outputdir + output_file)
    os.remove(outputdir + "___" + str(guildid) + "-temp.wav")
    return output_file


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
    pairs1 = word_letter_pairs(str1)
    pairs2 = word_letter_pairs(str2)
    intersection = 0
    union = len(pairs1) + len(pairs2)

    resultset = []
    for i in range(len(pairs1)):
        pair1 = pairs1[i]
        for j in range(len(pairs2)):
            pair2 = pairs2[j]
            if pair1 == pair2:
                intersection += 1
                pairs2[j] = None
                break
    if union == 0:
        return 0
    return (2 * intersection) / union
