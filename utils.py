import datetime 

#convert time in seconds to a hh:mm:ss string
def timetostr(seconds):
    outstr = str(datetime.timedelta(seconds=seconds)).split('.')[0]
    if outstr.split(':')[0] == '0':
        return outstr[2:]
    return outstr


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