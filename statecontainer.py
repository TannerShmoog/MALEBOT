
class guildStateContainer():
    
    def __init__(self):
        self.is_playing = False
        self.is_queueing = False
        self.now_playing = None
        self.timestamp = None
        self.guildid = None