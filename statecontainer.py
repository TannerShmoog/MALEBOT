
class guildStateContainer():
    
    def __init__(self):
        self.is_shuffling = False
        self.is_queueing = False
        self.now_playing = None
        self.timestamp = None
        self.id = None
        self.init_channel = None