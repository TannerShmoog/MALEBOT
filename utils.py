import datetime, sox, subprocess

#convert time in seconds to a hh:mm:ss string
def timetostr(seconds):
    outstr = str(datetime.timedelta(seconds=seconds)).split('.')[0]
    if outstr.split(':')[0] == '0':
        return outstr[2:]
    return outstr

def distort_audio(inputpath, outputdir, magnitude, guildid):  
    subprocess.run(['ffmpeg', '-y', '-i', inputpath, outputdir+"___"+str(guildid)+'-temp.wav', '-loglevel', 'quiet'])
    output_file = "___1-"+str(guildid)+"-temp.wav"
    tfm = sox.Transformer()
    tfm.norm(-1.0)
    tfm.bass(magnitude)
    tfm.treble(magnitude*0.42)
    tfm.equalizer(60.0, 80.0, 9.0)
    centralfreq = 107.0
    startgain = 6.0
    tfm.gain(32.0, normalize=False)
    tfm.compand()
    tfm.build(outputdir+"___"+str(guildid)+'-temp.wav', outputdir+output_file)
    return output_file

def letterPairs(string):
    numPairs = len(string)-1 
    pairs = []
    
    for i in range(numPairs):
        pairs.append([string[i], string[i+1]])
    
    return pairs
    
def wordLetterPairs(string):
    allpairs = []
    words = string.strip().split(' ')
    
    for i in words:
        pairsinword = letterPairs(i)
        for j in pairsinword:
            allpairs.append(j)
    
    return allpairs
    
def matchCompare(str1, str2):
    pairs1 = wordLetterPairs(str1)
    pairs2 = wordLetterPairs(str2)
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
    
    return (2*intersection)/union