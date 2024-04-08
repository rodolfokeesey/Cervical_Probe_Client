import numpy as np

class ProbeBuffer:
    """
    Manages all the data streams for the cervical probe
    """

    def __init__(self, num_channels: int, fs: int):
        self.fs = fs
        self.bufsize = 10 * fs
        self.bufdata: np.ndarray = np.zeros((self.bufsize, num_channels))
        self.cal_slope = -0.0000084
        self.cal_intercept = -0.5655986
    
    def add_data(self, data: np.ndarray):
        n = len(data)
        self.bufdata[:-n] = self.bufdata[n:]
        data = self.convert_to_newtons(data)
        self.bufdata[-n:] = data

    def convert_to_newtons(self, data: np.ndarray):
        data_array = np.array(data)
        data_array[:,1] = 1 * (data_array[:,1] * self.cal_slope + self.cal_intercept)
        return data_array.tolist()