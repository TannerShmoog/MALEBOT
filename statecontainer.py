from queueclass import MusicQueue


class GuildStateContainer:
    """Stores state information for a guild."""

    def __init__(self):
        self.is_shuffling = False
        self.is_queueing = False
        self.is_louder = False
        self.is_looping = False
        self.louder_magnitude = -1
        self.vol = 1

        self.now_playing = None
        self.title = None
        self.np_dir = None
        self.timestamp = None
        self.id = None
        self.init_channel = None
        self.queue = MusicQueue()
