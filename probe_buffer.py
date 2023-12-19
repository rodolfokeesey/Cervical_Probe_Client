import numpy as np

class ProbeBuffer:
    """
    Manages all the data streams for the cervical probe
    """

    def __init__(self, num_channels: int, fs: int):
        self.fs = fs
        self.bufsize = 3 * fs
        self.bufdata: np.ndarray = np.zeros((self.bufsize, num_channels))
    
    def add_data(self, data: np.ndarray):
        n = 