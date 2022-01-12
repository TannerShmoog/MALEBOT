class MusicQueue:
    def __init__(self):
        self.songlist = []

    def add(self, songName):
        self.songlist.append(songName)

    def remove(self, position):
        self.songlist.pop(position)

    def clear(self):
        self.songlist = []

    def playsong(self):
        return self.songlist.pop(0)

    def is_empty(self):
        return len(self.songlist) == 0

    def size(self):
        return len(self.songlist)

    def songlist(self):
        return self.songlist

    def swap(self, i1, i2):
        temp = self.songlist[i1]
        self.songlist[i1] = self.songlist[i2]
        self.songlist[i2] = temp
